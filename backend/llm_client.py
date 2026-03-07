"""LLM client that dispatches to browser providers or Claude CLI."""

import asyncio
from typing import List, Dict, Any, Optional

from .config import CLAUDE_CLI_MODEL

# Module-level singleton for the browser provider manager.
# Set during app startup via set_browser_manager().
_browser_manager = None


def set_browser_manager(manager):
    """Inject the BrowserProviderManager singleton (called from main.py lifespan)."""
    global _browser_manager
    _browser_manager = manager


def _flatten_messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Flatten a messages array into a single prompt string.

    For a single user message, just returns the content directly.
    For multiple messages, formats as "Role: content" sections.
    """
    if len(messages) == 1 and messages[0]["role"] == "user":
        return messages[0]["content"]

    parts = []
    for msg in messages:
        role = msg["role"].capitalize()
        parts.append(f"{role}: {msg['content']}")
    return "\n\n".join(parts)


async def query_browser(
    browser_provider: str,
    messages: List[Dict[str, str]],
    timeout: float = 630.0,
) -> Optional[Dict[str, Any]]:
    """
    Query a browser-based provider (ChatGPT or Gemini) directly.

    Args:
        browser_provider: "chatgpt" or "gemini"
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', or None if failed
    """
    if _browser_manager is None:
        print("Error: Browser manager not initialized")
        return None

    prompt = _flatten_messages_to_prompt(messages)

    result = await _browser_manager.query(browser_provider, prompt, timeout=timeout)
    if result is not None:
        return {"content": result}
    return None


async def query_claude_cli(
    messages: List[Dict[str, str]],
    timeout: float = 600.0
) -> Optional[Dict[str, Any]]:
    """
    Query Claude via the CLI: claude -p --model claude-opus-4-6

    Args:
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', or None if failed
    """
    prompt = _flatten_messages_to_prompt(messages)

    try:
        process = await asyncio.create_subprocess_exec(
            "claude", "-p", "--model", CLAUDE_CLI_MODEL, "--allowedTools", "WebSearch",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=prompt.encode("utf-8")),
            timeout=timeout,
        )

        if process.returncode != 0:
            print(f"Claude CLI error (exit {process.returncode}): {stderr.decode()}")
            return None

        content = stdout.decode("utf-8").strip()
        return {"content": content}

    except asyncio.TimeoutError:
        print(f"Claude CLI timed out after {timeout}s")
        if process:
            process.kill()
        return None
    except Exception as e:
        print(f"Error querying Claude CLI: {e}")
        return None


async def query_model(
    model_config: Dict[str, str],
    messages: List[Dict[str, str]],
    timeout: float = 600.0
) -> Optional[Dict[str, Any]]:
    """
    Dispatch a query to the appropriate provider based on model config.

    Args:
        model_config: Dict with 'id', 'name', and 'provider' keys
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', or None if failed
    """
    provider = model_config["provider"]

    if provider == "browser":
        browser_provider = model_config.get("browser_provider", "chatgpt")
        # Add buffer so inner response_complete timeout fires first and can return partial
        return await query_browser(browser_provider, messages, timeout + 60)
    elif provider == "claude-cli":
        return await query_claude_cli(messages, timeout)
    else:
        print(f"Unknown provider: {provider}")
        return None


async def query_models_parallel(
    models: List[Dict[str, str]],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of model config dicts
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model id to response dict (or None if failed)
    """
    tasks = [query_model(model, messages) for model in models]
    responses = await asyncio.gather(*tasks)

    return {model["id"]: response for model, response in zip(models, responses)}
