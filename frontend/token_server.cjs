const fs = require("fs");
const path = require("path");

// Zero-dependency .env loader
function loadEnv(filePath) {
    if (fs.existsSync(filePath)) {
        try {
            const content = fs.readFileSync(filePath, "utf-8");
            for (const line of content.split(/\r?\n/)) {
                const trimmed = line.trim();
                if (trimmed && !trimmed.startsWith("#") && trimmed.includes("=")) {
                    const [key, ...valParts] = trimmed.split("=");
                    const k = key.trim();
                    const v = valParts.join("=").trim().replace(/^["']|["']$/g, '');
                    if (!process.env[k]) {
                        process.env[k] = v;
                    }
                }
            }
        } catch (e) {
            console.warn("Could not read .env file:", e.message);
        }
    }
}

loadEnv(path.resolve(__dirname, "../.env"));
loadEnv(path.resolve(__dirname, ".env"));

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
