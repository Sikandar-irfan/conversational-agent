import logging
import json
import re
import os
import sys
import asyncio
from pathlib import Path
from collections.abc import AsyncIterable
from typing import AsyncIterable
from dotenv import load_dotenv
import soundfile as sf

from livekit.agents import tts
from livekit.agents import JobContext, TurnHandlingOptions, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import openai, sarvam
from livekit.agents.voice.agent import ModelSettings
from livekit.agents.beta.tools import EndCallTool
from livekit.agents import TurnHandlingOptions, inference

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Determine project base directory dynamically
BASE_DIR = Path(__file__).parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment variables
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

logger = logging.getLogger("voice-agent")
logger.setLevel(logging.INFO)

# ── Language detection ────────────────────────────────────────────────────────
_SCRIPT_MAP: list[tuple[str, str]] = [
    (r"[\u0C80-\u0CFF]", "kn-IN"),   # Kannada   ← priority
    (r"[\u0900-\u097F]", "hi-IN"),   # Devanagari / Hindi
    (r"[\u0B80-\u0BFF]", "ta-IN"),   # Tamil
    (r"[\u0C00-\u0C7F]", "te-IN"),   # Telugu
    (r"[\u0D00-\u0D7F]", "ml-IN"),   # Malayalam
    (r"[\u0980-\u09FF]", "bn-IN"),   # Bengali
    (r"[\u0A80-\u0AFF]", "gu-IN"),   # Gujarati
    (r"[\u0A00-\u0A7F]", "pa-IN"),   # Punjabi
]

def detect_tts_language(text: str) -> str:
    best_lang, best_count = "kn-IN", 0
    for pattern, lang in _SCRIPT_MAP:
        count = len(re.findall(pattern, text))
        if lang == "kn-IN" and count > 0:
            return "kn-IN"
        if count > best_count:
            best_count, best_lang = count, lang
    return best_lang if best_count > 0 else "en-IN"

# Dynamic Voice Pack Path
VOICE_PACK_PATH = Path(os.getenv("VOICE_PACK_PATH", str(BASE_DIR / "voice_packs" / "bandhana_voice.vc")))

from livekit_tts import RoseLiveKitTTS, RoseTTSStream


# ── Voice Agent ───────────────────────────────────────────────────────────────
class VoiceAgent(Agent):
    def __init__(self, voice="shubh", agent_name="Shubh"):
        groq_api_key = os.getenv("GROQ_API_KEY") or os.getenv("groq_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")

        if groq_api_key:
            model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
            llm_instance = openai.LLM(
                model=model_name,
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            logger.info(f"Initialized LLM via Groq API ({model_name})")
        elif openrouter_key:
            model_name = os.getenv("OPENROUTER_MODEL", "openrouter/free")
            llm_instance = openai.LLM(
                model=model_name,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
            logger.info(f"Initialized LLM via OpenRouter ({model_name})")
        else:
            raise ValueError("Neither GROQ_API_KEY nor OPENROUTER_API_KEY found in environment variables!")

        # Select dynamic voice pack based on persona selected on UI
        if voice.lower() in ["kavya", "simran", "asika", "asika_multi"]:
            target_pack = BASE_DIR / "voice_packs" / "asika_multi.vc"
        else:
            target_pack = BASE_DIR / "voice_packs" / "bandhana_voice.vc"

        if not target_pack.exists():
            target_pack = VOICE_PACK_PATH

        logger.info(f"Using voice pack for persona '{agent_name}': {target_pack.name}")

        super().__init__(
            instructions=f"""You are {agent_name}, a warm and efficient receptionist at "Sri Motors" — a trusted automotive service station in Bangalore.

## IDENTITY
You are a phone assistant for a vehicle service center in Bangalore.

## STRICT LANGUAGE RULES
- **PRIMARY LANGUAGE: KANNADA**.
- Unless the caller explicitly speaks full English or Hindi, you MUST respond 100% in natural Kannada (using Kannada script).
- NEVER switch to English unprompted. If the user speaks Kannada or mixed Kannada, respond ONLY in Kannada.
- When asking out-of-scope fallback, say in Kannada: "ನಾನು ವಾಹನ ಸರ್ವಿಸ್ ಬುಕಿಂಗ್ ವಿಷಯಗಳಲ್ಲಿ ಮಾತ್ರ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ."

## KANNADA QUESTION TEMPLATES (STRICTLY USE THESE KANNADA PHRASES)
- Owner Name: "ನಿಮ್ಮ ಶುಭ ಹೆಸರು ಏನು ಸಾರ್?"
- Vehicle Make & Model: "ನಿಮ್ಮ ವಾಹನದ ಕಂಪನಿ ಮತ್ತು ಮಾಡೆಲ್ ಯಾವುದು ಸಾರ್?" (ಉದಾಹರಣೆಗೆ: Swift, Hero Splendor, Activa)
- Registration Number: "ನಿಮ್ಮ ವಾಹನದ ನಂಬರ್ ಪ್ಲೇಟ್ ಸಂಖ್ಯೆ ಯಾವುದು?"
- KM Reading: "ನಿಮ್ಮ ವಾಹನ ಎಷ್ಟು ಕಿಲೋಮೀಟರ್ ಓಡಿದೆ ಸಾರ್?"
- Service Needed: "ವಾಹನಕ್ಕೆ ಏನು ಸರ್ವಿಸ್ ಮಾಡಿಸಬೇಕು?"
- Appointment Slot: "ಯಾವ ದಿನ ಮತ್ತು ಸಮಯಕ್ಕೆ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಮಾಡಲಿ?"

## RESPONSE STYLE
- Speak like a polite Bangalore service desk receptionist.
- Keep responses short, direct, and natural.
- Maximum 1 or 2 short sentences per reply.
- Ask only one question at a time.
- Do not use bullet points or formatting in spoken replies.

## AUDIO / ECHO RULES
- If the input is silence, say in Kannada: "ಹಲೋ? ಕೇಳಿಸ್ತಾ ಇದೆಯಾ ಸಾರ್?"
- If the user repeats your previous line, say in Kannada: "ಹಲೋ? ಲೈನ್‌ನಲ್ಲಿದ್ದೀರಾ?"

## REQUIRED DATA BEFORE FINAL CONFIRMATION
Before final confirmation, collect these details one by one in Kannada:
1. Owner name ("ನಿಮ್ಮ ಹೆಸರು")
2. Vehicle make/model ("ವಾಹನದ ಮಾಡೆಲ್")
3. Registration number ("ವಾಹನದ ನಂಬರ್")
4. KM reading ("ಓಡಿರೋ ಕಿಲೋಮೀಟರ್")
5. Service needed ("ಸರ್ವಿಸ್ ವಿಷಯ")
6. Appointment slot ("ಸಮಯ")

## CALL TERMINATION RULES
- If the caller says goodbye or phrases like "bye", "goodbye", "end call", "ಧನ್ಯವಾದಗಳು ಬೈ", "ಸಾಕು ಬೈ", "ಸರಿ ಬೈ", reply in Kannada: "ತುಂಬಾ ಧನ್ಯವಾದಗಳು ಸಾರ್! ಶುಭ ದಿನ." and end the call.

## CONVERSATION FLOW
1. Greet the caller
2. Ask the reason for the call
3. Collect missing booking details one by one
4. Offer or confirm an available slot
5. Summarize the final booking in one short confirmation
""",
            stt=sarvam.STT(
                language="kn-IN",
                model="saaras:v3",
                mode="transcribe",
                flush_signal=True
            ),
            llm=llm_instance,
            tts=RoseLiveKitTTS(voice_pack_path=str(target_pack), language="kn")
        )

async def graceful_end(session, room, api):
    await session.say("Thanks for your time. Have a great day.")
    await session.aclose()
    await api.room.delete_room(room.name)


# ── Entry point ───────────────────────────────────────────────────────────────
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info(f"User connected to room: {ctx.room.name}")

    voice = "shubh"
    agent_name = "shubh"

    for participant in ctx.room.remote_participants.values():
        if participant.metadata:
            try:
                meta = json.loads(participant.metadata)
                voice = meta.get("voice", voice)
                agent_name = meta.get("agentName", agent_name)
                logger.info(f"User selected agent: {agent_name} (voice: {voice})")
            except Exception as e:
                logger.warning(f"Could not parse participant metadata: {e}")
            break

    session = AgentSession(
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            endpointing={
                "mode": "fixed",
                "min_delay": 0.8,
                "max_delay": 3.0,
            },
            preemptive_generation={
                "preemptive_tts": True,
                "preemptive_llm": True,
            }
        )
    )

    @session.on("user_speech_committed")
    def on_user_speech(msg):
        text = getattr(msg, "content", "") or ""
        if not isinstance(text, str):
            text = str(text)
        text_lower = text.lower()
        goodbye_words = ["bye", "goodbye", "disconnect", "cut call", "end call", "ಬೈ", "ಸಾಕು ಬೈ", "ಧನ್ಯವಾದಗಳು ಬೈ", "ಸರಿ ಬೈ"]
        if any(w in text_lower for w in goodbye_words):
            logger.info(f"Detected goodbye in user transcript: '{text}'. Hanging up call after speech...")
            async def auto_hangup():
                await asyncio.sleep(3.5)
                try:
                    await ctx.room.disconnect()
                    logger.info(f"Room '{ctx.room.name}' disconnected automatically after user goodbye.")
                except Exception as e:
                    logger.warning(f"Failed to auto-disconnect room: {e}")
            asyncio.create_task(auto_hangup())

    await session.start(
        agent=VoiceAgent(voice=voice, agent_name=agent_name),
        room=ctx.room
    )

    await session.generate_reply(
        instructions="Greet the caller briefly in Kannada: 'ನಮಸ್ಕಾರ! ಶ್ರೀ ಮೋಟಾರ್ಸ್‌ಗೆ ಸ್ವಾಗತ, ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?'"
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
