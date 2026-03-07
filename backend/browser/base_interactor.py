import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from markdownify import markdownify as md

from .browser_manager import BrowserManager
from .browser_config import Timeouts
from .stealth import human_click, human_type, random_delay, send_enter

logger = logging.getLogger(__name__)


class BaseInteractor(ABC):
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager

    @property
    def tab(self):
        return self.bm.tab

    @property
    @abstractmethod
    def selectors(self):
        """Return the provider-specific selectors class."""
        ...

    @abstractmethod
    async def click_new_chat(self):
        """Navigate to a new chat for this provider."""
        ...

    @abstractmethod
    async def type_message(self, text: str):
        """Type a message into the provider's prompt input."""
        ...

    async def _find_element_with_fallbacks(self, selectors: list[str], timeout: float = None):
        """Try each selector in order, return first match."""
        timeout = timeout or Timeouts.element_find
        start = time.time()

        while time.time() - start < timeout:
            for i, selector in enumerate(selectors):
                try:
                    element = await self.tab.query_selector(selector)
                    if element:
                        if i > 0:
                            logger.debug(f"Used fallback selector [{i}]: {selector}")
                        return element
                except Exception:
                    pass
            await asyncio.sleep(0.3)

        return None

    async def click_temporary_chat(self):
        """Click the temporary chat toggle button if available."""
        element = await self._find_element_with_fallbacks(
            self.selectors.temporary_chat_button, timeout=5
        )
        if element:
            await human_click(self.tab, element)
            logger.debug("Clicked temporary chat toggle.")
            await asyncio.sleep(0.5)
        else:
            logger.warning("Temporary chat button not found, skipping.")

    async def click_send(self):
        """Click the send button, fallback to Enter key."""
        element = await self._find_element_with_fallbacks(self.selectors.send_button, timeout=5)
        if element:
            await human_click(self.tab, element)
            logger.debug("Clicked send button.")
        else:
            logger.debug("Send button not found, pressing Enter...")
            await send_enter(self.tab)

    async def _get_response_text(self) -> str:
        """Extract the latest assistant response text as markdown."""
        for selector in self.selectors.assistant_response:
            try:
                elements = await self.tab.query_selector_all(selector)
                if elements:
                    last = elements[-1]
                    html = await last.apply("(el) => el.innerHTML")
                    if html and html.strip():
                        text = md(html, heading_style="ATX", bullets="-")
                        return text.strip()
            except Exception:
                pass
        return ""

    async def _is_streaming(self) -> bool:
        """Check if the provider is still generating."""
        for selector in self.selectors.streaming_indicator:
            try:
                element = await self.tab.query_selector(selector)
                if element:
                    return True
            except Exception:
                pass

        for selector in self.selectors.stop_generating:
            try:
                element = await self.tab.query_selector(selector)
                if element:
                    return True
            except Exception:
                pass

        return False

    async def wait_for_response(self) -> str:
        """Wait for the response to complete using triple-signal detection."""
        logger.debug("Waiting for response to complete...")
        start = time.time()
        stable_count = 0
        last_text = ""
        required_stable = 3

        await asyncio.sleep(1.5)

        while time.time() - start < Timeouts.response_complete:
            await self.bm.check_and_handle_captcha()

            current_text = await self._get_response_text()
            is_streaming = await self._is_streaming()

            if current_text and current_text == last_text and not is_streaming:
                stable_count += 1
                if stable_count >= required_stable:
                    logger.debug(
                        f"Response complete ({len(current_text)} chars, "
                        f"{time.time() - start:.1f}s)"
                    )
                    return current_text
            else:
                stable_count = 0

            last_text = current_text
            await asyncio.sleep(Timeouts.polling_interval)

        logger.warning(
            f"Response timeout after {Timeouts.response_complete}s, "
            f"returning partial ({len(last_text)} chars)"
        )
        return last_text or "Error: Response timeout with no content"

    async def process_message(self, prompt: str, temporary_chat: bool = False):
        """Full flow: new chat -> type message -> send -> wait for response."""
        await self.click_new_chat()
        if temporary_chat:
            await self.click_temporary_chat()
        await self.type_message(prompt)
        await random_delay(0.2, 0.5)
        await self.click_send()
        await random_delay(0.3, 0.5)

        return await self.wait_for_response()
