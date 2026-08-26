# Conversational AI Voice Agent — Sri Motors (Bangalore)

An end-to-end real-time conversational AI receptionist for **Sri Motors** (Bangalore), powered by **LiveKit Agents**, **Sarvam STT**, **Groq / OpenRouter LLM**, and **Dr. Vishnuvardhan Voice Model (Seed-VC TTS)**.

---

## 🏗️ Architecture & Project Structure

The codebase is unified into a single portable repository structure:

```
conversational-agent/
├── backend/                  # Python Agent & Audio Synthesis Backend
│   ├── agent.py              # Main LiveKit Voice Agent entrypoint
│   ├── livekit_tts.py        # LiveKit custom TTS stream adapter
│   ├── tts_helper.py         # Standalone TTS synthesis helper & CLI
│   ├── test_groq.py          # Groq LLM API connectivity test script
│   ├── adapters/             # Voice conversion & ABI adapters
│   │   ├── base.py
│   │   ├── plugin_api.py
│   │   └── seedvc_adapter.py
│   └── voice_packs/          # Voice Model Packages
│       └── bandhana_voice.vc/# Dr. Vishnuvardhan Voice Model Package
├── frontend/                 # React 19 + Vite Web Application
│   ├── src/                  # Audio Visualizer & Call UI Components
│   ├── token_server.cjs      # Express token generator server
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── docs/                     # Technical specifications & documentation
│   ├── ai_rules.md
│   ├── architecture.md
│   ├── plan.md
│   └── prd.md
├── .env.example              # Environment variable template
├── .gitignore                # Git exclusion rules
├── package.json              # Root script manager
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- **Python**: 3.10 or 3.11
- **Node.js**: 18.x or higher
- **LiveKit Cloud account**: API Key & Secret
- **Groq API key**: For fast LLM inference

### 2. Environment Setup

Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```

Configure your credentials in `.env`:
```env
LIVEKIT_URL=wss://your-livekit-domain.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

GROQ_API_KEY=your_groq_api_key
SARVAM_API_KEY=your_sarvam_api_key
```

### 3. Backend Setup

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Run the backend LiveKit agent in development mode:
```bash
python backend/agent.py dev
```

### 4. Frontend Setup

Install frontend Node dependencies:
```bash
cd frontend
npm install
```

Start the token server and Vite web interface concurrently:
```bash
npm run dev:all
```

Access the UI at `http://localhost:5173`.

---

## 👥 Sharing Access to the GitHub Repository

This repository is configured as **private** on GitHub under `Sikandar-irfan`.

### To Invite Collaborators:
1. Open the repository on GitHub: `https://github.com/Sikandar-irfan/conversational-agent`
2. Click **Settings** (top navigation tab).
3. Select **Collaborators** under Access management.
4. Click **Add people** and enter the GitHub username or email address of the person you want to invite.
5. Alternatively, using GitHub CLI:
   ```bash
   gh repo invite <username> --repo Sikandar-irfan/conversational-agent
   ```

---

## 📜 License & Acknowledgments
Built for Dravidian multilingual voice agent applications for automotive booking services.
