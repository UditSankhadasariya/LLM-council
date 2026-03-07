"""BrowserProviderManager: owns browser lifecycle and provides query interface."""

import asyncio
import logging
from typing import Optional

from .browser_config import (
    ChatGPTBrowserConfig,
    ChatGPTSelectors,
    GeminiBrowserConfig,
    GeminiSelectors,
)
from .browser_manager import BrowserManager
from .chatgpt import ChatGPTInteractor
from .gemini import GeminiInteractor
from .queue_manager import BrowserRequest, QueueManager

logger = logging.getLogger(__name__)


class BrowserProviderManager:
    """Manages browser-based LLM providers (ChatGPT, Gemini).

    Owns the full lifecycle: launch browsers, wait for login, start queue workers.
    Provides a single `query()` method for the backend to call.

    Browser initialization runs in the background so the HTTP server starts
    immediately and can serve non-browser requests (e.g. create conversation)
    while Chrome instances are still launching / waiting for login.
    """

    def __init__(self):
        # provider_name -> {"browser": BrowserManager, "queue": QueueManager}
        self._providers: dict[str, dict] = {}
        self._init_tasks: list[asyncio.Task] = []
        self._init_done = asyncio.Event()

    async def start(self):
        """Kick off browser init in background tasks (returns immediately)."""
        logger.info("Scheduling browser provider initialization (background)...")
        self._init_tasks = [
            asyncio.create_task(self._init_provider(
                "chatgpt", ChatGPTBrowserConfig, ChatGPTSelectors, ChatGPTInteractor,
            )),
            asyncio.create_task(self._init_provider(
                "gemini", GeminiBrowserConfig, GeminiSelectors, GeminiInteractor,
            )),
        ]
        # Fire-and-forget a watcher that sets _init_done when both finish
        asyncio.create_task(self._watch_init())

    async def _init_provider(self, name, browser_config, selectors, interactor_cls):
        """Initialize a single browser provider (runs as a background task)."""
        try:
            logger.info(f"--- Initializing {name} provider ---")
            browser = BrowserManager(browser_config, selectors)
            await browser.start()
            interactor = interactor_cls(browser)
            queue = QueueManager(interactor)
            queue.start()
            self._providers[name] = {"browser": browser, "queue": queue}
            logger.info(f"{name} provider ready.")
        except Exception as e:
            logger.error(f"Failed to start {name} provider: {e}", exc_info=True)

    async def _watch_init(self):
        """Wait for all init tasks to complete, then log summary."""
        await asyncio.gather(*self._init_tasks, return_exceptions=True)
        if not self._providers:
            logger.error("No browser providers started successfully.")
        else:
            logger.info(f"Browser providers ready: {list(self._providers.keys())}")
        self._init_done.set()

    async def stop(self):
        """Cancel init tasks if still running, then stop workers and browsers."""
        logger.info("Shutting down browser providers...")
        # Cancel any still-running init tasks
        for task in self._init_tasks:
            if not task.done():
                task.cancel()
        for task in self._init_tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        # Stop running providers
        for name, p in self._providers.items():
            try:
                await p["queue"].stop()
                await p["browser"].stop()
                logger.info(f"Provider '{name}' shut down.")
            except Exception as e:
                logger.error(f"Error shutting down '{name}': {e}")
        self._providers.clear()
        logger.info("Browser providers shutdown complete.")

    async def query(
        self,
        provider_name: str,
        prompt: str,
        timeout: float = 630.0,
    ) -> Optional[str]:
        """Enqueue a prompt for a browser provider, await and return the result.

        Args:
            provider_name: "chatgpt" or "gemini"
            prompt: The prompt text to send
            timeout: Max seconds to wait for a response

        Returns:
            The response text, or None on failure
        """
        # Wait for background init to finish before checking availability
        if not self._init_done.is_set():
            logger.info(f"Waiting for browser init to complete before querying '{provider_name}'...")
            await self._init_done.wait()

        if provider_name not in self._providers:
            logger.error(f"Browser provider '{provider_name}' is not available.")
            return None

        p = self._providers[provider_name]

        if not p["browser"].ready:
            logger.error(f"Browser provider '{provider_name}' is not ready.")
            return None

        request = BrowserRequest(prompt=prompt, temporary_chat=True)

        try:
            await p["queue"].enqueue(request)
        except asyncio.QueueFull:
            logger.error(f"Queue full for provider '{provider_name}'.")
            return None

        try:
            result = await asyncio.wait_for(request.future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Browser query to '{provider_name}' timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Browser query to '{provider_name}' failed: {e}")
            return None
