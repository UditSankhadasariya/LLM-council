import asyncio
import logging

from .base_interactor import BaseInteractor
from .browser_config import GeminiSelectors, Timeouts
from .stealth import human_click, human_type, random_delay

logger = logging.getLogger(__name__)


class GeminiInteractor(BaseInteractor):
    @property
    def selectors(self):
        return GeminiSelectors

    async def click_new_chat(self):
        """Start a new chat by navigating to gemini.google.com/app."""
        logger.debug("Starting new Gemini chat...")
        await self.tab.get("https://gemini.google.com/app")
        await asyncio.sleep(2)

        # Wait for prompt input to appear
        element = await self._find_element_with_fallbacks(
            GeminiSelectors.prompt_input, timeout=Timeouts.page_load
        )
        if not element:
            raise RuntimeError("Gemini prompt input not found after navigating to new chat")

        # Temporary chat MUST be enabled before switching mode,
        # otherwise selecting Pro triggers a page reload that resets temp chat.
        await self._enable_temporary_chat()
        await self._switch_to_pro_mode()

        # After mode switch the DOM re-renders — wait for input to be ready again
        await asyncio.sleep(2)
        element = await self._find_element_with_fallbacks(
            GeminiSelectors.prompt_input, timeout=Timeouts.page_load
        )
        if not element:
            raise RuntimeError("Gemini prompt input not found after mode switch")

        # Click the input to dismiss any overlay and ensure focus
        await human_click(self.tab, element)
        await asyncio.sleep(0.3)

        logger.debug("New Gemini chat ready (temporary + Pro mode).")

    async def _enable_temporary_chat(self):
        """Click the temporary chat button."""
        element = await self._find_element_with_fallbacks(
            GeminiSelectors.temporary_chat_button, timeout=5
        )
        if element:
            await human_click(self.tab, element)
            logger.debug("Enabled temporary chat.")
            await asyncio.sleep(0.5)
        else:
            logger.warning("Temporary chat button not found on Gemini.")

    async def _switch_to_pro_mode(self):
        """Open the mode picker and select Pro. Skips if already on Pro."""
        # Check current mode first — skip if already Pro
        picker = await self._find_element_with_fallbacks(
            GeminiSelectors.mode_picker_button, timeout=5
        )
        if not picker:
            logger.warning("Mode picker button not found on Gemini.")
            return

        current_mode = await picker.apply("(el) => el.textContent.trim()")
        if current_mode and "pro" in current_mode.lower():
            logger.debug("Already in Pro mode, skipping.")
            return

        # Open the dropdown
        await human_click(self.tab, picker)
        await asyncio.sleep(0.8)

        # Click the Pro option
        pro_option = await self._find_element_with_fallbacks(
            GeminiSelectors.mode_pro_option, timeout=5
        )
        if pro_option:
            await human_click(self.tab, pro_option)
            logger.debug("Switched to Pro mode.")
            await asyncio.sleep(1)
        else:
            logger.warning("Pro mode option not found in Gemini mode picker.")

    async def process_message(self, prompt: str, temporary_chat: bool = False):
        """Override base: skip the separate click_temporary_chat() call since
        click_new_chat() already enables temp chat + Pro mode for Gemini."""
        await self.click_new_chat()
        # Do NOT call click_temporary_chat() here — already done in click_new_chat()
        await self.type_message(prompt)
        await random_delay(0.2, 0.5)
        await self.click_send()
        await random_delay(0.3, 0.5)

        return await self.wait_for_response()

    async def type_message(self, text: str):
        """Type a message into Gemini's Quill-based input editor."""
        element = await self._find_element_with_fallbacks(GeminiSelectors.prompt_input)
        if not element:
            raise RuntimeError("Gemini prompt input not found")

        # Clear existing content using innerHTML reset — preserves Quill's internal state
        await human_click(self.tab, element)
        await element.apply("""(el) => {
            el.focus();
            el.innerHTML = '<p><br></p>';
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }""")
        await random_delay(0.1, 0.2)

        logger.debug(f"Typing message ({len(text)} chars) into Gemini input...")
        await human_type(self.tab, element, text)
        logger.debug("Finished typing message.")
