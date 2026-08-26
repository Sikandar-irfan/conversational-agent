# AI Quality Control & Optimization Rules
## Kannada Voice Conversational Agent

**Version:** 1.0
**Date:** March 2025
**Purpose:** Maintain response quality, optimize latency, ensure Kannada fluency

---

## Table of Contents

1. [Response Quality Standards](#response-quality-standards)
2. [Prompt Engineering & Language Rules](#prompt-engineering--language-rules)
3. [Latency Optimization Targets](#latency-optimization-targets)
4. [Streaming Optimization Techniques](#streaming-optimization-techniques)
5. [Error Recovery Rules](#error-recovery-rules)
6. [Conversation Context Management](#conversation-context-management)
7. [Interrupt Handling Rules](#interrupt-handling-rules)
8. [Performance Monitoring & Alerting](#performance-monitoring--alerting)
9. [Kannada-Specific Quality Rules](#kannada-specific-quality-rules)

---

## Response Quality Standards

### 1. Coherence Rules

**Requirement:** All responses must make logical sense within the conversation context.

**Checking:**
- ✅ Reference prior turns explicitly (e.g., "You mentioned earlier that..." or "ನೀವು ಮೊದಲೇ ಹೇಳಿದ್ದರಿಂದ...")
- ✅ No contradictions with previous agent responses (track reasoning consistency)
- ✅ Pronouns resolved correctly ("he/she/they" must refer to named entities from recent turns)
- ❌ Don't generate responses that contradict earlier advice
- ❌ Don't switch tone (professional → casual) without explanation

**Implementation:**
```python
def check_coherence(current_response, conversation_history):
    """
    Verify response makes sense given prior context.
    """
    # Check: mentions previous turn subject?
    last_user_turn = conversation_history[-2]["content"]
    similarity = cosine_similarity(current_response, last_user_turn)

    if similarity < 0.3:
        # Low relevance, might be off-topic
        log_warning(f"Low coherence: {similarity:.2f}")

    return similarity > 0.3
```

**Quality Threshold:**
- Minimum coherence score: 0.3 (cosine similarity)
- If below threshold: flag for manual review

---

### 2. Relevance Rules

**Requirement:** Responses must directly address the user's question or concern.

**Checking:**
- ✅ >90% of response body relates to user's latest message
- ✅ First sentence directly answers question (don't bury answer in later sentences)
- ❌ Don't include unrelated information (e.g., company history when user asks about pricing)
- ❌ Don't go off-topic (e.g., weather when discussing account issues)

**Customer Service Specifics:**
- ✅ Lead with solution or status (e.g., "ನಿಮ್ಮ ಸಮಸ್ಯೆ ಇದೆ: [problem]. ಶುದ್ಧೀಕರಿಸಲು ಹೀಗೆ ಮಾಡಿ: [steps]")
- ✅ Acknowledge customer concern ("ನೀವು ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿ ವಿಳಂಬ ಎದುರಿಸುತ್ತಿದ್ದೀರಿ ಎಂಬುದು ನನಗೆ ತಿಳಿದಿದೆ")
- ❌ Don't dismiss concerns ("That's not a real problem")
- ❌ Don't over-apologize (one concise apology, then solution)

**Implementation:**
```python
def check_relevance(user_query, response_text):
    """
    Verify response addresses user query.
    """
    query_embedding = embed(user_query)
    response_embedding = embed(response_text)

    cosine_sim = cosine_similarity(query_embedding, response_embedding)

    # Threshold: >0.5 similarity
    return cosine_sim > 0.5
```

---

### 3. Length Rules

**Requirement:** Responses appropriately sized for voice conversation.

**Targets:**
- **Optimal:** 20-50 words (~3-8 seconds TTS)
- **Minimum:** 5 words (e.g., "ಹೌದು, ಸಂಪೂರ್ಣವಾಗಿ. ಹೆಚ್ಚಿನ ಲಾಭ?")  = "Yes, absolutely. Anything else?"
- **Maximum:** 150 words (~10-15 seconds TTS)

**Truncation Rule:**
If LLM generates >150 words:
1. Find last sentence boundary (. ! ?) before 150-word limit
2. Truncate at that boundary
3. Don't append "[truncated]" or similar (feels unnatural)
4. Allow natural continuation in next turn

**Word Count Verification:**
```python
def enforce_length_limit(response_text, max_words=150):
    """
    Truncate response at sentence boundary if >max_words.
    """
    words = response_text.split()

    if len(words) <= max_words:
        return response_text

    # Find last sentence boundary within limit
    truncated = " ".join(words[:max_words])

    # Find last sentence-ending character
    for ending in ["।", "।", "।", ".", "!", "?"]:  # Kannada and English endings
        if ending in truncated:
            last_pos = truncated.rfind(ending)
            if last_pos > (max_words * 0.8):  # At least 80% of target
                return truncated[:last_pos + len(ending)]

    # Fallback: truncate at word boundary
    return truncated + "।"  # Kannada period
```

---

### 4. Tone Rules

**Requirement:** Responses maintain professional, friendly, solution-oriented customer service tone.

**Tone Characteristics:**
- ✅ **Friendly & Professional:** Respectful but not stiff ("ನೀನೆ ಈ ಸಮಸ್ಯೆಯಿಂದ ಬಿಡುಗಣಿಸಬಹುದು" = "You can get relief from this issue")
- ✅ **Solution-Focused:** Emphasize what can be done (not what can't)
- ✅ **Brief & Clear:** Use simple Kannada words, avoid jargon
- ✅ **Empathetic:** Acknowledge frustration without over-apologizing
- ❌ **Not Robotic:** Avoid "I am an AI assistant..." ("ನಾನು AI ಸಹಾಯಕರಿ" - never say this)
- ❌ **Not Dismissive:** Don't minimize customer concerns
- ❌ **Not Corporate-Speak:** Avoid buzzwords ("Let me circle back", "Reach out")

**Consistency:**
- Use same terminology across turns (don't call "debit card" "ನಿರ್ಗಮ ಕಾರ್ಡ" once and "debit card" later)
- Keep personality consistent (if friendly in turn 1, stay friendly in turn 5)

**Examples:**

Good:
```
ಬಳಕೆದಾರ: ನನ್ನ ಖಾತೆ ಏಕೆ ಲಾಕ್ ಆಗಿತ್ತು?
ಏಜೆಂಟ್: ನೀವು ತಪ್ಪು ಪಾಸ್‌ವರ್ಡ್ 3 ಬಾರಿ ನೀಡಿದ್ದೀರಿ, ಆದ್ದರಿಂದ ಸುರಕ್ಷೆಯರ್ಥ ಲಾಕ್ ಮಾಡಿದ್ದೇನೆ.
ಅದನ್ನು ಮುಕ್ತಗೊಳಿಸಲು, ನಿಮ್ಮ ಈಮೇಲ್ ಪರಿಶೀಲಿಸಿ ಮತ್ತು verify ಲಿಂಕ್ ಕ್ಲಿಕ್ ಮಾಡಿ.
[Simple, solution-focused]
```

Avoid:
```
ನಿಮ್ಮ ಖಾತೆ ಲಾಕ್ ಆಗಿದೆ ಏಕೆಂದರೆ ನೀವು ತಪ್ಪು ಪಾಸ್‌ವರ್ಡ್ ನೀಡಿದ್ದೀರಿ.
[Too terse, sounds accusatory]
```

---

## Prompt Engineering & Language Rules

### System Prompt Template (Kannada)

```
ನೀವು ಒಂದು ಸಹಾಯಕ, ರೆಸಲ್ಯೂಶನ್ ಮೇಲೆ ಕೇಂದ್ರೀಭೂತ ಗ್ರಾಹಕ ಸೇವಾ ಏಜೆಂಟ್ ಆಗಿದ್ದೀರಿ.
ಸಾಮೀಪ್ಯ ಅತಿ ಮುಖ್ಯ, ಸಂಬಂಧಿತ ಮತ್ತು ಸ್ಪಷ್ಟ ಪ್ರತಿಕ್ರಿಯೆಗಳನ್ನು ನೀಡಿ.
ಗ್ರಾಹಕನ ಚಿಂತೆಯನ್ನು ಮೊದಲಬಲ್ಲೆ ಗುರುತಿಸಿ, ನಂತರ ಪರಿಹಾರ ಮೊದಲಾಗಿ ನೀಡಿ.
ನೈಸರ್ಗಿಕ, ಸರಳ ಕನ್ನಡ ಬಳಸಿ. ಯಾಂತ್ರಿಕ ಭಾಷೆ ತಪ್ಪಿಸಿ.
[Optional domain instructions]

---
English Version (for English conversations):

You are a helpful, resolution-focused customer service agent.
Keep responses brief, relevant, and clear (20-50 words target).
Lead with empathy: acknowledge the customer's concern before offering solutions.
Use natural, conversational English. Avoid robotic phrases like "I am an AI assistant."
[Optional domain instructions]
```

### Conversation History Formatting

**Format:** JSON, role-based structure

```python
[
    {
        "role": "user",
        "content": "ನಾನು ನನ್ನ ಖಾತೆ ಅಸ್ತಿತ್ವ ಕಳೆದುಕೊಂಡೆ"
    },
    {
        "role": "assistant",
        "content": "ಕ್ಷಮಿಸಿ, ನೀವು ಪ್ರವೇಶ ನಷ್ಟಪಟ್ಟಿದ್ದೀರಾ? ನಿಮ್ಮೊಂದಿಗೆ ಪುನರುদ್ಧರಿಸಿದರೆ..."
    },
    {
        "role": "user",
        "content": "ಹೌದು, ನಾನು ನನ್ನ ಪಾಸ್‌ವರ್ಡ್ ಮರೆತೆ"
    }
]
```

**Building the Prompt:**

```python
def build_prompt(system_prompt, conversation_history, current_user_message, language="kannada"):
    """
    Build LLM prompt with context.
    """
    # 1. System prompt
    prompt = system_prompt

    # 2. Conversation history (last 4-6 turns)
    recent_turns = conversation_history[-10:]  # max 10 turns, 5 exchanges
    for turn in recent_turns:
        role_prefix = "ಗ್ರಾಹಕ:" if language == "kannada" else "Customer:"
        if turn["role"] == "user":
            role_prefix = "ಗ್ರಾಹಕ:" if language == "kannada" else "Customer:"
        else:
            role_prefix = "ಏಜೆಂಟ್:" if language == "kannada" else "Agent:"

        prompt += f"\n{role_prefix} {turn['content']}"

    # 3. Current user message
    prompt += f"\nಗ್ರಾಹಕ: {current_user_message}\nಏಜೆಂಟ್:"

    return prompt
```

**Context Window Rules:**
- **Default:** Last 10 turns (5 user + 5 agent)
- **Maximum:** 20 turns (token limits, cost)
- **Minimum:** 2 turns (current turn + last agent response)
- **Clear on:** Explicit user request ("ಪುನರಾರಂಭ" = reset), >10min inactivity, token limit exceeded

---

## Latency Optimization Targets

### Latency Budget Breakdown

| Component | Budget | Typical | Margin | Notes |
|-----------|--------|---------|--------|-------|
| **VAD Detection** | <50ms | ~10ms | ✅ Good | Per-frame processing |
| **Pause-Based Turn Detection** | <100ms | ~800ms + 50ms | ⓘ User-induced | Wait for 800ms pause, confirm with 50ms debounce |
| **STT (Sarvam AI)** | <200ms | ~180ms | ✅ Good | Kannada optimized, streaming chunks |
| **LLM (Groq) - First Token** | <150ms | ~120ms | ✅ Good | Streaming API, Kannada fluency |
| **LLM - Per Token (buffered)** | <100ms | ~50ms | ✅ Good | Parallel streaming to TTS |
| **TTS (Sarvam AI) - Time-to-First-Byte** | <100ms | ~80ms | ✅ Good | Begin playback immediately |
| **TTS - Per Chunk (queued)** | <100ms | ~50ms | ✅ Good | 24kHz audio streaming |
| **Pipeline Overhead** | <50ms | ~30ms | ✅ Good | Event routing, state transitions |
| **Interrupt Response (VAD to TTS Stop)** | <100ms | <50ms | ✅ Excellent | Hard interrupt priority |
| | | | | |
| **Total (Agent Latency, excl. pause)** | **<650ms** | **~500ms** | **✅ Good** | User perceives fast response |
| **Total (User Perceives, incl. pause)** | **~1.5s** | **~1.3s** | **✅ Natural** | 800ms pause + 500ms agent |

### Latency Optimization Techniques

#### 1. Input Buffering Optimization

**Technique:** Use smaller audio chunks for STT to reduce perceived latency

```python
# Bad: Wait for full turn, then send to STT
audio_buffer = []  # accumulate user speech
when turn_complete:
    stt.transcribe(audio_buffer)  # Send all at once

# Good: Stream chunks to STT as available
stt_input_queue = asyncio.Queue()
while listening:
    chunk = get_audio_chunk(160ms)  # 160ms chunks
    stt_input_queue.put(chunk)

# STT consumes incrementally
await stt.stream_chunks(stt_input_queue)
```

**Benefit:** STT begins processing before user finishes speaking, reduces perceived latency

#### 2. Streaming Output Optimization

**Technique:** Begin TTS playback before LLM finishes response

```python
# Bad: Wait for full LLM response, then start TTS
llm_response = await llm.generate(prompt)
audio = await tts.synthesize(llm_response)
await speaker.play(audio)

# Good: Stream LLM tokens to TTS queue immediately
tts_queue = asyncio.Queue()

async def llm_to_tts():
    async for token in llm.stream_tokens(prompt):
        tts_queue.put(token)  # Queue immediately

async def tts_from_queue():
    while True:
        token = await tts_queue.get()
        audio_chunk = await tts.synthesize_chunk(token)
        await speaker.play_chunk(audio_chunk)  # Start playback immediately

asyncio.create_task(llm_to_tts())
asyncio.create_task(tts_from_queue())
```

**Benefit:** User hears agent start speaking sooner (time-to-first-audio reduced)

#### 3. Context Caching

**Technique:** Pre-format context before LLM call to save 20-30ms

```python
# Cache formatted context
context_cache = {
    "formatted_history": format_conversation_history(conversation),
    "timestamp": time.time()
}

# Only rebuild if changed
if time.time() - context_cache["timestamp"] > 60:
    context_cache = rebuild_context()
```

#### 4. Parallel Processing

**Technique:** Process LLM tokens and TTS audio in parallel

```python
# Don't wait for full LLM response before starting TTS
llm_task = asyncio.create_task(llm.stream_tokens(...))
tts_input_queue = asyncio.Queue()

# Feed TTS queue from LLM stream
async def feed_tts():
    async for token in llm_task:
        await tts_input_queue.put(token)

# TTS processes independently
tts_task = asyncio.create_task(tts.synthesize_stream(tts_input_queue))
```

#### 5. Network Optimization

**Technique:** Keep websocket connections persistent, reuse for multiple requests

```python
# Bad: New connection per request
async def stt_transcribe(audio):
    ws = await websockets.connect("wss://api.sarvam.ai/...")
    await ws.send(audio)
    response = await ws.recv()
    await ws.close()
    return response

# Good: Connection pool
class SarvamSTTClient:
    def __init__(self):
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect("wss://api.sarvam.ai/...")

    async def transcribe(self, audio):
        await self.ws.send(audio)
        return await self.ws.recv()

    # Reuse connection across multiple requests
```

---

## Streaming Optimization Techniques

### STT Streaming

**Chunk Size:** 160ms of audio (16kHz × 0.16s × 2 bytes = 5,120 bytes)

```python
# Sarvam AI expects 160ms chunks
audio_chunk = audio_data[offset:offset+5120]
await stt_websocket.send(audio_chunk)

# Receives intermediate results (partial transcript)
partial = await stt_websocket.recv()  # "ಹಾಯ್"
partial = await stt_websocket.recv()  # "ಹಾಯ್, ನಾನು"
final = await stt_websocket.recv()    # "ಹಾಯ್, ನಾನು ಸಾಲದ ಮಾಹಿತಿ ಬೇಕು"
```

**Optimization:** Discard partials, only use final transcript on interrupt

### LLM Streaming

**Token Collection:**
1. Collect first 2-3 tokens before routing to TTS (reduces jitter)
2. Stream remaining tokens to TTS queue as they arrive

```python
llm_stream = groq_client.chat.completions.create(
    model="mixtral-8x7b-32768",
    messages=prompt,
    stream=True
)

tokens_buffer = []
async for chunk in llm_stream:
    token = chunk.choices[0].delta.content
    tokens_buffer.append(token)

    if len(tokens_buffer) >= 3:
        # Buffer has enough, start TTS
        text = "".join(tokens_buffer)
        await tts_input_queue.put(text)
        tokens_buffer = []

# Flush remaining tokens
if tokens_buffer:
    await tts_input_queue.put("".join(tokens_buffer))
```

**Benefit:** Smooths LLM token rate variation (some tokens come fast, some slow)

### TTS Streaming

**Immediate Playback:** Begin audio playback on first chunk

```python
tts_response = sarvam_tts_client.synthesize_stream(response_text)

first_chunk = await tts_response.recv()
# BEGIN PLAYBACK IMMEDIATELY
speaker_task = asyncio.create_task(speaker.play_chunk(first_chunk))

# Queue remaining chunks
async for chunk in tts_response:
    await speaker_queue.put(chunk)
```

**Latency Impact:** Reduces "time-to-first-audio" from LLM start to user hears agent

---

## Error Recovery Rules

### Transient Error Retry Logic

**Exponential Backoff with Jitter:**

```python
async def retry_with_backoff(func, max_retries=3):
    """
    Exponential backoff: 100ms, 200ms, 500ms, 1000ms
    """
    base_wait = 0.1  # 100ms
    for attempt in range(max_retries):
        try:
            return await func()
        except TransientError as e:
            if attempt >= max_retries - 1:
                raise

            wait_time = base_wait * (2 ** attempt)
            jitter = random.uniform(0, wait_time * 0.5)
            await asyncio.sleep(wait_time + jitter)
```

**Per-Component Retry Settings:**

| Component | Max Retries | Initial Wait | Max Wait | Timeout |
|-----------|------------|--------------|----------|---------|
| STT | 3 | 100ms | 1000ms | 2s |
| LLM | 2 | 200ms | 1000ms | 3s |
| TTS | 2 | 100ms | 500ms | 2s |
| WebSocket Connect | 5 | 100ms | 2000ms | 10s |

### Non-Recoverable Error Handling

**Error Categories:**

```python
# Recoverable: Retry
TransientError (timeout, rate limit, connection reset)

# Non-Recoverable: Fail-fast
class NonRecoverableError(Exception):
    pass

class InvalidAPIKeyError(NonRecoverableError):
    pass

class AudioDeviceError(NonRecoverableError):
    pass

class OutOfMemoryError(NonRecoverableError):
    pass
```

**Fallback Responses:**

| Failure | Fallback Response (Kannada) | Action |
|---------|----------------------------|--------|
| STT Timeout | "ಕ್ಷಮಿಸಿ, ನಾನು ಸುಂದರವಾಗಿ ಆಲಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಹೇಳಿ" | Retry STT |
| LLM Timeout | "ನನ್ನನ್ನು ಕ್ಷಮಿಸಿ, ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ..." | Respond with partial, allow continue |
| TTS Timeout | [No audio, return to LISTENING] | Log, skip response |
| Invalid API Key | Log error, exit | Manual restart required |
| Audio Device | "ನಿಮ್ಮ ಆಡಿಯೋ ಸಾಧನವನ್ನು ಪರಿಶೀಲಿಸಿ" | Prompt user to check |

---

## Conversation Context Management

### Context Window Rules

**Default Configuration:**
```python
max_turns = 10  # 5 user + 5 agent exchanges
min_context = 2  # Always include current turn + last response
token_limit = 4000  # Groq limit for free tier
```

**Context Building:**

```python
def build_context(conversation_history, current_turn):
    """
    Include last N turns, respecting token limit.
    """
    context = [current_turn]  # Always include latest

    # Add prior turns in reverse chronological order
    for turn in reversed(conversation_history[-20:]):
        potential_context = [turn] + context
        tokens = count_tokens(potential_context)

        if tokens < token_limit:
            context.insert(0, turn)
        else:
            break  # Hit token limit

    return context[:max_turns]  # Cap at max_turns
```

### Context Reset Triggers

**Explicit:**
- User says "ಪುನರಾರಂಭ" (restart), "ಹೊಸ ಗಿರಿ" (new conversation), "ಖಾತೆ ರಿಸೆಟ್" (reset account)

**Automatic:**
- >10 minutes of inactivity (timeout)
- Token limit exceeded (start fresh if resuming)
- Explicit API call: `context_manager.reset()`

**Implementation:**
```python
class ContextManager:
    def reset(self):
        self.turns.clear()
        self.last_activity = time.time()

    async def check_timeout(self):
        if time.time() - self.last_activity > 600:  # 10 min
            self.reset()
```

---

## Interrupt Handling Rules

### Interrupt Detection

**Trigger:** Any VAD `on_voice_start()` event during TTS playback

```python
if tts_active and vad.on_voice_start():
    # Debounce: wait 50ms to confirm
    await asyncio.sleep(0.05)
    if vad.is_speaking:
        emit("on_interrupt_detected")
```

**Debounce Duration:** 50ms (reduces false positives from breath sounds, background noise)

### Interrupt Response

**Hard Interrupt Protocol:**

1. **Immediate:** Stop TTS playback within 20ms
2. **Discard:** Clear TTS output queue, don't resume
3. **Clear:** Stop consuming LLM tokens
4. **Reset:** State machine returns to `PROCESSING_TURN`
5. **Reprocess:** New user speech treated as fresh input

```python
async def handle_interrupt():
    # 1. Stop TTS
    await tts_pipeline.halt()

    # 2. Clear queues
    tts_output_queue.clear()

    # 3. Disconnect LLM streaming
    await llm_task.cancel()

    # 4. Reset state
    state_machine.transition_to("PROCESSING_TURN")

    # 5. Restart listening (VAD already active)
```

### User Experience

**Goal:** Interrupt feels natural, not jarring

**Quality Checks:**
- ✅ No audible glitches or repeated words in TTS audio
- ✅ No delay between user speech and halt (should feel instant, <100ms)
- ✅ Agent responds coherently to new input (context includes previous turns)

**Testing:**
```python
def test_interrupt_latency():
    """
    Measure time from user voice resumption to TTS halt.
    Should be <100ms.
    """
    start = time.time()

    # Emit on_voice_start
    interrupt_handler.on_vad_voice_start()

    # Check TTS halted
    while tts_active:
        await asyncio.sleep(1ms)

    latency = (time.time() - start) * 1000  # ms
    assert latency < 100, f"Interrupt latency too high: {latency}ms"
```

---

## Performance Monitoring & Alerting

### Metrics to Track

**Latency Metrics (per turn):**
- `vad_latency_ms` - VAD processing time
- `turn_detection_latency_ms` - Pause detection to turn_complete
- `stt_latency_ms` - STT round-trip time
- `llm_first_token_latency_ms` - Time to first LLM token
- `llm_total_latency_ms` - Full LLM response generation
- `tts_first_byte_latency_ms` - Time to first audio byte
- `tts_streaming_latency_ms` - Audio chunk generation time
- `total_e2e_latency_ms` - Wall-clock from user pause to first TTS audio
- `interrupt_latency_ms` - Voice detection to TTS halt

**Error Metrics (per hour):**
- `error_rate_percent` - Failed API calls / total calls
- `stt_error_count` - STT failures (retried/fallback)
- `llm_error_count` - LLM failures (timeout, invalid response)
- `tts_error_count` - TTS failures (timeout)
- `crash_count` - Unhandled exceptions

**Quality Metrics (per conversation):**
- `response_relevance_score` - Cosine similarity (user query vs response)
- `response_coherence_score` - Contextual coherence (0.3-1.0)
- `response_length_words` - Word count (target 20-50)
- `context_turns_used` - Number of prior turns referenced

### Alerting Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| `total_e2e_latency_ms` | >1000ms | Log WARNING |
| `stt_latency_ms` | >300ms | Log WARNING (may feel slow) |
| `interrupt_latency_ms` | >150ms | Log WARNING (feels delayed) |
| `error_rate_percent` | >5% (per hour) | Log ERROR (degraded service) |
| `crash_count` | >0 (per hour) | Log CRITICAL (unhandled exception) |
| `response_relevance_score` | <0.3 | Log WARNING (off-topic detected) |

### Logging Strategy

**Structured Logging (JSON):**

```python
import json
from datetime import datetime

def log_turn_metrics(metrics):
    """Log latency metrics in structured format."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "turn_complete",
        "metrics": {
            "vad_latency_ms": metrics["vad"],
            "stt_latency_ms": metrics["stt"],
            "llm_latency_ms": metrics["llm"],
            "tts_latency_ms": metrics["tts"],
            "e2e_latency_ms": metrics["total"]
        },
        "transcript": metrics["user_input"],
        "response_length": metrics["response_words"],
        "error": None
    }

    logger.info(json.dumps(log_entry))
```

**Log Levels:**
- **INFO:** Turn completed (transcript, latency metrics)
- **WARNING:** Latency threshold exceeded, high error rate
- **ERROR:** API timeout, retry exhausted, fallback response
- **CRITICAL:** Unhandled exception, system requires restart

---

## Kannada-Specific Quality Rules

### 1. Natural Kannada Generation

**Rule:** Responses must sound natural in Kannada, not translated from English.

**Bad Examples:**
- "ಆವಿನೂ ತಾನು ಕರೆನಾಯ್ತೆ" (Literal English grammar in Kannada)
- "ಅದರ ಹಂತಗಳು ಅದನ್ನು ಮಾಡಿ" (Machine-like phrasing)

**Good Examples:**
- "ಇದನ್ನು ಮಾಡೋದು ಅಷ್ಟೇ ಸುಲಭ" (Natural Kannada)
- "ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಬಹುದು" (Common phrasing)

**Verification:**
- Have native Kannada speaker review sample responses
- Check against common Kannada idioms and phrasings
- Avoid calques (word-for-word translation from English)

### 2. Kannada Grammar & Syntax

**Rules:**
- ✅ Correct case marking (nominative, objective, genitive, etc.)
- ✅ Proper verb conjugation (tense, aspect, mood)
- ✅ Correct postpositions ("ನಿಂದ" = from, "ಗೆ" = to, etc.)
- ✅ Subject-Object-Verb (SOV) word order (not English SVO)

**Examples:**

Correct SOV:
```
ನಾನು ನೀಮನ್ನು ಸಾಲ ಮಾಹಿತಿ ಕೊುಟ್ಟೆ
(I you-accusative loan information gave)
= I gave you loan information
```

Wrong SVO:
```
ನಾನು ಕೊುಟ್ಟೆ ನೀಮನ್ನು ಸಾಲ ಮಾಹಿತಿ
[Not natural Kannada]
```

### 3. Kannada Number Systems

**Rule:** Use Kannada numbers where appropriate in customer service context

**Examples:**
- ತಿಂಗಳು (month, written as "1", "2", etc. in context is OK)
- ಛೇದ (fraction, e.g., ೫/೪ = 5/4)
- ಲಕ್ಷ (lakh = 100,000), ಕೋಟಿ (crore = 10,000,000)

**Examples in Finance Context:**
- "ನಿಮ್ಮ ಸಾಲ ತಿಂಗಳು ೫ ರಷ್ಟು" (Your loan is 5 months...)
- "₹ 1,00,000 (1 ಲಕ್ಷ)" (1 lakh rupees)

### 4. Kannada Text Formatting

**Kannada Unicode:**
- ✅ Use proper Kannada Unicode characters (U+0C80 - U+0CFF)
- ✅ Handle ligatures correctly (ಕ್ಷ, ಜ್ಞ, ಶ್ರ, ಟ್ರ, ಣ್ಯ, etc.)
- ✅ Proper punctuation: ।  (Devanagari danda, or . for period)

**Avoid:**
- ❌ English letters used for Kannada (ಲಿಪಿ instead of "lipi")
- ❌ Latin script substitution ("Kannada" written in English letters)
- ❌ Mixing scripts without reason

### 5. Kannada Customer Service Context

**Terminology Consistency:**
- Once you call something "ಸಾಲ" (loan), don't call it "ಸಾಲಿಗೆ" or "ಸಾಲಿನ" in same conversation
- Use consistent terms for account types, transaction types, etc.

**Professional Kannada Phrases:**

| Situation | Kannada Phrase | English |
|-----------|----------------|---------|
| Greeting | "ನಮಸ್ಕಾರ, ಹೋಗಾಲೋ?" | "Hello, how are you?" |
| Acknowledgment | "ಠೀಕ್, ನಾನು ನಿಮ್ಮ ವಿಚಾರ ಕೆಲಸ ಆಗುತ್ತೆ" | "Sure, let me help you" |
| Empathy | "ನೀವು ಪ್ರಸ್ತರ ಕಠಿಣ ಪರಿಸ್ಥಿತಿ ಎದುರಿಸುತ್ತಿದ್ದೀರಿ ಎಂಬುದು ನನಗೆ ತಿಳಿದಿದೆ" | "I understand you're facing difficulties" |
| Solution | "ಇದೆ ಮುಕ್ತಿ ಹೋಗುತ್ತೆ ಹೀಗೆ ಮಾಡಿ..." | "Here's how to resolve this..." |
| Closing | "ಇದು ಸಹಾಯ ಮಾಡಿದೆಯೇ?" | "Did this help?" |

---

## Summary: Quality Checklist

**Before Every Response, Verify:**

- [ ] **Coherence:** References prior context or stands alone naturally
- [ ] **Relevance:** >90% on-topic, addresses user question
- [ ] **Length:** 20-50 words target, max 150 words
- [ ] **Tone:** Professional, friendly, solution-focused, not robotic
- [ ] **Kannada Quality:** Natural phrasing, correct grammar, proper Unicode
- [ ] **Latency:** Will be generated in <150ms (LLM), TTS in <100ms
- [ ] **Error Handling:** Fallback responses prepared if API timeout
- [ ] **Context:** Includes prior turns where relevant

---

## Reference Documents

- See **prd.md** for scope and constraints
- See **architecture.md** for technical implementation
- See **plan.md** for step-by-step implementation roadmap

---
