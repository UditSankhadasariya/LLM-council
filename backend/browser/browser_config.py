import os
from pathlib import Path


# --- ChatGPT Provider ---

class ChatGPTBrowserConfig:
    headless: bool = False
    user_data_dir: str = str(Path.home() / ".chatgpt_profile")
    lang: str = "en-US"
    debug_port: int = 9222
    target_url: str = "https://chatgpt.com/"
    tab_match: str = "chatgpt.com"
    browser_args: list[str] = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]


class ChatGPTSelectors:
    # Prompt input (fallback list, tried in order)
    prompt_input: list[str] = [
        "div#prompt-textarea",
        "textarea#prompt-textarea",
        "div[contenteditable='true'].ProseMirror",
    ]

    # Send button
    send_button: list[str] = [
        "button#composer-submit-button",
        "button[data-testid='send-button']",
        "button[aria-label='Send prompt']",
    ]

    # New chat URL (most reliable approach)
    new_chat_url: str = "https://chatgpt.com/"
    new_chat_button: list[str] = [
        "a[href='/']",
    ]

    # Assistant response
    assistant_response: list[str] = [
        "[data-message-author-role='assistant'] div.markdown",
        "div.markdown.prose",
    ]

    # Stop generating
    stop_generating: list[str] = [
        "button[aria-label='Stop generating']",
        "button[data-testid='stop-button']",
    ]

    # Streaming indicator
    streaming_indicator: list[str] = [
        "div.result-streaming",
    ]

    # CAPTCHA indicators
    captcha: list[str] = [
        "iframe[src*='challenges.cloudflare.com']",
        "#challenge-running",
        "div.cf-turnstile",
    ]

    # Login detection (presence means logged in)
    login_indicator: list[str] = [
        "div#prompt-textarea",
        "textarea#prompt-textarea",
    ]

    # Temporary chat toggle
    temporary_chat_button: list[str] = [
        "button[aria-label='Turn on temporary chat']",
        "button[aria-label*='temporary chat']",
    ]


# --- Gemini Provider ---

class GeminiBrowserConfig:
    headless: bool = False
    user_data_dir: str = str(Path.home() / ".gemini_profile")
    lang: str = "en-US"
    debug_port: int = 9223
    target_url: str = "https://gemini.google.com/app"
    tab_match: str = "gemini.google.com"
    browser_args: list[str] = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]


class GeminiSelectors:
    # Prompt input
    prompt_input: list[str] = [
        "div.ql-editor[contenteditable='true']",
        "rich-textarea .ql-editor",
        "div.input-area-container .ql-editor",
    ]

    # Send button
    send_button: list[str] = [
        "button.send-button",
        "button[aria-label='Send message']",
        "button[data-test-id='send-button']",
    ]

    # New chat URL
    new_chat_url: str = "https://gemini.google.com/app"
    new_chat_button: list[str] = [
        "a[href='/app']",
        "button[aria-label='New chat']",
    ]

    # Assistant response
    assistant_response: list[str] = [
        "message-content model-response-text .markdown",
        ".model-response-text .markdown",
        "model-response message-content",
    ]

    # Stop generating
    stop_generating: list[str] = [
        "button[aria-label='Stop response']",
        "button.stop-button",
    ]

    # Streaming indicator
    streaming_indicator: list[str] = [
        ".response-streaming",
        ".loading-indicator",
    ]

    # CAPTCHA indicators (Gemini uses Google auth, no Cloudflare CAPTCHA)
    captcha: list[str] = []

    # Login detection (presence means logged in)
    login_indicator: list[str] = [
        "div.ql-editor[contenteditable='true']",
        "rich-textarea .ql-editor",
    ]

    # Temporary chat toggle
    temporary_chat_button: list[str] = [
        "button[data-test-id='temp-chat-button']",
        "button[aria-label='Temporary chat']",
    ]

    # Mode picker (opens dropdown)
    mode_picker_button: list[str] = [
        "button[data-test-id='bard-mode-menu-button']",
        "button[aria-label='Open mode picker']",
    ]

    # Pro mode option (inside the dropdown)
    mode_pro_option: list[str] = [
        "button[data-test-id='bard-mode-option-pro']",
    ]


# --- Shared Config ---

class Timeouts:
    page_load: float = 30.0
    element_find: float = 10.0
    response_complete: float = 600.0
    login_wait: float = 600.0
    captcha_wait: float = 300.0
    polling_interval: float = 0.5


class Delays:
    typing_char_min: float = 0.02
    typing_char_max: float = 0.12
    typing_pause_chance: float = 0.05
    typing_pause_min: float = 0.2
    typing_pause_max: float = 0.8
    mouse_move_steps: int = 15
    before_click: float = 0.1
    after_click: float = 0.2
    paste_threshold: int = 500


# --- Provider Routing ---

class ProviderRouting:
    """Maps model name prefixes to provider names."""
    prefix_map: dict[str, str] = {
        "gpt-": "chatgpt",
        "chatgpt-": "chatgpt",
        "o1-": "chatgpt",
        "o3-": "chatgpt",
        "o4-": "chatgpt",
        "gemini-": "gemini",
    }

    default_provider: str = "chatgpt"

    @classmethod
    def resolve(cls, model: str) -> str:
        """Return provider name for a given model string."""
        model_lower = model.lower()
        for prefix, provider in cls.prefix_map.items():
            if model_lower.startswith(prefix):
                return provider
        return cls.default_provider
