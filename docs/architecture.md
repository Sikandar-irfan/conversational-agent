# System Architecture Documentation
## Kannada Voice Conversational Agent

**Version:** 1.0
**Date:** March 2025
**Status:** Active Development

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Directory Structure](#directory-structure)
3. [Component Data Flow](#component-data-flow)
4. [State Machine](#state-machine)
5. [Async/Concurrency Model](#asyncconcurrency-model)
6. [Error Handling Strategy](#error-handling-strategy)
7. [Data Types & Contracts](#data-types--contracts)
8. [Security & Privacy Boundaries](#security--privacy-boundaries)

---

## High-Level Architecture

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERACTION                             │
│  Kannada/English Speech Input (WebRTC) ← LiveKit Client         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AUDIO INPUT LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ AudioInputHandler (WebRTC Stream Receiver)              │   │
│  │ - Receives 48kHz stereo chunks (20ms) from LiveKit      │   │
│  │ - Emits: on_audio_chunk(chunk, timestamp)              │   │
│  └──────────────────┬───────────────────────────────────────┘   │
│                     │                                            │
│  ┌──────────────────↓───────────────────────────────────────┐   │
│  │ AudioResampler (Format Conversion)                      │   │
│  │ - 48kHz stereo → 16kHz mono for STT                     │   │
│  │ - Latency: <10ms                                        │   │
│  └──────────────────┬───────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ↓                 ↓                 ↓
┌────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  VAD Module    │ │ Turn Detection   │ │  Audio Buffer    │
│  (Parallel)    │ │  Module          │ │  (Accumulate)    │
└────────────────┘ └──────────────────┘ └──────────────────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    STT LAYER                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STT Pipeline (Sarvam AI WebSocket)                      │   │
│  │ - Sends: audio chunks 160ms → Sarvam AI API            │   │
│  │ - Receives: transcript (streaming)                     │   │
│  │ - Latency: ~180-200ms                                  │   │
│  │ - Output: on_transcript_ready(text)                    │   │
│  └──────────────────┬───────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┴──────────────────┐
           │                                    │
           ↓                                    ↓
┌──────────────────────────┐   ┌───────────────────────────┐
│   Context Manager        │   │   LLM Pipeline            │
│   (Conversation Hist)    │   │   (Groq/Alternative)     │
│   - Deque of N turns     │   │ - Input: transcript+ctx   │
│   - Max 10 turns default │   │ - Streams tokens          │
└──────────────────────────┘   │ - Latency: 120-200ms      │
           │                    │ - Output: response tokens │
           └────────┬───────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                     TTS LAYER                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TTS Pipeline (Sarvam AI WebSocket)                      │   │
│  │ - Sends: response text chunks                           │   │
│  │ - Receives: audio chunks (24kHz mono)                   │   │
│  │ - Begins playback immediately (time-to-first-byte)     │   │
│  │ - Monitors: interrupt signal during playback            │   │
│  │ - Latency: ~80ms to first audio byte                    │   │
│  └──────────────────┬───────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┴──────────────────┐
           │                                    │
           ↓                                    ↓
┌──────────────────────────┐   ┌───────────────────────────┐
│  Interrupt Handler       │   │  Audio Output Handler      │
│  (Monitors VAD during    │   │  (WebRTC Speaker)         │
│   TTS playback)          │   │ - Sends: audio chunks     │
│  - Detects: VAD on       │   │ - Stops on interrupt      │
│  - Triggers: TTS halt    │   │                           │
│  - Latency: <100ms       │   │                           │
└──────────────────────────┘   └───────────────────────────┘
           │                                    │
           └────────────────┬───────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              AUDIO OUTPUT (WebRTC)                               │
│  To: User speakers via LiveKit client                            │
└─────────────────────────────────────────────────────────────────┘
           ↓
           └───────────────────→  Back to Audio Input Layer
                                  (Continuous listening)
```

---

## Directory Structure

### Full Project Tree

```
conversational-agent/
│
├── docs/
│   ├── prd.md                          # Product Requirements Document
│   ├── architecture.md                 # This document
│   ├── ai_rules.md                     # Quality Control & Optimization
│   ├── plan.md                         # Implementation Roadmap
│   └── API_SPECS.md                    # (Optional) External API reference
│
├── src/
│   ├── __init__.py
│   ├── main.py                         # Entry point, event loop initializer
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py                 # Pydantic config models
│   │   └── constants.py                # Hard-coded constants
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── input_handler.py            # WebRTC audio input receiver
│   │   ├── output_handler.py           # WebRTC audio output sender
│   │   ├── resampler.py                # Audio format conversion
│   │   └── audio_buffer.py             # Chunk accumulation
│   │
│   ├── vad/
│   │   ├── __init__.py
│   │   ├── vad_engine.py               # VAD engine abstraction
│   │   └── webrtc_vad.py               # WebRTC-VAD implementation
│   │
│   ├── turn_detection/
│   │   ├── __init__.py
│   │   └── pause_detector.py           # End-of-speech via pause
│   │
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── sarvam_client.py            # Sarvam AI WebSocket client
│   │   └── stt_pipeline.py             # STT orchestrator
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── context_manager.py          # Conversation history
│   │   ├── llm_client.py               # Groq API client
│   │   └── llm_pipeline.py             # LLM orchestrator
│   │
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── sarvam_tts_client.py        # Sarvam AI TTS WebSocket
│   │   └── tts_pipeline.py             # TTS orchestrator
│   │
│   ├── interrupt/
│   │   ├── __init__.py
│   │   └── interrupt_handler.py        # VAD monitoring during TTS
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── state_machine.py            # State orchestration
│   │   ├── events.py                   # Event type definitions
│   │   └── language_detector.py        # Kannada vs English detection
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                   # Structured logging
│       ├── metrics.py                  # Latency & error tracking
│       ├── async_helpers.py            # Async utilities
│       └── exceptions.py               # Custom exceptions
│
├── tests/
│   ├── __init__.py
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_audio_resampler.py
│   │   ├── test_vad_engine.py
│   │   ├── test_pause_detector.py
│   │   ├── test_context_manager.py
│   │   ├── test_language_detector.py
│   │   └── ...
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_stt_pipeline.py       # Real Sarvam AI API
│   │   ├── test_llm_pipeline.py       # Real Groq API
│   │   ├── test_tts_pipeline.py       # Real Sarvam AI TTS
│   │   └── test_e2e_conversation.py   # Full pipeline
│   │
│   └── fixtures/
│       ├── sample_audio_kannada.wav
│       ├── sample_audio_english.wav
│       ├── mock_responses.json
│       └── test_transcripts.json
│
├── .env.example                        # Template for API keys
├── .env                                # (Git-ignored) Actual API keys
├── .gitignore                          # Exclude .env, __pycache__, etc.
├── requirements.txt                    # Python dependencies
├── requirements-dev.txt                # Dev-only dependencies (pytest, etc.)
├── README.md                           # Quick start guide
└── LICENSE                             # MIT or Apache 2.0
```

### Key Directory Rationale

**`src/` Structure by Responsibility:**
- **config/** - Centralized configuration (testable, reloadable)
- **audio/** - All audio I/O concerns isolated
- **vad/**, **turn_detection/** - Speech detection pipeline
- **stt/**, **tts/** - External API clients, separated from business logic
- **llm/** - Language model integration + context management
- **interrupt/** - Interrupt handling (critical feature)
- **pipeline/** - Orchestration layer (state machine, events, language detection)
- **utils/** - Cross-cutting concerns (logging, metrics, exceptions)

**Benefits:**
- Clear separation of concerns (testable in isolation)
- Easy to mock external APIs (Sarvam, Groq)
- Async patterns consistent across all modules
- Minimal interdependencies between components

---

## Component Data Flow

### 1. Audio Input Pipeline

**Files:** `src/audio/input_handler.py`, `src/audio/audio_buffer.py`, `src/audio/resampler.py`

**Inputs:**
- WebRTC audio stream from LiveKit (48kHz stereo, 20ms chunks)

**Processing:**
```python
# Pseudo-code:
raw_audio_chunk (48kHz stereo, 20ms)
  ↓ [Resampler: librosa.resample]
16kHz mono PCM chunk
  ↓ [Emit event: on_audio_chunk(chunk, timestamp)]
```

**Outputs:**
- Event: `on_audio_chunk(chunk: bytes, timestamp: float)`
- Emitted to: VAD engine, audio buffer

**Latency:** <20ms (minimal overhead, just resampling)

**Key Design:**
- Non-blocking async (asyncio callback-based)
- Resampling happens immediately (no buffering waste)
- Events drive downstream processing

---

### 2. VAD Pipeline

**Files:** `src/vad/vad_engine.py`, `src/vad/webrtc_vad.py`

**Inputs:**
- Audio chunks from AudioInputHandler (16kHz mono PCM)

**Processing:**
```
16kHz PCM frame (10ms)
  ↓ [WebRTC VAD classifier]
voice_activity: bool
  ↓ [State tracker: was_speaking?]
Emit: on_voice_start() [if just transitioned]
Emit: on_voice_end()   [if just stopped]
```

**Outputs:**
- Event: `on_voice_start()` - User started speaking
- Event: `on_voice_end()` - User stopped speaking
- State: `is_speaking: bool`, `voice_start_time: float`

**Latency:** <10ms per frame

**Key Design:**
- Frame-based processing (10ms frames for VAD)
- Stateful: tracks transitions (prevents event spam)
- Listeners: turn detector, interrupt handler

---

### 3. Turn Detection Pipeline

**Files:** `src/turn_detection/pause_detector.py`

**Inputs:**
- Events: `on_voice_start()`, `on_voice_end()` from VAD
- Configuration: `pause_duration` (default 800ms)

**Processing:**
```
on_voice_end() event
  ↓
Wait for pause_duration (800ms default)
  ↓
Check VAD status: still off?
  ↓ Yes:
Emit: on_turn_complete(audio_buffer)
  ↓ No:
Reset timer, continue listening
```

**Outputs:**
- Event: `on_turn_complete(audio_buffer: bytes, transcript_lang: str | None)`
- Contains: accumulated audio from voice_start to pause boundary

**Latency:** 800ms pause + 50ms confirmation ≈ 850ms (user-induced, not perceived as agent latency)

**Data Structure:**
```python
@dataclass
class TurnData:
    audio_buffer: bytes  # Accumulated WAV audio
    timestamp_start: float  # When speech started
    timestamp_end: float    # When speech ended
    duration: float         # Audio duration
```

**Key Design:**
- Debouncing: waits 800ms + confirmation to avoid false positives
- Accumulates all audio (no loss)
- Clears buffer after emitting event

---

### 4. STT Pipeline

**Files:** `src/stt/sarvam_client.py`, `src/stt/stt_pipeline.py`

**Inputs:**
- Event: `on_turn_complete(audio_buffer)`

**Processing:**
```
audio_buffer (WAV bytes)
  ↓ [SarvamSTTClient]
  │ - WebSocket: wss://api.sarvam.ai/v1/asr
  │ - Message: { "audio": base64(audio), "task": "asr" }
  ↓
transcript_stream (incremental results)
  ↓ [Collect final transcript]
transcript: str (e.g., "ಹಾಯ, ನಾನು ಸಾಲದ ಮಾಹಿತಿ ಬೇಕು")
  ↓
Emit: on_transcript_ready(transcript)
```

**Outputs:**
- Event: `on_transcript_ready(transcript: str)`
- Includes: detected language (Kannada/English)

**Latency:** ~180-200ms (Sarvam AI typical)

**Data Structures:**
```python
@dataclass
class STTRequest:
    audio_data: bytes  # WAV or PCM
    language: str      # "kannada", "english"
    sample_rate: int   # 16000

@dataclass
class STTResponse:
    transcript: str
    confidence: float
    language: str
```

**Error Handling:**
- Timeout: 2 seconds per request
- Retry: Exponential backoff (100ms, 200ms, 500ms, 1s)
- Max retries: 3
- Fallback: "I didn't catch that. Can you repeat?" (Kannada version in Kannada mode)

**Key Design:**
- Streaming API (partial results supported, final only used)
- Language detection can be hinted from context
- Robust error recovery with fallback responses

---

### 5. LLM Pipeline

**Files:** `src/llm/context_manager.py`, `src/llm/llm_client.py`, `src/llm/llm_pipeline.py`

**Inputs:**
- Event: `on_transcript_ready(transcript)`
- Context: from ContextManager (last N turns)

**Processing:**
```
transcript + context_history
  ↓ [ContextManager.get_context()]
  │ Returns: List[Dict[role, content]]
  │ [
  │   {"role": "user", "content": "ನಾಕ್ಷತ್ರ..."},
  │   {"role": "assistant", "content": "..."},
  │   {"role": "user", "content": transcript}
  │ ]
  ↓ [LLMPipeline.build_prompt()]
prompt = system_prompt + context_history + user_message
  ↓ [GroqLLMClient.stream_response_tokens()]
  │ - WebSocket/HTTP: https://api.groq.com/v1/messages
  │ - Model: "mixtral-8x7b-32768" or latest (supports Kannada)
  │ - Streaming enabled
  ↓
response_tokens (stream)
  ↓ [Collect first 2-3 tokens, then stream rest]
Emit: on_response_chunk(token)
  ↓ [Until sentence boundary or 150 words]
Emit: on_response_complete(full_response)
  ↓ [Update ContextManager]
```

**Outputs:**
- Event: `on_response_chunk(token: str)` (streaming)
- Event: `on_response_complete(response: str)` (full response)
- Side effect: ContextManager updated with response

**Latency:** ~120-200ms to first token, ~50ms per subsequent token

**Key Design:**
- Streaming: collect initial tokens, buffer against LLM variability
- Context windowing: last N turns (configurable, default 10)
- Prompt building: system + context + user message
- Truncation: stops at sentence boundary or 150-word limit

**Response Quality Rules:**
- Max 150 words per response (~10-15 seconds TTS)
- References prior context (>90% should mention previous turns)
- Kannada-optimized: natural Kannada responses, not translations
- Customer service tone: professional, solution-oriented, concise

**Data Structures:**
```python
@dataclass
class PromptContext:
    system_prompt: str
    conversation_history: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]
    current_user_message: str
    language: str  # "kannada" or "english"

@dataclass
class LLMResponse:
    text: str
    tokens_used: int
    model: str
    language: str
```

---

### 6. Interrupt Handler

**Files:** `src/interrupt/interrupt_handler.py`

**Inputs:**
- Event: `on_voice_start()` from VAD (during TTS playback)
- Signal: `tts_active: bool` (monitored continuously)

**Processing:**
```
While TTS is playing (tts_active = True):
  ↓ [Monitor VAD continuously]
  ↓ [If on_voice_start() detected]
  │ AND [debounce 50ms confirms voice]
  ↓
  Emit: on_interrupt_detected()
  Signal: stop_tts = True
  ↓ [TTS Pipeline receives stop signal]
  ↓ [TTS immediately stops, clears queue]
```

**Outputs:**
- Event: `on_interrupt_detected()`
- Triggers: TTS halt, back to STT pipeline

**Latency:** <100ms from user voice to TTS halt
- VAD detects voice: 10ms
- Debounce confirmation: 50ms
- Event routing: <20ms
- TTS halt: <20ms

**Key Design:**
- **Hard interrupt:** Discard current TTS response, don't resume
- **Debouncing:** 50ms wait to reduce false positives (breath sounds)
- **Priority:** Preempts LLM token streaming
- **State safe:** Returns to listening mode immediately

---

### 7. TTS Pipeline

**Files:** `src/tts/sarvam_tts_client.py`, `src/tts/tts_pipeline.py`

**Inputs:**
- Event: `on_response_chunk(token)` from LLM
- Or: `on_response_complete(full_response)` if waiting for complete response

**Processing:**
```
response_text (or tokens)
  ↓ [Collect tokens until: sentence_boundary OR 5-10 word buffer]
text_chunk = "...ಇದೆ ಮೇಲೆ ಏನು ಮಾಡಬಹುದು?"
  ↓ [SarvamTTSClient]
  │ - WebSocket: wss://api.sarvam.ai/v1/tts
  │ - Message: { "text": text_chunk, "language": "kannada" }
  ↓
audio_stream (24kHz mono PCM)
  ↓ [Begin playback immediately (time-to-first-byte)]
Emit: on_audio_chunk(chunk) → AudioOutputHandler
  ↓
Emit: on_playback_complete() [when all audio sent]
  ↓ [Monitor: interrupt_signal?]
  ├─ If interrupt during playback:
  │  └─ Abort, discard remaining audio, return to STT
  └─ If no interrupt:
     └─ Wait for next LLM token or response_complete
```

**Outputs:**
- Event: `on_audio_chunk(chunk: bytes)` (streaming to output)
- Event: `on_playback_complete()` (turn completed)

**Latency:** ~80ms to first audio byte, ~50-100ms per subsequent chunk

**Data Structures:**
```python
@dataclass
class TTSRequest:
    text: str
    language: str  # "kannada" or "english"
    voice_id: str  # Optional: specific voice preference

@dataclass
class TTSResponse:
    audio_chunk: bytes  # 24kHz mono PCM
    duration: float     # Duration of this chunk (ms)
```

**Interruptible Design:**
- Queue continuously monitored for `stop_signal`
- On interrupt: clear queue, stop receiving from LLM
- No resume: hard stop, return to IDLE state

**Key Design:**
- **Streaming:** Audio begins playback before full response generated
- **Interruptible:** Monitors interrupt flag continuously
- **Time-to-first-byte:** ~80ms (critical for perceived latency)
- **Queue buffering:** 5-10 word buffer to smooth LLM token rate variation

---

### 8. Context Manager

**Files:** `src/llm/context_manager.py`

**Inputs:**
- Event: agent adds turn `add_turn(speaker, content)`

**Processing:**
```
Conversation History (deque, max_size=10):
  [
    {"role": "user", "content": "ನಾನು..."},
    {"role": "assistant", "content": "ನೀವು..."},
    ...
    {"role": "user", "content": current_message}
  ]

When max capacity reached:
  pop oldest turn (FIFO)
```

**Outputs:**
- `get_context()` → List[Dict[role, content]]
- Format: API-ready for LLM (Groq expects this exact format)

**Latency:** <1ms (in-memory deque)

**Data Structure:**
```python
@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str  # Transcript or LLM response
    timestamp: float  # For debugging
    language: str  # Detected language (Kannada/English)
    duration: float  # Audio/response duration (optional)
```

**Reset Triggers:**
- User explicitly says "start over" (detected in LLM context)
- >10 minutes inactivity (timeout)
- Manual reset via UI button

**Key Design:**
- Deque with max_size (FIFO, drop oldest)
- Preserves conversation coherence
- No persistence (local memory only)
- Efficient for LLM context building

---

## State Machine

### State Definitions

| State | Meaning | Valid Inputs | Actions |
|-------|---------|--------------|---------|
| **IDLE** | Listening for button press, waiting for activation | on_button_press | → LISTENING |
| **LISTENING** | Button pressed, waiting for user speech | VAD on_voice_start | → LISTENING (no change) |
| | | VAD on_voice_end + pause | → PROCESSING_TURN |
| | | on_button_release | → IDLE |
| **PROCESSING_TURN** | Audio buffer collected, starting STT | stt_start | → STT_IN_PROGRESS |
| | | timeout (>2s) | → ERROR |
| **STT_IN_PROGRESS** | Speaking to speech, waiting for transcript | on_transcript_ready | → LLM_IN_PROGRESS |
| | | timeout (>2s) | → ERROR |
| **LLM_IN_PROGRESS** | Generating response, streaming tokens | on_response_chunk | → SPEAKING |
| | | on_response_complete | → SPEAKING |
| | | timeout (>3s) | → ERROR (with recovery) |
| **SPEAKING** | Playing TTS audio response | audio_playback ongoing | → SPEAKING |
| | | on_voice_start (interrupt) | → INTERRUPTED |
| | | on_playback_complete | → LISTENING |
| **INTERRUPTED** | User spoke during TTS, halt and process new input | tts_halt complete | → PROCESSING_TURN |
| **ERROR** | Recoverable error occurred | error recovery | → IDLE (after cooldown) |

### State Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                        IDLE                                    │
│  (Waiting for button press)                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                    on_button_press
                          │
                          ↓
┌───────────────────────────────────────────────────────────────┐
│                     LISTENING                                  │
│  (Awaiting user speech)                                        │
│  - VAD monitoring: is_speaking                                 │
│  - Accumulating audio buffer                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
            on_voice_end + pause_timeout
                          │
                          ↓
┌───────────────────────────────────────────────────────────────┐
│                  PROCESSING_TURN                               │
│  (Preparing STT)                                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                     stt_start
                          │
                          ↓
┌───────────────────────────────────────────────────────────────┐
│                 STT_IN_PROGRESS                               │
│  (Speaking-to-Text)                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                 on_transcript_ready
                          │
                          ↓
┌───────────────────────────────────────────────────────────────┐
│                 LLM_IN_PROGRESS                               │
│  (Generating Response)                                         │
│  - Streaming tokens to TTS queue                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
            on_response_chunk OR on_response_complete
                          │
                          ↓
┌───────────────────────────────────────────────────────────────┐
│                      SPEAKING                                  │
│  (TTS Playback)                                                │
│  - Audio flowing to speaker                                    │
│  - Interrupt handler monitoring VAD                            │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ IF on_voice_start + VAD on:                            │   │
│  │   → INTERRUPTED (hard stop TTS)                        │   │
│  └────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ IF on_playback_complete:                               │   │
│  │   → LISTENING (back to listening)                      │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
           ┌──────────────┴──────────────┐
           │                             │
        INTERRUPTED              LISTENING
           │
           ↓
    PROCESSING_TURN (new input)
```

### Timeout Handling

| State | Timeout | Action |
|-------|---------|--------|
| PROCESSING_TURN | 5s | → ERROR (audio too long) |
| STT_IN_PROGRESS | 2s | → ERROR (STT API timeout) |
| LLM_IN_PROGRESS | 3s | → ERROR (LLM API timeout, but allow recovery) |
| SPEAKING | None (audio-driven) | Complete when playback finishes |
| ERROR | Auto-recovery | Wait 500ms, then → IDLE |

### Error Recovery

**Transient Errors (retry):**
1. STT timeout → Retry with backoff (100ms, 200ms, 500ms)
2. LLM timeout → Respond "I'm still thinking..." + continue
3. TTS timeout → Skip TTS, return to LISTENING with message "Audio unavailable"

**Non-Recoverable Errors:**
1. No audio from WebRTC → Fallback: "Please check your audio input"
2. Invalid API key → Log and exit (requires manual restart)
3. Out of memory → Log, trigger GC, try recovery

---

## Async/Concurrency Model

### Event Loop Architecture

**Framework:** Python `asyncio` (single event loop)

**Components:**
```
┌─────────────────────────────────────────────────────────┐
│           Main Async Event Loop (asyncio)               │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ async functions:                                 │  │
│  │ - audio_input_listener()                         │  │
│  │ - state_machine_runner()                         │  │
│  │ - stt_processor()                                │  │
│  │ - llm_processor()                                │  │
│  │ - tts_processor()                                │  │
│  │ - interrupt_monitor()                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  I/O Bound: All WebSocket/HTTP calls async             │
│  (awaits for Sarvam AI, Groq)                          │
└─────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────┐
│     Separate Thread (CPU-Bound VAD Processing)          │
│                                                          │
│  vad_processor_thread():                                │
│    - Runs webrtc-vad algorithm (CPU-intensive)         │
│    - 10ms frame rate                                    │
│    - Emits events via thread-safe queue                │
│    - Main loop picks up events (non-blocking)          │
└─────────────────────────────────────────────────────────┘
```

### Concurrency Patterns

**Pattern 1: Event-Driven Communication**
```python
# Component A emits event
event_bus.emit("on_voice_start")

# Component B listens
event_bus.on("on_voice_start", callback=handler())

# Handler is called immediately (non-blocking)
```

**Pattern 2: Task Concurrency**
```python
# Run multiple tasks in parallel
await asyncio.gather(
    audio_input_task(),
    interrupt_monitor_task(),
    state_machine_task(),
)

# All run concurrently on single event loop
```

**Pattern 3: Queue-Based Streaming**
```python
# TTS producer: streams audio chunks to queue
queue.put(audio_chunk)

# Audio output consumer: reads from queue continuously
while True:
    chunk = await queue.get()
    await speaker.play(chunk)
```

### Thread Safety

**VAD Processing (CPU-Bound):**
```python
# Main thread:
vad_queue = asyncio.Queue()

# VAD thread:
while True:
    frame = audio_buffer.get_frame()  # Blocking read
    is_voice = vad_engine.process(frame)  # CPU work
    vad_queue.put(("on_voice" if is_voice else "off"))

# Main thread:
async def monitor_vad():
    while True:
        status = await vad_queue.get()  # Non-blocking get
        handle_vad_event(status)
```

**Benefits:**
- VAD runs at full speed (no throttling)
- Main loop responsive (can handle I/O)
- No locks needed (queue is thread-safe)

---

## Error Handling Strategy

### Error Categories

| Category | Examples | Recovery |
|----------|----------|----------|
| **Transient** | Network timeout, API rate limit, WebRTC reconnect | Retry with exponential backoff |
| **Recoverable** | LLM timeout, audio buffer overflow | Fallback response, continue |
| **Non-Recoverable** | Invalid API key, audio device failure, memory critical | Log, exit gracefully |

### Retry Strategy

**Exponential Backoff with Jitter:**
```
Attempt 1: Wait  100ms + random(0, 50ms)
Attempt 2: Wait  200ms + random(0, 50ms)
Attempt 3: Wait  500ms + random(0, 50ms)
Attempt 4: Wait 1000ms + random(0, 50ms)
Attempt 5: Fail → Fallback response
```

**Per-Component Retry Settings:**
```python
STT: max_retries=3, initial_wait=100ms
LLM: max_retries=2, initial_wait=200ms
TTS: max_retries=2, initial_wait=100ms
```

### Fallback Responses

| Failure Point | Fallback Response (Kannada) |
|---------------|---------------------------|
| STT Timeout | "ಕ್ಷಮಿಸಿ, ನಾನು ಸುಂದರವಾಗಿ ಆಲಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಹೇಳಿ" (Sorry, didn't hear clearly. Please repeat.) |
| LLM Timeout | "ನನ್ನನ್ನು ಕ್ಷಮಿಸಿ, ನಾನು ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ..." (Excuse me, I'm thinking...) |
| TTS Failure | [Return to LISTENING silently, log error] |
| Audio Device | "ನಿಮ್ಮ ಆಡಿಯೋ ಸಾಧನವನ್ನು ಪರಿಶೀಲಿಸಿ" (Check your audio device) |

---

## Data Types & Contracts

### Core Data Classes

```python
# Audio
@dataclass
class AudioChunk:
    data: bytes  # PCM audio
    sample_rate: int  # 16000 for STT input
    channels: int  # 1 for mono
    bit_depth: int  # 16
    timestamp: float  # Unix time

# Speech
@dataclass
class SpeechSegment:
    audio: bytes
    language: str  # "kannada" | "english"
    duration: float  # seconds
    confidence: float  # 0.0-1.0

# Text
@dataclass
class TranscriptResult:
    text: str
    language: str
    confidence: float

# Conversation
@dataclass
class ConversationMessage:
    role: str  # "user" | "assistant"
    content: str
    timestamp: float
    language: str
```

### Event Types

```python
# Events emitted by components
Event = Union[
    AudioChunkEvent,        # (audio, timestamp)
    VoiceStartedEvent,      # ()
    VoiceEndedEvent,        # ()
    TurnCompleteEvent,      # (audio_buffer)
    TranscriptReadyEvent,   # (transcript, language)
    ResponseChunkEvent,     # (token)
    ResponseCompleteEvent,  # (full_response)
    AudioChunkEvent,        # (audio_chunk)
    PlaybackCompleteEvent,  # ()
    InterruptDetectedEvent, # ()
    ErrorEvent,             # (error, context)
]
```

---

## Security & Privacy Boundaries

### Data Flows

**On-Device (local machine):**
- ✅ Audio captured from WebRTC
- ✅ Audio resampling and buffering
- ✅ VAD detection (audio discarded after analysis)
- ✅ Conversation history (in-memory)
- ✅ State machine coordination

**External (sent to APIs):**
- ⚠️ Audio → Sarvam AI STT (for transcription, discarded by Sarvam)
- ⚠️ Transcript + Context → Groq LLM (for inference, no logging per Groq free tier)
- ⚠️ Text → Sarvam AI TTS (for synthesis, discarded by Sarvam)

**Never Stored:**
- ❌ Audio recordings (not persisted to disk)
- ❌ Conversation logs (in-memory only, lost on exit)
- ❌ User telemetry (no analytics tracking)
- ❌ IP addresses or identifiers (local device only)

### API Key Management

**Storage:**
```
.env (git-ignored):
SARVAM_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

**Loading:**
```python
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("SARVAM_API_KEY")
```

**Never:**
- ❌ Log API keys
- ❌ Commit .env to git
- ❌ Print configuration (print statements filtered)
- ❌ Include keys in error messages

---

## Reference: Component Dependencies

```
AudioInputHandler
  ↓
AudioResampler
  ├→ VADEngine
  ├→ AudioBuffer
  └→ TurnDetector
       ↓
    STTPipeline
       ↓
    ContextManager (reads)
       ├→ LLMPipeline
       │    └→ (ContextManager updates)
       │
       └→ TTSPipeline
            ├→ InterruptHandler (monitors VAD)
            └→ AudioOutputHandler

StateMachine (coordinates all events)
```

---

## Next Steps

- See **ai_rules.md** for quality standards and optimization techniques
- See **plan.md** for step-by-step implementation roadmap

---

