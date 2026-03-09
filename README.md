# LLM Council

![llmcouncil](header.jpg)

Instead of asking one LLM, ask all of them — and let them collaborate on the answer.

LLM Council is a self-hosted web app that sends your question to multiple LLMs simultaneously (ChatGPT, Gemini, Claude), displays their individual responses side by side, and then has a "Chairman" LLM synthesize everything into a single comprehensive answer. You use your own existing subscriptions — no API keys or per-token costs required.

Originally inspired by [Karpathy's LLM Council](https://github.com/karpathy/llm-council). This fork replaces the OpenRouter API approach with direct browser automation and CLI integration, so you can use your existing ChatGPT Plus, Gemini Advanced, and Claude subscriptions at no additional cost.

## How It Works

When you submit a query, the council runs a 2-stage process:

1. **Stage 1 — Individual Responses**: Your query is sent to all council members in parallel. Each LLM responds independently. Results stream in progressively as each model finishes, displayed in a tab view so you can inspect them one by one.

2. **Stage 2 — Chairman Synthesis**: The council member with the largest context window is automatically selected as Chairman. It receives all individual responses and synthesizes them into a single, comprehensive answer — preserving every fact, flagging contradictions, and highlighting consensus.

## Architecture

The app connects to LLMs through two provider types:

- **Browser providers** (ChatGPT, Gemini): Uses [nodriver](https://github.com/nichochar/nodriver) to automate Chrome, interacting with the web UIs directly. This means you use your existing paid subscriptions (ChatGPT Plus, Gemini Advanced) with no additional API costs. Each provider runs in its own Chrome instance with a persistent profile for session persistence.

- **CLI provider** (Claude): Uses [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude -p`) to query Claude Opus. Requires an active Claude subscription with CLI access.

## Prerequisites

- **Python 3.10+** and [uv](https://docs.astral.sh/uv/) for package management
- **Node.js 18+** and npm
- **Google Chrome** installed (for browser providers)
- **Claude Code CLI** installed and authenticated (for Claude provider)
- Active subscriptions to the LLM services you want to use (ChatGPT Plus, Gemini Advanced, Claude)

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/llm-council.git
cd llm-council

# Python dependencies
uv sync

# Frontend dependencies + production build
cd frontend
npm install
npm run build
cd ..
```

### 2. First-time browser login

The browser providers need you to log in once. On first launch, Chrome windows will open for ChatGPT and Gemini. Log in to each one manually. Your sessions are saved to `~/.chatgpt_profile` and `~/.gemini_profile` so you only need to do this once.

If running on a headless server (no display), use screen sharing or VNC to complete the initial login.

### 3. Verify Claude CLI (if using Claude provider)

```bash
claude auth status
```

Should show `loggedIn: true`. If not, run `claude auth login`.

### 4. Configure council members (optional)

Edit `backend/config.py` to add, remove, or change council members:

```python
COUNCIL_MODELS = [
    {"id": "chatgpt", "name": "ChatGPT", "provider": "browser", "browser_provider": "chatgpt", "context_window": 128_000},
    {"id": "gemini", "name": "Gemini", "provider": "browser", "browser_provider": "gemini", "context_window": 1_000_000},
    {"id": "claude-opus", "name": "Claude Opus", "provider": "claude-cli", "context_window": 200_000},
]
```

The model with the largest `context_window` is automatically selected as Chairman for synthesis.

## Running

### Quick start (development)

```bash
./start.sh
```

This launches the backend and a Vite dev server with color-coded logs. Access at `http://localhost:5173`.

### Production (single process)

After building the frontend (`npm run build` in `frontend/`), the backend serves everything on a single port:

```bash
uv run python -m backend.main
```

Access at `http://localhost:8001` — or `http://<your-ip>:8001` from any device on the network.

### Run as a background process

```bash
nohup uv run python -m backend.main > council.log 2>&1 &
```

To stop it:

```bash
kill $(lsof -ti:8001)
```

### Headless server notes

If deploying on a Mac without a display (e.g., Mac Mini/Studio as a home server):

- macOS runs its window server even without a physical display, so Chrome can launch
- You must be logged in to the macOS GUI (auto-login on boot works)
- Use screen sharing for the one-time ChatGPT/Gemini login
- After initial login, the browser profiles persist and no further GUI interaction is needed
- Access the web UI from any device on your LAN at `http://<server-ip>:8001`

## Ports

| Service | Port | Notes |
|---------|------|-------|
| Backend + Frontend | 8001 | FastAPI serves both API and static frontend |
| ChatGPT Chrome | 9222 | Chrome remote debugging port |
| Gemini Chrome | 9223 | Chrome remote debugging port |

## Tech Stack

- **Backend**: FastAPI, uvicorn, async Python
- **Frontend**: React + Vite, react-markdown
- **Browser Automation**: nodriver (undetected Chrome)
- **Storage**: JSON files in `data/conversations/`
- **Package Management**: uv (Python), npm (JavaScript)

## Project Structure

```
llm-council/
├── backend/
│   ├── main.py              # FastAPI app, routes, static file serving
│   ├── config.py             # Council member definitions
│   ├── council.py            # 2-stage orchestration logic
│   ├── llm_client.py         # Provider dispatcher (browser / CLI)
│   ├── storage.py            # JSON conversation persistence
│   └── browser/              # Chrome automation
│       ├── provider_manager.py   # Manages browser lifecycle
│       ├── browser_manager.py    # Chrome launch, tab management
│       ├── chatgpt.py            # ChatGPT web UI interactor
│       ├── gemini.py             # Gemini web UI interactor
│       ├── browser_config.py     # Selectors, timeouts, config
│       ├── queue_manager.py      # Request queuing per provider
│       ├── base_interactor.py    # Shared interactor interface
│       └── stealth.py            # Anti-detection measures
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main app, conversation management
│   │   ├── api.js            # API client
│   │   └── components/       # Stage1, Stage2, ChatInterface, etc.
│   └── dist/                 # Production build (gitignored)
├── data/conversations/       # Stored conversations (gitignored)
├── start.sh                  # Dev launcher (backend + frontend)
├── CLAUDE.md                 # Detailed technical notes
└── pyproject.toml
```

## License

MIT
