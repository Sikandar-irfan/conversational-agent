const path = require("path");
require("dotenv").config({ path: path.resolve(__dirname, "../.env") });
require("dotenv").config({ path: path.resolve(__dirname, ".env") });
const express = require("express");
const { AccessToken } = require("livekit-server-sdk");

const app = express();
app.use(express.json());

const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || "APIqSHysktZMcAY";
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || "tejbJ0xPaeiim71QqCZR7o3Vaw791IEU4yINNti7f0OB";
const LIVEKIT_URL = process.env.LIVEKIT_URL || "wss://kannada-voice-agent-o2m5t0mo.livekit.cloud";
const PORT = process.env.PORT || 3001;

app.get("/api/token", async (req, res) => {
    const participantName = req.query.name || "guest-" + Date.now();
    const voice = req.query.voice || "shubh";
    const agentName = req.query.agentName || "Shubh";

    const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
        identity: participantName,
        metadata: JSON.stringify({ voice, agentName }),
    });

    token.addGrant({
        roomJoin: true,
        room: process.env.LIVEKIT_ROOM || "sri-motors-room",
        canSubscribe: true,
        canPublish: true,
    });

    const jwt = await token.toJwt();
    res.json({ token: jwt, url: LIVEKIT_URL });
});

app.listen(PORT, () => {
    console.log(`✅ Token server running on http://localhost:${PORT}`);
});
