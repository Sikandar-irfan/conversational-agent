# Product Requirements Document (PRD)
## Kannada Voice Conversational Agent

**Version:** 1.0
**Date:** March 2025
**Status:** Active Development
**Language Support:** Kannada (Primary) + English (Secondary)
**Use Case:** Customer Service

---

## Executive Summary

This document defines a real-time conversational voice agent for customer service interactions in Kannada, optimized for sub-500ms end-to-end latency through streaming-first pipeline architecture. The agent listens for user activation via UI button press, detects speech in real-time, transcribes to text using Sarvam AI STT, generates responses via Groq LLM, and synthesizes speech back using Sarvam AI TTS. Hard interrupts allow users to cut off agent responses immediately and provide new input. The system maintains conversation context (last N turns) to enable coherent, relevant responses within the bounds of a local development machine.

**Key Differentiators:**
- Always-on VAD-based listening (no explicit wake word, but manual activation via button)
- Hard interrupt handling: user speech immediately halts agent response
- Streaming-first architecture: reduces perceived latency vs. batch processing
- Kannada-optimized: native Kannada STT/TTS, natural Kannada LLM responses
- Customer service focused: professional tone, solution-oriented, quick resolution

---

## What The Agent IS

### 1. Real-Time Voice Conversation System

The agent engages in voice-based conversations with end users in Kannada and English. It:
- Receives continuous audio input from user via WebRTC once activated
- Processes audio in real-time (streaming chunks, not batch)
- Responds verbally within <500ms perceived latency (time from user pause to first TTS audio)
- Maintains natural conversation flow with minimal delays and smooth handoffs

**Scope:** Single user, single conversation, no multi-party dialogue.

### 2. Pipeline-Driven Architecture

The agent processes user input through a well-defined sequential pipeline:

```
User Audio Input → VAD (Voice Detection)
                 → Turn Detection (Pause-based End-of-Speech)
                 → Audio Buffering
                 → STT (Speech-to-Text via Sarvam AI)
                 → LLM (Response Generation via Groq)
                 → TTS (Text-to-Speech via Sarvam AI)
                 → Audio Output
                 → [Interrupt Handler monitors during TTS]
```

Each stage has well-defined inputs/outputs and operates asynchronously. Pipeline state is managed by a finite state machine (IDLE → LISTENING → PROCESSING → SPEAKING → back to IDLE). Clear separation of concerns enables testing each component independently.

### 3. Context-Aware Conversationalist

The agent maintains conversation history to generate coherent, contextually-relevant responses:
- Stores last N turns (default 10 turns = 5 user + 5 agent exchanges)
- Includes context turns in LLM prompt to enable multi-turn dialogue
- Tracks customer issue across conversation for resolution-focused responses
- Clears context on user explicit request or after >10 minutes of inactivity
- Context stored in-memory only (local machine, no persistence)

### 4. Manual Activation (Button-Press Listening)

The agent operates in manual activation mode for customer service:
- **UI Button Trigger:** User clicks button in UI to start listening
- **Active Period:** Once activated, agent continuously listens for speech
- **Automatic Turn Detection:** VAD + pause detection automatically identifies when user finishes speaking
- **State Transition:** After user speech detected and processed, agent returns to listening (awaits next user input or deactivation)
- **No Wake Word:** Unlike "Alexa" or "Google Assistant," no voice wake word is required

**Why Manual Activation:** Better for customer service (clear start/end of conversation), avoids false positives, reduces always-on CPU usage.

### 5. Hardware-Agnostic Audio via LiveKit WebRTC

The agent uses industry-standard WebRTC for audio I/O:
- **Audio Input:** Receives audio from user's microphone via WebRTC (typically 48kHz stereo from browser/client)
- **Audio Output:** Sends agent responses to user's speakers via WebRTC
- **Format Conversion:** Automatically resamples 48kHz stereo → 16kHz mono for STT, 24kHz for TTS
- **Device Agnostic:** Works with any WebRTC-capable client (browser, mobile app, desktop client)
- **No Audio File I/O:** Zero disk access for audio (all streaming), faster and more private

### 6. Streaming-First Implementation

All components process data in real-time chunks, not batch:
- **STT:** Receives audio in 160ms chunks, returns partial transcripts incrementally
- **LLM:** Streams response tokens as generated (~50-100ms per token), not waiting for full response
- **TTS:** Returns audio chunks immediately as synthesized, begins playback before full response generated
- **Latency Benefit:** User perceives faster response (hears agent speak sooner, doesn't wait for batch completion)

---

## What The Agent ISN'T

### 1. Not Cloud-Based

- All processing occurs on **local development machine** only
- Data never leaves local machine except for API calls to Sarvam AI (STT/TTS) and Groq (LLM)
- No distributed processing, no multi-server coordination
- Not designed for horizontal scaling or cloud deployment
- Privacy-centric: conversation history, user audio, and context remain on device

### 2. Not a General-Purpose Voice Assistant

- **No smart home integration** (can't control lights, thermostats, etc.)
- **No arbitrary command execution** (can't "play Spotify" or "set a reminder")
- **No information retrieval** (no Wikipedia lookup, weather API, flight bookings)
- **No natural language understanding for command intent** (doesn't parse "remind me in 2 hours" as a command)
- **Limited to conversational dialogue** (chat-based interaction only)

### 3. Not a Voice Application Framework

- Not a platform for building voice apps on top
- Not providing SDKs or APIs for third-party voice plugins
- Single-purpose conversational interface, not extensible for other use cases
- Not designed to host multiple independent voice applications

### 4. Not Supporting Multi-Party or Multi-Session Conversations

- Single user, single agent only (no group conversations or virtual meetings)
- One active conversation at a time (no session management for multiple concurrent users)
- No speaker identification or authentication
- Not designed for enterprise multi-tenant scenarios

### 5. Not Handling Advanced Audio Processing

- **No noise cancellation** (agent receives user audio as-is from microphone)
- **No speaker diarization** (can't determine "who said what" in multi-speaker scenarios)
- **No emotion detection** (doesn't analyze sentiment or stress in user's voice)
- **No acoustic feature extraction** (no speaker characteristics analysis)
- **No echo cancellation** (relies on OS/WebRTC, not custom implementation)

### 6. Not Production-Grade

- Development/PoC tool, not intended for production deployment
- No scalability guarantees (single-machine resource constraints apply)
- No SLA commitments (best-effort, local machine failures = system failure)
- No formal uptime targets or reliability guarantees
- Limited monitoring and alerting capabilities
- Designed for developer iteration, not customer-facing production systems

---

## Scope Definition

### In Scope

**Core Functionality:**
- ✅ WebRTC audio I/O integration via LiveKit
- ✅ Voice Activity Detection (VAD) for continuous listening
- ✅ End-of-speech detection via pause heuristics (configurable pause duration, default 800ms)
- ✅ Sarvam AI Bulbul STT in Kannada + English with automatic language detection
- ✅ LLM inference (Groq recommended, alternative high-performance provider acceptable)
- ✅ Hard interrupt handling: user speech during TTS immediately halts and restarts conversation flow
- ✅ Conversation memory management (last N turns, in-memory deque)
- ✅ Streaming TTS output with real-time interrupt routing

**Language & Localization:**
- ✅ Kannada speech recognition and synthesis (primary language)
- ✅ English speech recognition and synthesis (secondary language, fallback)
- ✅ Automatic language detection (analyzes first 3-5 words)
- ✅ System prompts and responses in detected language
- ✅ Kannada customer service tone and terminology

**Error Handling & Robustness:**
- ✅ Transient error retry with exponential backoff
- ✅ API timeout handling (2-3 seconds per service)
- ✅ Graceful degradation (fallback responses vs. crashes)
- ✅ State machine prevents race conditions
- ✅ Comprehensive error logging with context

**Performance & Optimization:**
- ✅ <500ms end-to-end latency target (VAD + STT + LLM + TTS)
- ✅ Streaming optimization to reduce perceived latency
- ✅ Interrupt response <100ms (from user speech to TTS halt)
- ✅ Memory-efficient audio buffering
- ✅ Async/await throughout (non-blocking I/O)

### Out of Scope

**Language & Localization:**
- ❌ Speech recognition beyond Kannada and English
- ❌ Multi-language conversations in single turn (pick one language per session)
- ❌ Language-specific grammar correction or spell-checking
- ❌ Accent adaptation or personalization

**Advanced Audio Processing:**
- ❌ Acoustic noise cancellation (Wiener filtering, spectral subtraction, etc.)
- ❌ Speaker identification or biometric authentication
- ❌ Emotion or stress detection from voice
- ❌ Speech synthesis voice cloning or personalization
- ❌ Multi-speaker diarization ("Speaker 1 said X, Speaker 2 said Y")

**Data & Persistence:**
- ❌ Conversation history persistence (no database, SQL, file storage)
- ❌ User profile or session persistence
- ❌ Audio recording or log file archival
- ❌ Analytics or telemetry beyond local performance metrics

**Natural Language Processing:**
- ❌ Named entity recognition (NER) - extracting names, places, organizations
- ❌ Intent classification beyond conversational context (no "book flight" command detection)
- ❌ Sentiment analysis or opinion mining
- ❌ Information extraction or knowledge base integration
- ❌ Custom domain-specific language models

**Deployment & Infrastructure:**
- ❌ Cloud deployment (AWS, GCP, Azure)
- ❌ Containerization (Docker) or orchestration (Kubernetes)
- ❌ Distributed processing or horizontal scaling
- ❌ High availability or redundancy
- ❌ Monitoring dashboards or real-time alerting systems

---

## Key Constraints

### Technical Constraints

#### 1. Latency Budget (<500ms Perceived)

Perception includes speech production duration, so visible latency breakdown:

| Component | Budget | Typical | Notes |
|-----------|--------|---------|-------|
| VAD | <50ms | ~10ms | Per-frame processing, minimal overhead |
| Pause Detection | <100ms | ~800ms | Includes required pause wait time |
| STT (Sarvam AI) | <200ms | ~180ms | WebSocket streaming, Kannada optimized |
| LLM (Groq) | <150ms | ~120ms | First token latency, streaming the rest |
| TTS (Sarvam AI) | <100ms | ~80ms | Time to first audio byte |
| Pipeline Overhead | <50ms | ~30ms | Buffering, event routing, state transitions |
| **Total (excluding pause)** | **<650ms** | **~500ms** | |
| **Total (with 800ms pause)** | **~1.45s** | **~1.3s** | User wait is pause, agent response is 650ms |

**Key Insight:** Total wall-clock time includes 800ms pause wait (user finishing speech). Agent's actual response latency is ~500ms, which feels natural.

#### 2. Memory Constraints

| Resource | Limit | Justification |
|----------|-------|---------------|
| Conversation History | 10 turns (~50KB) | Sufficient for customer service context, prevents infinite growth |
| Audio Buffers | 3-4 seconds of 16kHz mono PCM (~100KB) | Standard for turn-by-turn conversation |
| LLM Model Weights | 2-4GB RAM (local) or API-based | Must fit on mid-range GPU or use external API |
| VAD State | <1KB | Minimal buffer, frame-by-frame processing |
| TTS Queue | 5-10 words (~5KB) | Buffer against LLM token rate variation |

**Implication:** Local models (Ollama) must be <4GB; for larger models, use Groq API (external).

#### 3. Real-Time Requirement

- **Non-blocking I/O:** All operations async (Python asyncio)
- **No UI Freezing:** Audio processing never blocks user interface
- **Concurrent Execution:** VAD processing in separate thread (CPU-bound), main event loop handles I/O
- **Priority Interrupt:** Hard interrupt has highest priority (preempts LLM, TTS)
- **No Batch Processing:** Single-turn processing only, no accumulation of requests

#### 4. Audio Format Requirement

| Stage | Format | Justification |
|-------|--------|---------------|
| WebRTC Input | 48kHz stereo (browser default) | Standard for web audio |
| STT Input | 16kHz mono PCM | Sarvam AI requirement |
| TTS Output | 24kHz mono PCM | Sarvam AI TTS output |
| Resampling | Real-time via librosa/scipy | Automatic conversion on playback |

**Note:** Audio format conversion must happen in real-time (no pre-processing delays).

### Business Constraints

#### 1. Local Development Only

- **Deployment Model:** Single machine (laptop/desktop with GPU)
- **User Base:** Single developer/user (not multi-tenant)
- **Cost Model:** Personal project, minimize recurring costs (API usage)

#### 2. Cost Efficiency

- **Sarvam AI:** Choose appropriate tier (free vs. paid) based on usage
- **Groq:** Free tier available with rate limits (~10 requests/min); upgrade if needed
- **Alternative:** Ollama (self-hosted, no API costs) for local LLM inference
- **Infrastructure:** No paid cloud services required (all local)

#### 3. Privacy & Data Minimization

- **No Persistent Storage:** Conversation data never saved to disk
- **No Telemetry:** No tracking or analytics (except local performance metrics)
- **API Trade-off:** OK to send audio to Sarvam AI and prompts to Groq (accepting external processing for STT/TTS/LLM)
- **No Third-Party Tracking:** No GA, Sentry, or user tracking

---

## Success Metrics

### Quantitative Metrics

#### Latency Targets
- **End-to-End Latency:** <500ms (measured from user end-pause to first TTS audio output), 95th percentile <600ms
- **STT Latency:** <300ms per turn (STT accuracy <200-250ms typical for Kannada)
- **LLM Latency:** <200ms to first token, <50ms per subsequent token
- **TTS Latency:** <150ms to first audio byte
- **Interrupt Response:** <100ms from user voice resumption to TTS halt

#### Accuracy & Quality
- **STT Accuracy:** >90% word error rate (WER) for Kannada, measured on representative customer service phrases
- **Context Coherence:** >95% of responses reference prior conversation (subjective evaluation)
- **Response Relevance:** >90% on-topic responses (measured via prompt → response similarity >0.5)

#### Reliability
- **Error Rate:** <5% per component per hour (acceptable transient errors)
- **Crash Rate:** 0% (graceful error handling, no unhandled exceptions)
- **API Timeout Rate:** <1% (errors recovered, retried automatically)

### Qualitative Metrics

- **Responsiveness Perception:** User perceives agent as responsive, not "thinking"
- **Interrupt Naturalness:** User feels interrupts are smooth (no audio glitches or repeated words)
- **Conversation Flow:** Dialogue feels natural without awkward pauses or dead silence
- **Kannada Quality:** Agent responses sound natural in Kannada, not machine-generated or translated
- **Customer Service Quality:** Agent is helpful, professional, solution-oriented

---

## Assumptions & Dependencies

### Technology Assumptions

| Assumption | Reason | Risk |
|-----------|--------|------|
| Python 3.10+ available | Development language, async/await required | **Low** - Python widely available |
| Sarvam AI API accessible | STT/TTS provider chosen | **Medium** - API availability, rate limits |
| Groq API accessible | LLM provider recommended | **Medium** - API availability, rate limits |
| LiveKit server available | WebRTC infrastructure | **Low** - Self-hosted or cloud option available |
| OS-level audio accessible | WebRTC audio I/O | **Low** - Standard cross-platform support |
| GPU (optional) available | For local LLM (Ollama) | **Low** - OK to use Groq API instead |

### Integration Assumptions

| Assumption | Reason | Risk |
|-----------|--------|------|
| Sarvam AI WebSocket stable | API stability and uptime | **Medium** - Document API contracts, fallbacks |
| Groq rate limits permissive | Free tier supports real-time conversation | **Medium** - May need paid tier for high usage |
| LiveKit WebRTC reliable | Audio streaming quality | **Low** - WebRTC battle-tested, stable |
| Network latency <100ms | Local WebRTC path | **Low** - Typical local network performance |
| Kannada model availability | Groq/LLM has Kannada support | **Medium** - Verify LLM language coverage |

---

## Out-of-Scope Items (Documented for Reference)

**The following features are explicitly NOT included but may be useful for future iterations:**
- Wake word detection ("Hey Agent" trigger)
- Always-on listening without button press
- Persistent conversation logs
- Advanced NLP (NER, intent classification)
- Multi-party conversation support
- Voice cloning or speech synthesis customization
- Sentiment analysis or emotion detection
- Cloud deployment with scaling
- Speech-to-speech translation (cross-language)
- Integration with CRM or ticketing systems

---

## Document Map

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **prd.md** (this doc) | Define scope, requirements, constraints | To understand WHAT the agent is/isn't |
| **architecture.md** | Design file structure, data flow | To understand HOW the system is organized |
| **ai_rules.md** | Quality standards, optimization rules | To understand QUALITY standards |
| **plan.md** | Step-by-step implementation roadmap | To understand WHEN/HOW to build it |

---

## Approval & Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | Srihari K S | 2025-03-19 | ✓ |
| Technical Lead | Claude Code | 2025-03-19 | ✓ |

---

## Change Log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2025-03-19 | Claude Code | Initial PRD: Kannada voice agent, customer service, <500ms latency |

---
