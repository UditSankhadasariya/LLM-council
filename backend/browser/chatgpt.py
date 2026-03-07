import asyncio
import logging

from .base_interactor import BaseInteractor
from .browser_config import ChatGPTSelectors, Timeouts
from .stealth import human_click, human_type, random_delay

logger = logging.getLogger(__name__)


class ChatGPTInteractor(BaseInteractor):
    @property
    def selectors(self):
        return ChatGPTSelectors

    async def click_new_chat(self):
        """Start a new chat by navigating to chatgpt.com."""
        logger.debug("Starting new ChatGPT chat...")
        await self.tab.get("https://chatgpt.com/")
        await asyncio.sleep(2)

        # Handle any CAPTCHA after navigation
        await self.bm.check_and_handle_captcha()

        # Wait for prompt input to appear
        element = await self._find_element_with_fallbacks(
            ChatGPTSelectors.prompt_input, timeout=Timeouts.page_load
        )
        if not element:
            raise RuntimeError("Prompt input not found after navigating to new chat")

        logger.debug("New ChatGPT chat ready.")

    async def type_message(self, text: str):
        """Type a message into ChatGPT's ProseMirror prompt input."""
        element = await self._find_element_with_fallbacks(ChatGPTSelectors.prompt_input)
        if not element:
            raise RuntimeError("Prompt input not found")

        # Clear any existing content
        await human_click(self.tab, element)
        await element.apply("""(el) => {
            el.innerHTML = '';
            el.textContent = '';
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }""")
        await random_delay(0.1, 0.2)

        # Type or paste the message
        await human_type(self.tab, element, text)
