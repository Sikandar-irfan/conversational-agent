# backend/livekit_tts.py
# LiveKit Agents Custom TTS Adapter for Dr. Vishnuvardhan Voice Package

import os
import sys
import asyncio
from pathlib import Path
from typing import AsyncIterable

CURRENT_DIR = Path(__file__).parent.resolve()
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from livekit.agents import tts
    BaseTTS = tts.TTS
    BaseChunkedStream = tts.ChunkedStream
except (ImportError, AttributeError):
    BaseTTS = object
    BaseChunkedStream = object

from adapters.seedvc_adapter import SeedVCAdapter

class RoseLiveKitTTS(BaseTTS):
    """
    LiveKit Agents custom TTS plugin for Dr. Vishnuvardhan voice package.
    """
    def __init__(self, voice_pack_path: str = None, language: str = "kn"):
        if voice_pack_path is None:
            default_vc = CURRENT_DIR / "voice_packs" / "bandhana_voice.vc"
            voice_pack_path = os.getenv("VOICE_PACK_PATH", str(default_vc))
        elif not os.path.isabs(voice_pack_path) and not os.path.exists(voice_pack_path):
            voice_pack_path = str(CURRENT_DIR / voice_pack_path)

        if BaseTTS is not object:
            super().__init__(
                capabilities=tts.TTSCapabilities(streaming=False),
                sample_rate=22050,
                num_channels=1,
            )

        self.language = language
        self._sample_rate = 22050
        self.voice_pack_path = voice_pack_path
        
        print(f"[LiveKit TTS] Initializing Dr. Vishnuvardhan Voice Package: {self.voice_pack_path}")
        self.adapter = SeedVCAdapter()
        self.adapter._xtts_adapter = False
        self.adapter.load_voice_package(self.voice_pack_path)

    def synthesize(self, text: str, *, conn_options: getattr(tts, 'APIConnectOptions', None) = None, **kwargs):
        if conn_options is None:
            try:
                from livekit.agents import DEFAULT_API_CONNECT_OPTIONS
                conn_options = DEFAULT_API_CONNECT_OPTIONS
            except ImportError:
                pass

        return RoseTTSStream(
            tts=self,
            adapter=self.adapter,
            text=text,
            language=self.language,
            sample_rate=self._sample_rate,
            conn_options=conn_options,
        )


class RoseTTSStream(BaseChunkedStream):
    def __init__(
        self,
        tts: BaseTTS,
        adapter: SeedVCAdapter,
        text: str,
        language: str,
        sample_rate: int = 22050,
        conn_options: getattr(tts, 'APIConnectOptions', None) = None,
    ):
        if BaseChunkedStream is not object:
            super().__init__(tts=tts, input_text=text, conn_options=conn_options)
        self.adapter = adapter
        self.text = text
        self.language = language
        self.sample_rate = sample_rate

    async def _run(self, output_emitter=None) -> None:
        import soundfile as sf
        import numpy as np

        base_voice_map = {
            "kn": "kn-IN-GaganNeural",
            "hi": "hi-IN-MadhurNeural",
            "ta": "ta-IN-ValluvarNeural",
            "en": "en-IN-PrabhatNeural"
        }
        base_voice = base_voice_map.get(self.language, "kn-IN-GaganNeural")

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None,
            lambda: self.adapter.synthesize(
                text=self.text,
                language=self.language,
                base_voice=base_voice,
                temperature=0.70,
                speed=1.0
            )
        )

        wav_path = res["audio_path"]
        data, sr = sf.read(wav_path, dtype="int16")
        chunk_samples = int(sr * 0.10)

        if output_emitter is not None:
            if not getattr(output_emitter, "_started", False):
                if hasattr(output_emitter, "initialize"):
                    output_emitter.initialize(
                        request_id="dr_vishnuvardhan_tts",
                        sample_rate=sr,
                        num_channels=1,
                        mime_type="audio/pcm",
                    )
                elif hasattr(output_emitter, "start"):
                    output_emitter.start(
                        request_id="dr_vishnuvardhan_tts",
                        sample_rate=sr,
                        num_channels=1,
                        stream=False,
                    )

        for i in range(0, len(data), chunk_samples):
            chunk = data[i : i + chunk_samples]
            if output_emitter is not None:
                if hasattr(output_emitter, "push"):
                    output_emitter.push(chunk.tobytes())
            elif hasattr(tts, "AudioFrame"):
                frame = tts.AudioFrame(
                    data=chunk.tobytes(),
                    sample_rate=sr,
                    num_channels=1,
                    samples_per_channel=len(chunk)
                )
                if hasattr(self, "_event_ch"):
                    if hasattr(tts, "SynthesizeEvent"):
                        self._event_ch.send_nowait(tts.SynthesizeEvent(frame=frame))
                    elif hasattr(tts, "SynthesizedAudio"):
                        self._event_ch.send_nowait(tts.SynthesizedAudio(frame=frame, request_id=""))
