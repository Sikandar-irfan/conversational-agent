# Implementation Plan & Roadmap
## Kannada Voice Conversational Agent (12 Phases)

**Version:** 1.0
**Date:** March 2025
**Language:** Python 3.10+
**Total Estimated Effort:** 4-6 weeks (flexible, self-paced)

---

## Overview

This document provides a step-by-step implementation roadmap for building the Kannada voice conversational agent. The plan is divided into 12 sequential phases, each with clear deliverables, acceptance criteria, and dependencies. Follow the phases in order to avoid missing dependencies.

**Key Principle:** Complete each phase fully before moving to the next. Mark phase complete only when all acceptance criteria are met.

---

## Phase 0: Foundation & Environment Setup

**Duration:** 1-2 days
**Goal:** Project environment ready, dependencies installed, basic structure in place

### Deliverables
- Python virtual environment created and activated
- All dependencies installed (requirements.txt ready)
- Project directory structure created (src/, tests/, docs/)
- src directory stubs created (empty \_\_init\_\_.py files)
- Logger configured and tested
- pydantic Config models created
- README.md with quickstart

### Tasks

**0.1 Project Initialization**
```bash
mkdir -p c:\SRIHARI\ K\ S\conversational\ agent
cd c:\SRIHARI\ K\ S\conversational\ agent

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows
# or: venv\Scripts\activate

# Initialize git (optional)
git init
echo "venv/" > .gitignore
echo ".env" >> .gitignore
```

**0.2 Install Dependencies**

Create `requirements.txt`:
```
asyncio-contextmanager==1.0.0
aiohttp==3.9.0
websockets==12.0
numpy==1.24.0
librosa==0.10.0  # Audio resampling
webrtc-vad==0.0.3  # VAD library
python-livekit==0.7.0  # WebRTC
pydantic==2.0.0  # Config validation
pydantic-settings==2.0.0
python-dotenv==1.0.0  # .env loading
pytest==7.4.0  # Testing
pytest-asyncio==0.21.0  # Async testing
```

```bash
pip install -r requirements.txt
```

**0.3 Create Directory Structure**

```bash
# Create src directories
mkdir -p src/{config,audio,vad,turn_detection,stt,llm,tts,interrupt,pipeline,utils}

# Create test directories
mkdir -p tests/{unit,integration,fixtures}

# Create docs directory
mkdir docs

# Create empty __init__.py files
touch src/__init__.py
touch src/config/__init__.py
touch src/audio/__init__.py
touch src/vad/__init__.py
touch src/turn_detection/__init__.py
touch src/stt/__init__.py
touch src/llm/__init__.py
touch src/tts/__init__.py
touch src/interrupt/__init__.py
touch src/pipeline/__init__.py
touch src/utils/__init__.py

touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

**0.4 Configure Logger (src/utils/logger.py)**

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def info(self, event, **kwargs):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "event": event,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))

    def warning(self, event, **kwargs):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "event": event,
            **kwargs
        }
        self.logger.warning(json.dumps(log_entry))

    def error(self, event, **kwargs):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "event": event,
            **kwargs
        }
        self.logger.error(json.dumps(log_entry))
```

**0.5 Configuration Models (src/config/settings.py)**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    sarvam_api_key: str
    groq_api_key: str

    # Pause detection
    pause_duration_ms: int = 800
    pause_confirmation_ms: int = 50

    # Context management
    max_conversation_turns: int = 10
    context_reset_timeout_min: int = 10

    # Latency targets (ms)
    vad_latency_target: int = 50
    stt_latency_target: int = 200
    llm_latency_target: int = 150
    tts_latency_target: int = 100

    # Model configuration
    llm_model: str = "mixtral-8x7b-32768"  # Groq default

    class Config:
        env_file = ".env"

settings = Settings()
```

Create `.env.example`:
```
SARVAM_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

**0.6 Unit Test Framework Setup (tests/conftest.py)**

```python
import pytest
import asyncio

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def sample_audio_16khz():
    """Sample 16kHz mono PCM audio (1 second)."""
    import numpy as np
    sr = 16000
    duration = 1.0
    samples = int(sr * duration)
    audio = np.random.randn(samples).astype(np.int16)
    return audio.tobytes()
```

### Success Criteria
- [ ] Python imports all modules without error: `python -c "import src"`
- [ ] pytest runs: `pytest --collect-only` shows test discovery
- [ ] Config loads from .env without raising exceptions
- [ ] Logger outputs JSON structured logs
- [ ] README.md has quickstart section

---

## Phase 1: Audio I/O & VAD

**Duration:** 1-2 days
**Goal:** Audio flowing from WebRTC through resampler to VAD, events firing correctly

**Dependencies:** Phase 0 complete

### Deliverables
- `AudioInputHandler` class (WebRTC audio receiver)
- `AudioResampler` class (48kHz stereo → 16kHz mono)
- `VADEngine` abstraction with `WebRTCVADImpl`
- Unit tests for resampler
- Unit tests for VAD
- Integration test: sample audio → VAD → events

### Key Files
- `src/audio/input_handler.py` - WebRTC receiver
- `src/audio/resampler.py` - Format conversion
- `src/vad/vad_engine.py` - VAD abstraction
- `src/vad/webrtc_vad.py` - WebRTC-VAD implementation
- `tests/unit/test_audio_resampler.py`
- `tests/unit/test_vad_engine.py`

### Implementation Guide

**1.1 AudioInputHandler (src/audio/input_handler.py)**

```python
import asyncio
from typing import Callable, Optional
import numpy as np

class AudioInputHandler:
    def __init__(self, sample_rate=48000, channels=2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.on_audio_chunk: Optional[Callable] = None

    async def receive_from_livekit(self, frame):
        """
        Receives audio frame from LiveKit WebRTC stream.
        frame: audio data (48kHz stereo)
        """
        # Emit event
        if self.on_audio_chunk:
            await self.on_audio_chunk(frame, timestamp=time.time())

    def set_audio_listener(self, callback):
        self.on_audio_chunk = callback
```

**1.2 AudioResampler (src/audio/resampler.py)**

```python
import librosa
import numpy as np

class AudioResampler:
    def __init__(self, source_sr=48000, target_sr=16000, channels=2):
        self.source_sr = source_sr
        self.target_sr = target_sr
        self.channels = channels

    def resample(self, audio_bytes: bytes) -> bytes:
        """
        Convert 48kHz stereo → 16kHz mono.
        Returns: 16-bit PCM bytes
        """
        # Convert bytes to numpy array
        audio = np.frombuffer(audio_bytes, dtype=np.int16)

        # Handle stereo → mono (take average of channels)
        if self.channels == 2:
            audio = audio.reshape(-1, 2)
            audio = np.mean(audio, axis=1).astype(np.int16)

        # Resample
        audio_float = audio.astype(np.float32) / 32768.0
        resampled = librosa.resample(
            audio_float,
            orig_sr=self.source_sr,
            target_sr=self.target_sr
        )

        # Convert back to int16
        resampled = (resampled * 32768.0).astype(np.int16)
        return resampled.tobytes()
```

**1.3 VADEngine (src/vad/vad_engine.py & webrtc_vad.py)**

```python
# vad_engine.py (abstract base)
from abc import ABC, abstractmethod

class VADEngine(ABC):
    @abstractmethod
    async def process(self, audio_chunk: bytes) -> bool:
        """Process audio chunk, return True if voice detected."""
        pass

    @abstractmethod
    def get_is_speaking(self) -> bool:
        """Get current voice state."""
        pass

# webrtc_vad.py (implementation)
import webrtcvad

class WebRTCVADImpl(VADEngine):
    def __init__(self, sample_rate=16000, frame_duration_ms=10, aggressiveness=2):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self._is_speaking = False
        self._last_voice_time = 0

    async def process(self, audio_chunk: bytes) -> bool:
        """Process 16kHz mono PCM audio."""
        audio = np.frombuffer(audio_chunk, dtype=np.int16)

        # Process frame by frame
        for i in range(0, len(audio), self.frame_size):
            frame = audio[i:i+self.frame_size]

            if len(frame) < self.frame_size:
                break  # Incomplete frame

            has_voice = self.vad.is_speech(frame.tobytes(), self.sample_rate)

            # Detect transitions
            if has_voice and not self._is_speaking:
                self._is_speaking = True
                await self._emit_event("on_voice_start")

            elif not has_voice and self._is_speaking:
                self._is_speaking = False
                await self._emit_event("on_voice_end")

            self._last_voice_time = time.time() if has_voice else self._last_voice_time

        return self._is_speaking

    def get_is_speaking(self) -> bool:
        return self._is_speaking

    async def _emit_event(self, event_name):
        # Will be overridden by calling code
        pass
```

### Unit Tests

**tests/unit/test_audio_resampler.py:**

```python
import pytest
import numpy as np
from src.audio.resampler import AudioResampler

def test_resampler_converts_format():
    resampler = AudioResampler(source_sr=48000, target_sr=16000, channels=2)

    # Create dummy 48kHz stereo audio (1 second)
    duration = 1.0
    sr_source = 48000
    samples = int(sr_source * duration) * 2  # stereo
    audio = np.random.randint(-32768, 32767, samples, dtype=np.int16)

    result = resampler.resample(audio.tobytes())

    # Check output is roughly right size
    # 1 second @ 16kHz = 16000 samples = 32000 bytes
    assert len(result) > 30000 and len(result) < 35000
```

**tests/unit/test_vad_engine.py:**

```python
import pytest
from src.vad.webrtc_vad import WebRTCVADImpl
import numpy as np

@pytest.mark.asyncio
async def test_vad_detects_voice():
    vad = WebRTCVADImpl(sample_rate=16000, frame_duration_ms=10)

    # Create silence
    silence = np.zeros(16000, dtype=np.int16).tobytes()
    assert not await vad.process(silence)

    # Create tone (simple sine wave)
    sr = 16000
    duration = 0.5
    freq = 440  # A4
    samples = int(sr * duration)
    t = np.arange(samples) / sr
    tone = (32767 * 0.5 * np.sin(2*np.pi*freq*t)).astype(np.int16)

    is_voice = await vad.process(tone.tobytes())
    # May or may not detect tone as voice (VAD is conservative)
    # Just verify it doesn't crash
```

### Success Criteria
- [ ] `AudioResampler` converts 48kHz stereo → 16kHz mono correctly
- [ ] Output audio maintains amplitude (verify with sox)
- [ ] `VADEngine` detects voice transitions in test audio
- [ ] VAD latency <10ms per frame (measured)
- [ ] No unhandled exceptions in tests

---

## Phase 2: Turn Detection & Audio Buffering

**Duration:** 1 day
**Goal:** User audio is accumulated until pause detected, event fires with complete audio buffer

**Dependencies:** Phase 1 complete (VAD events available)

### Deliverables
- `PauseDetector` class (end-of-speech via pause heuristics)
- `AudioBuffer` class (accumulate chunks until turn complete)
- Unit tests for pause timing
- Integration test: VAD events → audio buffer → turn complete event

### Key Files
- `src/turn_detection/pause_detector.py`
- `src/audio/audio_buffer.py`
- `tests/unit/test_pause_detector.py`
- `tests/unit/test_audio_buffer.py`

### Implementation Guide

**2.1 AudioBuffer (src/audio/audio_buffer.py)**

```python
class AudioBuffer:
    def __init__(self, sample_rate=16000):
        self.sr = sample_rate
        self.buffer = bytearray()
        self.start_time = None

    def append_chunk(self, chunk: bytes):
        """Add audio chunk to buffer."""
        if not self.start_time:
            self.start_time = time.time()
        self.buffer.extend(chunk)

    def get_buffer(self) -> bytes:
        """Get accumulated audio."""
        return bytes(self.buffer)

    def clear(self):
        """Clear buffer for next turn."""
        self.buffer.clear()
        self.start_time = None

    def get_duration_ms(self) -> float:
        """Get buffer duration in ms."""
        samples = len(self.buffer) // 2  # 16-bit int
        return (samples / self.sr) * 1000
```

**2.2 PauseDetector (src/turn_detection/pause_detector.py)**

```python
import asyncio
import time

class PauseDetector:
    def __init__(self, pause_duration_ms=800, confirmation_ms=50):
        self.pause_duration = pause_duration_ms / 1000.0  # Convert to seconds
        self.confirmation = confirmation_ms / 1000.0
        self.pause_start = None
        self.on_turn_complete: Optional[Callable] = None

    async def on_voice_start(self):
        """Called when VAD detects voice start."""
        self.pause_start = None  # Clear any pending pause

    async def on_voice_end(self):
        """Called when VAD detects voice end."""
        self.pause_start = time.time()

    async def monitor_pause(self, vad_engine):
        """Monitor VAD for pause completion."""
        while True:
            await asyncio.sleep(0.1)  # Check every 100ms

            if self.pause_start is None:
                continue

            elapsed = time.time() - self.pause_start

            if elapsed >= self.pause_duration:
                # Pause duration exceeded, confirm VAD is still off
                await asyncio.sleep(self.confirmation)

                if not vad_engine.get_is_speaking():
                    # Confirmed: turn complete
                    if self.on_turn_complete:
                        await self.on_turn_complete()
                    self.pause_start = None
```

### Success Criteria
- [ ] Pause detection fires after 800ms of silence
- [ ] False positives minimal (test with breath sounds)
- [ ] Audio buffer contains correct audio data
- [ ] Turn complete event has correct duration

---

## Phase 3: STT Pipeline (Sarvam AI Integration)

**Duration:** 1-2 days
**Goal:** User audio transcribed to text via Sarvam AI WebSocket streaming

**Dependencies:** Phase 2 complete (audio buffer ready)

### Deliverables
- `SarvamSTTClient` class (WebSocket connection, streaming)
- `STTPipeline` orchestrator (error handling, retries, fallback)
- Unit test: mock Sarvam API responses
- Integration test: real API call (requires API key)

### Key Files
- `src/stt/sarvam_client.py`
- `src/stt/stt_pipeline.py`
- `src/utils/exceptions.py` (custom exception classes)
- `tests/unit/test_stt_client_mock.py`
- `tests/integration/test_stt_pipeline.py`

### Implementation Guide

**3.1 Custom Exceptions (src/utils/exceptions.py)**

```python
class AgentException(Exception):
    pass

class TransientError(AgentException):
    pass

class STTTimeoutError(TransientError):
    pass

class STTError(AgentException):
    pass

class APIKeyMissingError(AgentException):
    pass
```

**3.2 SarvamSTTClient (src/stt/sarvam_client.py)**

```python
import websockets
import json
import base64
import asyncio

class SarvamSTTClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "wss://api.sarvam.ai/v1/asr"

    async def transcribe(self, audio_bytes: bytes, language="kannada") -> str:
        """
        Transcribe audio using Sarvam AI WebSocket.
        """
        if not self.api_key:
            raise APIKeyMissingError("SARVAM_API_KEY not set")

        try:
            async with websockets.connect(
                self.endpoint,
                subprotocols=["asr-stream"],
                timeout=2.0
            ) as websocket:
                # Send auth header
                auth_msg = {
                    "event": "start",
                    "auth": self.api_key,
                    "language": language,
                    "model": "sarvam-asr-2024-01"
                }
                await websocket.send(json.dumps(auth_msg))

                # Send audio in chunks
                chunk_size = 16000 * 0.16  # 160ms @ 16kHz = 5120 bytes
                offset = 0
                while offset < len(audio_bytes):
                    chunk = audio_bytes[offset:offset + int(chunk_size)]
                    offset += int(chunk_size)

                    audio_msg = {
                        "event": "data",
                        "audio": base64.b64encode(chunk).decode()
                    }
                    await websocket.send(json.dumps(audio_msg))
                    await asyncio.sleep(0.16)  # Pace with audio duration

                # Signal end
                await websocket.send(json.dumps({"event": "end"}))

                # Receive transcript
                transcript = ""
                while True:
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=0.5
                        )
                        msg = json.loads(response)
                        if msg.get("status") == "done":
                            transcript = msg.get("transcript", "")
                            break
                    except asyncio.TimeoutError:
                        break

                return transcript

        except asyncio.TimeoutError:
            raise STTTimeoutError("Sarvam AI STT timeout")
        except Exception as e:
            raise STTError(f"STT error: {e}")
```

**3.3 STTPipeline (src/stt/stt_pipeline.py)**

```python
from src.utils.exceptions import TransientError, STTTimeoutError
import asyncio

class STTPipeline:
    def __init__(self, stt_client):
        self.client = stt_client
        self.on_transcript_ready: Optional[Callable] = None
        self.logger = StructuredLogger(__name__)

    async def transcribe_turn(self, audio_buffer: bytes, language: str = "kannada"):
        """
        Transcribe audio with retry logic.
        """
        max_retries = 3
        backoff_times = [0.1, 0.2, 0.5]  # seconds

        for attempt in range(max_retries):
            try:
                transcript = await self.client.transcribe(audio_buffer, language)

                if not transcript:
                    raise STTError("Empty transcript")

                self.logger.info(
                    "stt_complete",
                    attempt=attempt + 1,
                    transcript_length=len(transcript),
                    language=language
                )

                if self.on_transcript_ready:
                    await self.on_transcript_ready(transcript, language)

                return transcript

            except (STTTimeoutError, TransientError) as e:
                self.logger.warning(
                    "stt_retry",
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_times[attempt])
                else:
                    # Fallback response
                    fallback = "ಕ್ಷಮಿಸಿ, ನಾನು ಸುಂದರವಾಗಿ ಆಲಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಹೇಳಿ"
                    if self.on_transcript_ready:
                        await self.on_transcript_ready(fallback, language)
                    return None
```

### Success Criteria
- [ ] STT latency <300ms (measured with real API)
- [ ] Retry logic works (test with simulated timeout)
- [ ] Fallback response generated on 3 retries
- [ ] Kannada transcript accuracy >90% (manual check on 10 samples)

---

## Phase 4: Context Manager

**Duration:** 1 day
**Goal:** Conversation history maintained for LLM prompt building

**Dependencies:** Phase 0 (config ready)

### Deliverables
- `ContextManager` class (deque-based conversation store)
- Unit tests for context building
- Kannada/English language tracking

### Key Files
- `src/llm/context_manager.py`
- `tests/unit/test_context_manager.py`

### Implementation Guide

```python
from collections import deque
from dataclasses import dataclass

@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str
    language: str  # "kannada" or "english"
    timestamp: float

class ContextManager:
    def __init__(self, max_turns=10):
        self.max_turns = max_turns
        self.turns: deque = deque(maxlen=max_turns)
        self.last_activity = time.time()

    def add_turn(self, role: str, content: str, language: str = "kannada"):
        """Add turn to context."""
        turn = ConversationTurn(
            role=role,
            content=content,
            language=language,
            timestamp=time.time()
        )
        self.turns.append(turn)
        self.last_activity = time.time()

    def get_context(self) -> List[Dict[str, str]]:
        """Format for LLM API."""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self.turns
        ]

    def reset(self):
        """Clear context."""
        self.turns.clear()
        self.last_activity = time.time()

    def is_timed_out(self, timeout_min=10) -> bool:
        """Check if conversation idle > timeout."""
        return (time.time() - self.last_activity) > (timeout_min * 60)
```

### Success Criteria
- [ ] Context correctly formatted for LLM
- [ ] Max capacity enforced (oldest turns dropped)
- [ ] Language tracked per turn
- [ ] Reset works correctly

---

## Phase 5: LLM Pipeline (Groq Integration)

**Duration:** 1-2 days
**Goal:** LLM generates responses from transcript plus context

**Dependencies:** Phase 4 complete (context ready)

### Deliverables
- `GroqLLMClient` class (streaming API)
- `LLMPipeline` orchestrator (prompt building, truncation)
- Mock tests
- Integration with real Groq API (requires API key)

### Key Files
- `src/llm/llm_client.py`
- `src/llm/llm_pipeline.py`
- `tests/unit/test_llm_client_mock.py`
- `tests/integration/test_llm_pipeline.py`

### Implementation Guide

**5.1 GroqLLMClient (src/llm/llm_client.py)**

```python
import aiohttp
import json

class GroqLLMClient:
    def __init__(self, api_key: str, model="mixtral-8x7b-32768"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    async def stream_response(self, messages: List[Dict]):
        """
        Stream LLM response tokens.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 200
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=3.0)
                ) as resp:
                    async for line in resp.content:
                        if line.startswith(b"data: "):
                            data_str = line[6:].decode()
                            if data_str.strip() and data_str != "[DONE]":
                                try:
                                    data = json.loads(data_str)
                                    token = data["choices"][0]["delta"].get("content", "")
                                    if token:
                                        yield token
                                except json.JSONDecodeError:
                                    continue
            except asyncio.TimeoutError:
                raise LLMTimeoutError("Groq API timeout")
```

**5.2 LLMPipeline (src/llm/llm_pipeline.py)**

```python
class LLMPipeline:
    SYSTEM_PROMPT_KANNADA = """
    ನೀವು ಒಂದು ಸಹಾಯಕ, ರೆಸಲ್ಯೂಶನ್ ಮೇಲೆ ಕೇಂದ್ರೀಭೂತ ಗ್ರಾಹಕ ಸೇವಾ ಏಜೆಂಟ್ ಆಗಿದ್ದೀರಿ.
    ಹೆಚ್ಚುವರಿ ಅತಿ ಮುಖ್ಯ, ಸಂಬಂಧಿತ ಮತ್ತು ಸ್ಪಷ್ಟ ಪ್ರತಿಕ್ರಿಯೆಗಳನ್ನು ನೀಡಿ.
    ಗ್ರಾಹಕನ ಚಿಂತೆಯನ್ನು ಮೊದಲಬಲ್ಲೆ ಗುರುತಿಸಿ, ನಂತರ ಪರಿಹಾರ ಮೊದಲಾಗಿ ನೀಡಿ.
    ನೈಸರ್ಗಿಕ, ಸರಳ ಕನ್ನಡ ಬಳಸಿ. ಯಾಂತ್ರಿಕ ಭಾಷೆ ತಪ್ಪಿಸಿ.
    ರೆಸ್ಪನ್ಸ್ ಗಳು ಸ್ವಲ್ಪ ಸುಂಬರ (20-50 ಪದಗಳು), max 150 ಪದಗಳು.
    """

    def __init__(self, llm_client, context_manager):
        self.llm = llm_client
        self.context = context_manager
        self.on_response_chunk: Optional[Callable] = None
        self.on_response_complete: Optional[Callable] = None

    async def generate_response(self, user_transcript: str, language: str):
        """Generate LLM response with streaming."""
        # Build prompt
        system_prompt = self.SYSTEM_PROMPT_KANNADA if language == "kannada" else self.SYSTEM_PROMPT_ENGLISH

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(self.context.get_context())
        messages.append({"role": "user", "content": user_transcript})

        # Stream tokens
        response_text = ""
        tokens_buffer = []

        async for token in self.llm.stream_response(messages):
            response_text += token
            tokens_buffer.append(token)

            # Buffer first 3 tokens, then stream
            if len(tokens_buffer) >= 3:
                buffered = "".join(tokens_buffer)
                if self.on_response_chunk:
                    await self.on_response_chunk(buffered)
                tokens_buffer = []

            # Check length limit
            word_count = len(response_text.split())
            if word_count >= 150:
                # Truncate at sentence boundary
                response_text = self._truncate_at_sentence(response_text, 150)
                break

        # Flush remaining
        if tokens_buffer:
            if self.on_response_chunk:
                await self.on_response_chunk("".join(tokens_buffer))

        # Update context
        self.context.add_turn("user", user_transcript, language)
        self.context.add_turn("assistant", response_text, language)

        if self.on_response_complete:
            await self.on_response_complete(response_text)

        return response_text

    def _truncate_at_sentence(self, text: str, max_words: int) -> str:
        """Truncate at sentence boundary."""
        words = text.split()
        if len(words) <= max_words:
            return text

        truncated = " ".join(words[:max_words])
        for ending in ["।", "।", "।", ".", "!", "?"]:
            if ending in truncated:
                last_pos = truncated.rfind(ending)
                if last_pos > (max_words * 0.8):
                    return truncated[:last_pos + len(ending)]

        return truncated + "।"
```

### Success Criteria
- [ ] LLM latency <200ms to first token (measured)
- [ ] Response length limited (max 150 words)
- [ ] Context correctly included
- [ ] Streaming works (tokens received incrementally)

---

## Phase 6: TTS Pipeline (Sarvam AI Integration)

**Duration:** 1-2 days
**Goal:** LLM response synthesized to speech, streamed to speaker

**Dependencies:** Phase 5 complete (LLM response available)

### Deliverables
- `SarvamTTSClient` class (WebSocket streaming)
- `TTSPipeline` orchestrator (interruptible, queuing)
- Mock tests
- Integration with real Sarvam TTS API

### Key Files
- `src/tts/sarvam_tts_client.py`
- `src/tts/tts_pipeline.py`
- `tests/unit/test_tts_client_mock.py`

### Implementation Guide

```python
# src/tts/sarvam_tts_client.py
class SarvamTTSClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "wss://api.sarvam.ai/v1/tts"

    async def synthesize_stream(self, text: str, language: str = "kannada"):
        """
        Synthesize text to speech, streaming audio chunks.
        """
        async with websockets.connect(self.endpoint) as ws:
            # Send auth
            await ws.send(json.dumps({
                "event": "start",
                "auth": self.api_key,
                "language": language
            }))

            # Send text chunks
            for chunk in text.split():
                await ws.send(json.dumps({
                    "event": "data",
                    "text": chunk
                }))
                await asyncio.sleep(0.05)

            await ws.send(json.dumps({"event": "end"}))

            # Receive audio chunks
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("status") == "done":
                    break
                if msg.get("audio"):
                    audio_bytes = base64.b64decode(msg["audio"])
                    yield audio_bytes

# src/tts/tts_pipeline.py
class TTSPipeline:
    def __init__(self, tts_client):
        self.client = tts_client
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.stop_signal = False
        self.on_audio_chunk: Optional[Callable] = None

    async def synthesize(self, response_text: str, language: str):
        """Synthesize response, stream chunks."""
        self.stop_signal = False

        try:
            async for audio_chunk in self.client.synthesize_stream(
                response_text,
                language=language
            ):
                if self.stop_signal:
                    break

                if self.on_audio_chunk:
                    await self.on_audio_chunk(audio_chunk)

        except Exception as e:
            logger.error("tts_error", error=str(e))

    def interrupt(self):
        """Stop TTS immediately."""
        self.stop_signal = True
        self.output_queue = asyncio.Queue()  # Clear queue
```

### Success Criteria
- [ ] TTS latency <150ms to first audio byte
- [ ] Audio quality acceptable (no artifacts)
- [ ] Interrupt stops playback within 50ms

---

## Phase 7: Interrupt Handler & Pipeline Integration

**Duration:** 1-2 days
**Goal:** Hard interrupt handling; full pipeline orchestrated by state machine

**Dependencies:** Phases 1-6 complete

### Deliverables
- `InterruptHandler` class (monitors VAD during TTS)
- `StateMachine` class (orchestrates all components)
- `EventBus` for pub-sub events
- Integration tests: full conversation with interrupt

### Key Files
- `src/interrupt/interrupt_handler.py`
- `src/pipeline/state_machine.py`
- `src/pipeline/events.py`
- `tests/integration/test_e2e_interrupt.py`

### Implementation Guide

**7.1 EventBus & Event Types (src/pipeline/events.py)**

```python
from dataclasses import dataclass

@dataclass
class Event:
    timestamp: float = field(default_factory=time.time)

@dataclass
class AudioChunkEvent(Event):
    chunk: bytes
    sr: int

@dataclass
class VoiceStartedEvent(Event):
    pass

@dataclass
class VoiceEndedEvent(Event):
    pass

@dataclass
class TurnCompleteEvent(Event):
    audio_buffer: bytes

@dataclass
class TranscriptReadyEvent(Event):
    transcript: str
    language: str

@dataclass
class ResponseChunkEvent(Event):
    token: str

@dataclass
class ResponseCompleteEvent(Event):
    response: str

@dataclass
class PlaybackCompleteEvent(Event):
    pass

@dataclass
class InterruptDetectedEvent(Event):
    pass

# Event bus
class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event_type, callback):
        """Register listener."""
        self.listeners[event_type].append(callback)

    async def emit(self, event: Event):
        """Emit event to all listeners."""
        for callback in self.listeners[type(event)]:
            await callback(event)
```

**7.2 InterruptHandler (src/interrupt/interrupt_handler.py)**

```python
class InterruptHandler:
    def __init__(self, vad_engine, event_bus):
        self.vad = vad_engine
        self.events = event_bus
        self.tts_active = False
        self.debounce_ms = 50

    async def monitor(self):
        """Monitor VAD during TTS playback."""
        while True:
            if self.tts_active and self.vad.get_is_speaking():
                # Debounce
                await asyncio.sleep(self.debounce_ms / 1000.0)

                if self.vad.get_is_speaking():
                    # Confirmed interrupt
                    await self.events.emit(InterruptDetectedEvent())
                    self.tts_active = False

            await asyncio.sleep(0.01)  # Check every 10ms

    async def on_tts_start(self):
        self.tts_active = True

    async def on_tts_end(self):
        self.tts_active = False
```

**7.3 StateMachine (src/pipeline/state_machine.py)** (simplified)

```python
from enum import Enum

class State(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING_TURN = "processing_turn"
    STT_IN_PROGRESS = "stt_in_progress"
    LLM_IN_PROGRESS = "llm_in_progress"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"

class StateMachine:
    def __init__(self, event_bus, components):
        self.state = State.IDLE
        self.events = event_bus
        # Store references to all pipeline components
        self.audio_input = components["audio_input"]
        self.vad = components["vad"]
        self.turn_detector = components["turn_detector"]
        self.stt_pipeline = components["stt"]
        self.llm_pipeline = components["llm"]
        self.tts_pipeline = components["tts"]
        self.context = components["context"]
        self.logger = StructuredLogger(__name__)

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register state transition handlers."""
        self.events.on(VoiceStartedEvent, self._on_voice_start)
        self.events.on(VoiceEndedEvent, self._on_voice_end)
        self.events.on(TurnCompleteEvent, self._on_turn_complete)
        self.events.on(TranscriptReadyEvent, self._on_transcript)
        self.events.on(ResponseCompleteEvent, self._on_response)
        self.events.on(InterruptDetectedEvent, self._on_interrupt)

    async def transition(self, new_state: State):
        """Transition to new state."""
        self.logger.info("state_transition", from_state=self.state.value, to_state=new_state.value)
        self.state = new_state

    async def _on_voice_start(self, event: VoiceStartedEvent):
        if self.state == State.LISTENING:
            # Already listening, no change
            pass

    async def _on_voice_end(self, event: VoiceEndedEvent):
        if self.state == State.LISTENING:
            # Start pause timer in turn_detector
            pass

    async def _on_turn_complete(self, event: TurnCompleteEvent):
        if self.state in (State.LISTENING, State.INTERRUPTED):
            await self.transition(State.PROCESSING_TURN)
            # Start STT
            await self.stt_pipeline.transcribe_turn(
                event.audio_buffer,
                language="kannada"
            )

    async def _on_transcript(self, event: TranscriptReadyEvent):
        if self.state == State.STT_IN_PROGRESS:
            await self.transition(State.LLM_IN_PROGRESS)
            # Generate LLM response
            await self.llm_pipeline.generate_response(
                event.transcript,
                language=event.language
            )

    async def _on_response(self, event: ResponseCompleteEvent):
        if self.state == State.LLM_IN_PROGRESS:
            await self.transition(State.SPEAKING)
            # Start TTS
            await self.tts_pipeline.synthesize(
                event.response,
                language="kannada"
            )

    async def _on_interrupt(self, event: InterruptDetectedEvent):
        if self.state == State.SPEAKING:
            await self.transition(State.INTERRUPTED)
            # Halt TTS
            self.tts_pipeline.interrupt()
            # Return to processing (will buffer new audio)
            await self.transition(State.PROCESSING_TURN)
```

### Success Criteria
- [ ] Full conversation completes end-to-end
- [ ] States transition correctly
- [ ] Interrupt detected and handled
- [ ] No race conditions

---

## Phase 8: Audio Output & WebRTC

**Duration:** 1 day
**Goal:** TTS audio routed to speaker via WebRTC

**Dependencies:** Phase 7 complete

### Deliverables
- `AudioOutputHandler` class (LiveKit SendTrack)
- Integration with main loop

### Key Files
- `src/audio/output_handler.py`
- `src/main.py` (entry point)

### Implementation Guide

```python
# src/audio/output_handler.py
class AudioOutputHandler:
    def __init__(self, livekit_participant):
        self.participant = livekit_participant
        self.queue: asyncio.Queue = asyncio.Queue()

    async def send_audio(self, audio_chunk: bytes):
        """Queue audio chunk for playback."""
        await self.queue.put(audio_chunk)

    async def playback_loop(self):
        """Continuously play queued audio chunks."""
        while True:
            try:
                chunk = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=0.1
                )
                # Send to LiveKit
                await self.participant.send_audio(chunk)
            except asyncio.TimeoutError:
                continue

# src/main.py (entry point)
import asyncio

async def main():
    settings = Settings()

    # Initialize components
    audio_input = AudioInputHandler()
    resampler = AudioResampler()
    vad = WebRTCVADImpl()
    turn_detector = PauseDetector()
    stt_pipeline = STTPipeline(SarvamSTTClient(settings.sarvam_api_key))
    context = ContextManager()
    llm_pipeline = LLMPipeline(
        GroqLLMClient(settings.groq_api_key),
        context
    )
    tts_pipeline = TTSPipeline(SarvamTTSClient(settings.sarvam_api_key))
    audio_output = AudioOutputHandler(livekit_participant)
    event_bus = EventBus()

    # Create state machine
    components = {
        "audio_input": audio_input,
        "vad": vad,
        "turn_detector": turn_detector,
        "stt": stt_pipeline,
        "llm": llm_pipeline,
        "tts": tts_pipeline,
        "context": context,
    }
    state_machine = StateMachine(event_bus, components)

    # Create interrupt handler
    interrupt_handler = InterruptHandler(vad, event_bus)

    # Start tasks
    await asyncio.gather(
        audio_input_listener(audio_input, resampler, event_bus),
        turn_detector.monitor_pause(vad),
        interrupt_handler.monitor(),
        audio_output.playback_loop(),
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Success Criteria
- [ ] Audio audible through WebRTC
- [ ] No dropout
- [ ] Proper audio format (24kHz mono)

---

## Phase 9: Performance & Latency Testing

**Duration:** 1-2 days
**Goal:** Verify <500ms end-to-end latency

**Dependencies:** Phase 8 complete

### Deliverables
- Latency measurement instrumentation
- Performance tests for each component
- Report with latency breakdown

### Key Files
- `src/utils/metrics.py`
- `tests/integration/test_latency_*.py`

### Implementation Guide

```python
# src/utils/metrics.py
from contextlib import asynccontextmanager
import time

class LatencyTracker:
    def __init__(self):
        self.measurements = []

    @asynccontextmanager
    async def measure(self, name: str):
        """Context manager to measure latency."""
        start = time.time()
        try:
            yield
        finally:
            latency = (time.time() - start) * 1000  # ms
            self.measurements.append((name, latency))
            logger.info("latency_measurement", component=name, ms=latency)

# Usage
tracker = LatencyTracker()

async def test_e2e_latency():
    """Measure end-to-end latency."""
    async with tracker.measure("e2e_latency"):
        # Simulate turn complete
        await state_machine._on_turn_complete(...)
        # Monitor until response starts playing
        await wait_for(state_machine, lambda s: s == State.SPEAKING)

    # Check result
    e2e = [m[1] for m in tracker.measurements if m[0] == "e2e_latency"][0]
    assert e2e < 500, f"E2E latency exceeded: {e2e}ms"
```

### Success Criteria
- [ ] E2E latency <500ms (95th percentile <600ms)
- [ ] No component exceeds budget by >50%
- [ ] Latency consistent across multiple turns

---

## Phase 10: Error Handling & Robustness

**Duration:** 1-2 days
**Goal:** Agent handles failures gracefully, recovers automatically

**Dependencies:** Phase 9 complete

### Deliverables
- Comprehensive error handling
- Fallback responses
- Reconnect logic
- Error scenario tests

### Implementation Guide (covered in Phase 3-6)

### Success Criteria
- [ ] Agent never crashes (no unhandled exceptions)
- [ ] All errors logged
- [ ] Recovery from transient failures <5s
- [ ] Graceful degradation on permanent failures

---

## Phase 11: Metrics & Monitoring

**Duration:** 1 day
**Goal:** Real-time performance visibility

**Dependencies:** Phase 10 complete

### Deliverables
- Metrics collection
- Structured logging
- Optional dashboard

### Implementation Guide (covered in Phase 5 latency tracking)

### Success Criteria
- [ ] Per-turn metrics logged
- [ ] Error tracking working
- [ ] No overhead from metrics

---

## Phase 12: Documentation & Testing

**Duration:** 1-2 days
**Goal:** Code well-documented, tests comprehensive

**Dependencies:** All phases complete

### Deliverables
- README.md with quickstart
- Docstrings for all classes
- Test coverage >80%

### Tasks

**12.1 README.md**

```markdown
# Kannada Voice Conversational Agent

A real-time voice-based customer service agent for Kannada speakers.

## Installation

1. Clone repo, create venv, install requirements
2. Copy .env.example → .env, Add API keys
3. Run: python src/main.py

##Configuration

Edit src/config/settings.py for latency targets, context limits, etc.

## Testing

python -m pytest tests/ -v

## Troubleshooting

[See docs/troubleshooting.md]
```

**12.2 Add Docstrings**

```python
class STTPipeline:
    """
    Orchestrates speech-to-text transcription.

    Accepts audio buffers from turn detector, sends to Sarvam AI,
    handles retries and fallbacks.

    Attributes:
        client (SarvamSTTClient): Sarvam AI API client
        on_transcript_ready (Callable): Event fired when transcript ready

    Example:
        pipeline = STTPipeline(client)
        await pipeline.transcribe_turn(audio_bytes, language="kannada")
    """
```

### Success Criteria
- [ ] All public methods documented
- [ ] README complete and accurate
- [ ] Test coverage >80%
- [ ] No TODO comments

---

## Implementation Milestones

| Milestone | Phase(s) | Criteria |
|-----------|----------|----------|
| **Audio Flowing** | 0-1 | Audio from WebRTC → VAD working |
| **Turn Detection** | 2 | Audio buffered, pause detected |
| **User Transcribed** | 3 | STT working, >90% accuracy |
| **Agent Responds** | 4-5 | LLM generates, context included |
| **Full Conversation** | 6-7 | End-to-end pipeline with interrupt |
| **Performance Verified** | 9 | E2E latency <500ms confirmed |
| **Production Ready** | 10-12 | All tests passing, docs complete |

---

## Phase Dependencies Graph

```
Phase 0 (Foundation)
  ↓
Phase 1 (Audio/VAD)
  ↓
Phase 2 (Turn Detection)
  ├→ Phase 3 (STT) ─┐
  │                 ├→ Phase 5 (LLM) ─┐
  └→ Phase 4 (Context) ─┘              │
                                       ├→ Phase 6 (TTS)
                                       │              ├→ Phase 7 (Integration)
                                       │              │              ├→ Phase 8 (Audio Output)
                                       │              │              │              ├→ Phase 9 (Performance)
                                       │              │              │              │              ├→ Phase 10 (Errors)
                                       │              │              │              │              │              ├→ Phase 11 (Metrics)
                                       │              │              │              │              │              │              ├→ Phase 12 (Docs)
```

**Key Parallelization:** Phase 4 (Context) can be done in parallel with Phase 3 (STT).

---

## Risk Mitigation Strategies

### Risk 1: Latency Budget Exceeded
**Mitigation:**
- Instrument early (Phase 9, not late)
- Identify bottleneck components
- Optimize hot paths (likely: LLM or network)
- Accept higher latency if unavoidable, document

### Risk 2: Sarvam AI API Changes
**Mitigation:**
- Abstract with `SarvamSTTClient` and `SarvamTTSClient` interfaces
- Plan alternative providers (Google Cloud Speech, Azure)
- Test with mocks early and often

### Risk 3: Interrupt Race Conditions
**Mitigation:**
- Test interrupt scenarios extensively (Phase 7)
- Use thread-safe queues and asyncio primitives
- Log state transitions for debugging

### Risk 4: Groq Rate Limits
**Mitigation:**
- Research free tier limits early (Phase 0)
- Plan batching or local LLM (Ollama) fallback
- Monitor token usage (Phase 11)

### Risk 5: WebRTC Setup Complexity
**Mitigation:**
- Verify setup in Phase 0 or 1
- Use LiveKit-provided samples
- Fall back to simple audio I/O for development

---

## Success Criteria Summary

**At Completion:**
- [ ] All 12 phases complete
- [ ] Test coverage >80%
- [ ] E2E latency <500ms verified
- [ ] All error scenarios handled
- [ ] Kannada fluency verified (native speaker review)
- [ ] Documentation complete
- [ ] Ready to hand off to implementation team

---

## References

- **prd.md** - Scope and requirements
- **architecture.md** - Technical design
- **ai_rules.md** - Quality standards
- See each phase for specific file locations and class definitions

---
