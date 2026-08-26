import { useState, useCallback, useEffect } from 'react';
import {
  LiveKitRoom,
  useVoiceAssistant,
  useRoomContext,
  RoomAudioRenderer,
} from '@livekit/components-react';
import AuraVisualizer from './AudioVisualizer';
import './App.css';

const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || "wss://kannada-voice-agent-o2m5t0mo.livekit.cloud";
const AGENTS = [
  { voice: 'shubh', name: 'Shubh', emoji: '👨‍💼', desc: 'Friendly • Male', color: '#1FD5F9' },
  { voice: 'simran', name: 'Simran', emoji: '👩‍💼', desc: 'Warm • Female', color: '#a78bfa' },
  { voice: 'kavya', name: 'Kavya', emoji: '👩', desc: 'Calm • Female', color: '#34d399' },
  { voice: 'rahul', name: 'Rahul', emoji: '👨', desc: 'Energetic • Male', color: '#fb923c' },
];

// ─────────────────────────────────────────────────────────────────
// AgentRoom — renders when connected
// ─────────────────────────────────────────────────────────────────
function AgentRoom({ onDisconnect, selectedAgent }) {
  const room = useRoomContext();
  const { state, audioTrack, agentTranscriptions } = useVoiceAssistant();

  useEffect(() => {
    if (room) {
      room.startAudio().catch((err) => console.warn('Autoplay startAudio error:', err));
    }
  }, [room]);

  const speaking = state === 'speaking';
  const lastLine = agentTranscriptions?.at(-1)?.segment ?? '';

  const stateLabel = {
    connecting: 'Connecting…',
    initializing: 'Initializing…',
    listening: 'Listening…',
    thinking: 'Thinking…',
    speaking: 'Speaking',
    disconnected: 'Disconnected',
  }[state] ?? state;

  const handleEndCall = useCallback(async () => {
    await room.disconnect();
    onDisconnect();
  }, [room, onDisconnect]);

  return (
    <>
      <RoomAudioRenderer />

      <div className={`status-badge ${state !== 'disconnected' ? 'connected' : ''}`}>
        <span className="status-dot" />
        {stateLabel}
      </div>

      <div className="visualizer-wrapper">
        <AuraVisualizer
          audioTrack={audioTrack}
          speaking={speaking}
          color={selectedAgent.color}
        />
        <div className={`orb ${speaking ? 'speaking' : ''}`}
          style={{ '--agent-color': selectedAgent.color }}>
          <span className="orb-icon">{selectedAgent.emoji}</span>
        </div>
      </div>

      <div className="agent-name">{selectedAgent.name}</div>
      <div className="agent-subtitle">Sri Motors · Bangalore</div>

      <div className={`transcript-box ${lastLine ? 'active' : ''}`}>
        {lastLine || 'ನಮಸ್ಕಾರ! ಮಾತನಾಡಿ…'}
      </div>

      <button className="btn-end" onClick={handleEndCall}>
        📵 &nbsp;End Call
      </button>

      <div className="mic-hint">
        <div className="mic-dot" />
        Microphone active — speak anytime
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────
// App — root component
// ─────────────────────────────────────────────────────────────────
export default function App() {
  const [token, setToken] = useState(null);
  const [serverUrl, setServerUrl] = useState(LIVEKIT_URL);
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]); // default: Shubh

  const startCall = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        name: 'user-' + Date.now(),
        voice: selectedAgent.voice,
        agentName: selectedAgent.name,
      });
      const res = await fetch('/api/token?' + params);
      const data = await res.json();
      if (data.url) {
        setServerUrl(data.url);
      }
      setToken(data.token);
    } catch (e) {
      alert('❌ Could not connect.\n\nMake sure:\n1. node token_server.cjs is running\n2. python agent.py dev is running');
    } finally {
      setLoading(false);
    }
  }, [selectedAgent]);

  const endCall = useCallback(() => setToken(null), []);

  return (
    <div className="app">
      <div className="bg-particles" />
      <div className="bg-grid" />

      <div className="header">
        <div className="header-logo">Sri Motors</div>
        <div className="header-title">AI Voice Receptionist</div>
      </div>

      {token ? (
        <LiveKitRoom
          token={token}
          serverUrl={serverUrl}
          connect={true}
          audio={true}
          video={false}
          onDisconnected={endCall}
        >
          <AgentRoom onDisconnect={endCall} selectedAgent={selectedAgent} />
        </LiveKitRoom>
      ) : (
        <>
          {/* Idle visualizer */}
          <div className="visualizer-wrapper">
            <AuraVisualizer
              audioTrack={null}
              speaking={false}
              color={selectedAgent.color}
            />
            <div className="orb" style={{ '--agent-color': selectedAgent.color }}>
              <span className="orb-icon">{selectedAgent.emoji}</span>
            </div>
          </div>

          <div className="agent-name">{selectedAgent.name}</div>
          <div className="agent-subtitle">Sri Motors · Bangalore</div>

          {/* ── Agent selector cards ── */}
          <div className="agent-selector">
            {AGENTS.map((agent) => (
              <button
                key={agent.voice}
                className={`agent-card ${selectedAgent.voice === agent.voice ? 'active' : ''}`}
                style={{ '--card-color': agent.color }}
                onClick={() => setSelectedAgent(agent)}
              >
                <span className="card-emoji">{agent.emoji}</span>
                <span className="card-name">{agent.name}</span>
                <span className="card-desc">{agent.desc}</span>
              </button>
            ))}
          </div>

          <button className="btn-call" onClick={startCall} disabled={loading}>
            {loading ? 'Connecting…' : `🎙️  Talk to ${selectedAgent.name}`}
          </button>
        </>
      )}
    </div>
  );
}
