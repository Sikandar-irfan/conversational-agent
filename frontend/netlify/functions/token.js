// netlify/functions/token.js
// Replaces token_server.cjs — runs as a serverless Netlify Function
// Secrets are stored in Netlify dashboard → Environment Variables (never in code)

const { AccessToken } = require("livekit-server-sdk");

exports.handler = async (event) => {
  // CORS preflight
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
      body: "",
    };
  }

  const params = event.queryStringParameters || {};
  const participantName = params.name || "guest-" + Date.now();
  const voice = params.voice || "shubh";
  const agentName = params.agentName || "Shubh";

  const apiKey    = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const livekitUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !livekitUrl) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Server misconfigured: missing env vars" }),
    };
  }

  const token = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    metadata: JSON.stringify({ voice, agentName }),
  });

  token.addGrant({
    roomJoin: true,
    room: "sri-motors-room",
    canSubscribe: true,
    canPublish: true,
  });

  const jwt = await token.toJwt();

  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    body: JSON.stringify({ token: jwt, url: livekitUrl }),
  };
};
