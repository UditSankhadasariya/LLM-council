"""Configuration for the LLM Council."""

# Council members - each with id, display name, provider type, and context window size
COUNCIL_MODELS = [
    {"id": "chatgpt", "name": "ChatGPT", "provider": "browser", "browser_provider": "chatgpt", "context_window": 128_000},
    {"id": "gemini", "name": "Gemini", "provider": "browser", "browser_provider": "gemini", "context_window": 1_000_000},
    {"id": "claude-opus", "name": "Claude Opus", "provider": "claude-cli", "context_window": 200_000},
]

# Fallback chairman model - used if dynamic selection fails
CHAIRMAN_MODEL_FALLBACK = {"id": "claude-opus", "name": "Claude Opus", "provider": "claude-cli", "context_window": 200_000}

# Claude CLI model identifier
CLAUDE_CLI_MODEL = "claude-opus-4-6"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
