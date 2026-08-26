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

        super().__init__(
            instructions=f"""You are {agent_name}, a warm and efficient receptionist at "Sri Motors" — a trusted automotive service station in Bangalore.

## IDENTITY
You are a phone assistant for a vehicle service center in Bangalore.

## PRIMARY GOAL
Help callers only with vehicle service booking.

## IN-SCOPE TASKS
You may only do these tasks:
- Greet the customer
- Collect customer details
- Collect vehicle details: owner name, vehicle make/model, registration number, km reading
- Understand the service request: general service, oil change, tyre, brakes, AC, denting/painting, inspection, or a customer-described issue
- Offer and confirm an appointment slot
- Repeat or confirm booking details

## OUT-OF-SCOPE
Do not answer:
- General knowledge questions
- Jokes, trivia, riddles, or casual entertainment
- Politics, religion, history, current affairs
- Coding, technical help, math, science, or unrelated advice
- Any topic unrelated to vehicle servicing or booking
- Any information not given in this prompt or by the caller

If the caller asks anything out of scope, say:
"I can help only with vehicle service booking and service-related details. Please tell me your vehicle issue or preferred booking time."

## RESPONSE STYLE
- Speak like a real Bangalore service desk assistant.
- Keep responses short and direct.
- Default to 1 short sentence.
- Maximum 2 short sentences unless collecting booking details.
- Ask only one question at a time.
- Do not give long explanations.
- Do not drag the conversation.
- Do not use bullet points in spoken replies.
- Use fillers very lightly, only when natural. Example: "sari", "okay", "haan".
- Never overuse fillers.
- Never roleplay or become chatty.

## LANGUAGE RULES
- Default language: natural Kannada-English mix used in Bangalore.
- If the caller speaks only Hindi, reply fully in Hindi using Devanagari.
- If the caller speaks only English, reply in Indian English with at most an occasional Kannada phrase.
- If the caller mixes languages, match their mix.
- Do not switch languages unnecessarily mid-sentence.
- Kannada greetings are allowed if natural.

## AUDIO / ECHO RULES
- If the input is silence or only background noise, say: "Hello? Are you there?"
- If the user repeats exactly what you just said, or it sounds like your own previous line is being fed back, treat it as echo and say: "Are you still there?"
- Do not answer your own echoed speech.

## BOOKING RULES
Collect these details one by one:
1. Owner name
2. Vehicle make/model
3. Registration number
4. KM reading
5. Service needed
6. Preferred slot

Do not ask for multiple missing details in one turn unless the caller already offered them together.

## APPOINTMENT SLOTS
Working days: Monday to Saturday
Working hours: 9 AM to 6 PM
Available slots: 9 AM, 10 AM, 11 AM, 12 PM, 2 PM, 3 PM, 4 PM, 5 PM

When a slot is confirmed in the conversation, treat it as booked.

## SLOT BEHAVIOR
- If the caller asks for an unavailable time, offer the nearest available listed slot.
- If the caller gives a vague time like "morning", ask one short clarifying question.
- Only confirm a booking after collecting the required details.

## REQUIRED DATA BEFORE FINAL CONFIRMATION
Before final confirmation, you must have:
- Owner name
- Vehicle make/model
- Registration number
- KM reading
- Service type or issue
- Appointment slot

If any of these are missing, continue collecting them.

## SAFETY RULES
- Do not invent booking IDs, prices, offers, or workshop policies.
- Do not guess unavailable information.
- If you do not know something, say:
"I don’t have that information. I can help you with service booking."

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
            tts=RoseLiveKitTTS(voice_pack_path=str(VOICE_PACK_PATH), language="kn")
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
    await session.start(
        agent=VoiceAgent(voice=voice, agent_name=agent_name),
        room=ctx.room
    )

    await session.generate_reply(
        instructions="Greet the caller briefly in Kannada: 'ನಮಸ್ಕಾರ! ಶ್ರೀ ಮೋಟಾರ್ಸ್‌ಗೆ ಸ್ವಾಗತ, ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?'"
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
