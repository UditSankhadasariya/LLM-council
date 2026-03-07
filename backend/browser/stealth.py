import asyncio
import random
import logging

import nodriver.cdp.input_ as cdp_input

from .browser_config import Delays

logger = logging.getLogger(__name__)


async def random_delay(min_s: float = 0.1, max_s: float = 0.3):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_type(tab, element, text: str):
    """Type text character-by-character with human-like delays.
    For long text (>paste_threshold), use clipboard paste instead.
    """
    if len(text) > Delays.paste_threshold:
        await paste_text(tab, element, text)
        return

    await human_click(tab, element)
    for char in text:
        await tab.send(cdp_input.dispatch_key_event(
            type_="keyDown",
            text=char,
            key=char,
            code=f"Key{char.upper()}" if char.isalpha() else "",
            unmodified_text=char,
        ))
        await tab.send(cdp_input.dispatch_key_event(
            type_="keyUp",
            key=char,
            code=f"Key{char.upper()}" if char.isalpha() else "",
        ))
        delay = random.uniform(Delays.typing_char_min, Delays.typing_char_max)
        if random.random() < Delays.typing_pause_chance:
            delay += random.uniform(Delays.typing_pause_min, Delays.typing_pause_max)
        await asyncio.sleep(delay)


async def paste_text(tab, element, text: str):
    """Paste text into a contenteditable div using insertText command."""
    await human_click(tab, element)
    await random_delay(0.1, 0.2)

    escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    js = f"""
    (function() {{
        const el = document.activeElement;
        if (el) {{
            el.focus();
            document.execCommand('insertText', false, `{escaped}`);
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
    }})();
    """
    await tab.evaluate(js)
    await random_delay(0.1, 0.3)


async def human_click(tab, element):
    """Click an element with small random offset and delays."""
    await random_delay(Delays.before_click * 0.5, Delays.before_click * 1.5)
    try:
        await element.click()
    except Exception as e:
        logger.warning(f"Click failed, trying JS click: {e}")
        try:
            await element.apply("(el) => el.click()")
        except Exception:
            pass
    await random_delay(Delays.after_click * 0.5, Delays.after_click * 1.5)


async def send_enter(tab):
    """Press Enter key via CDP."""
    await tab.send(cdp_input.dispatch_key_event(
        type_="keyDown",
        key="Enter",
        code="Enter",
        windows_virtual_key_code=13,
        native_virtual_key_code=13,
    ))
    await tab.send(cdp_input.dispatch_key_event(
        type_="keyUp",
        key="Enter",
        code="Enter",
    ))
