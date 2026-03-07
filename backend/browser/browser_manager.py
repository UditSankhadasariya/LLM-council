import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import nodriver as uc

from .browser_config import Timeouts

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(self, browser_config, selectors):
        self.config = browser_config
        self.selectors = selectors
        self.browser = None
        self.tab = None
        self.ready = False

    async def start(self):
        """Connect to existing Chrome or launch a new one."""
        port = self.config.debug_port

        if self._is_chrome_running(port):
            logger.info(f"Found existing Chrome on port {port}, connecting...")
            await self._connect_existing(port)
        else:
            logger.info(f"No existing Chrome found on port {port}, launching new browser...")
            await self._launch_new(port)

        # Common setup
        await asyncio.sleep(3)
        await self.check_and_handle_captcha()
        await self.wait_for_login()
        self.ready = True
        logger.info(f"Browser is ready for {self.config.target_url}!")

    def _is_chrome_running(self, port: int) -> bool:
        """Check if Chrome is listening on the debug port."""
        try:
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/version", timeout=3
            )
            data = json.loads(resp.read())
            logger.info(f"Chrome detected: {data.get('Browser', 'unknown')}")
            return True
        except Exception:
            return False

    async def _connect_existing(self, port: int):
        """Connect to an already-running Chrome via nodriver."""
        self.browser = await uc.start(host="127.0.0.1", port=port)
        self.tab = await self._find_or_create_target_tab()
        logger.info("Connected to existing browser.")

    async def _launch_new(self, port: int):
        """Launch Chrome manually with a fixed debug port, then connect."""
        exe = self._find_chrome()
        args = [
            str(exe),
            f"--remote-debugging-port={port}",
            "--remote-debugging-host=127.0.0.1",
            "--remote-allow-origins=*",
            f"--user-data-dir={self.config.user_data_dir}",
            f"--lang={self.config.lang}",
            "--no-first-run",
            "--no-service-autorun",
            "--no-default-browser-check",
            "--homepage=about:blank",
            "--no-pings",
            "--password-store=basic",
            "--disable-infobars",
            "--disable-breakpad",
            "--disable-dev-shm-usage",
            "--disable-session-crashed-bubble",
            "--disable-search-engine-choice-screen",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-blink-features=AutomationControlled",
        ]

        subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        logger.info(f"Chrome process started on port {port}.")

        # Wait for Chrome to be ready
        for i in range(30):
            if self._is_chrome_running(port):
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError("Chrome failed to start within 30 seconds.")

        # Connect via nodriver
        self.browser = await uc.start(host="127.0.0.1", port=port)
        self.tab = await self._find_or_create_target_tab()
        logger.info("Launched new browser and connected.")

    async def _find_or_create_target_tab(self):
        """Find an existing tab matching the provider or navigate to it."""
        tab_match = self.config.tab_match
        target_url = self.config.target_url

        # Check existing tabs
        for tab in self.browser.tabs:
            url = ""
            if hasattr(tab, "target") and tab.target:
                url = getattr(tab.target, "url", "") or ""
            if tab_match in url:
                logger.info(f"Found existing tab: {url}")
                return tab

        # No matching tab found — navigate in the first available tab
        if self.browser.tabs:
            tab = self.browser.tabs[0]
            await tab.get(target_url)
            logger.info(f"Navigated first tab to {target_url}")
            return tab

        # No tabs at all — open a new one
        tab = await self.browser.get(target_url)
        logger.info(f"Opened new tab to {target_url}")
        return tab

    def _find_chrome(self) -> str:
        """Find Chrome executable on the system."""
        if sys.platform == "darwin":
            path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(path):
                return path
        candidates = [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ]
        for name in candidates:
            found = shutil.which(name)
            if found:
                return found
        raise RuntimeError(
            "Chrome executable not found. Install Google Chrome or set the path manually."
        )

    async def wait_for_login(self):
        """Wait for the user to log in by polling for the login indicator element."""
        logger.info(
            f"Waiting for login... Please log in at {self.config.target_url} in the browser window."
        )
        logger.info(f"You have {int(Timeouts.login_wait)} seconds to log in.")

        start = time.time()
        while time.time() - start < Timeouts.login_wait:
            for selector in self.selectors.login_indicator:
                try:
                    element = await self.tab.query_selector(selector)
                    if element:
                        logger.info("Login detected! Input element found.")
                        return
                except Exception:
                    pass

            await self.check_and_handle_captcha()
            await asyncio.sleep(2)

        raise TimeoutError(
            f"Login not detected within {int(Timeouts.login_wait)}s. "
            "Please restart and try again."
        )

    async def check_and_handle_captcha(self):
        """Check for CAPTCHA and attempt to handle it. Skip if no captcha selectors."""
        if not self.selectors.captcha:
            return

        for selector in self.selectors.captcha:
            try:
                element = await self.tab.query_selector(selector)
                if element:
                    logger.warning("CAPTCHA detected! Attempting auto-bypass...")
                    try:
                        await self.tab.verify_cf()
                        logger.info("Cloudflare challenge bypassed automatically.")
                        await asyncio.sleep(2)
                        return
                    except Exception as e:
                        logger.warning(f"Auto-bypass failed: {e}")
                        logger.info(
                            "Please solve the CAPTCHA manually in the browser. "
                            f"Waiting up to {int(Timeouts.captcha_wait)}s..."
                        )
                        await self._wait_captcha_resolved()
                        return
            except Exception:
                pass

    async def _wait_captcha_resolved(self):
        """Wait for CAPTCHA to be resolved (indicators disappear)."""
        start = time.time()
        while time.time() - start < Timeouts.captcha_wait:
            captcha_present = False
            for selector in self.selectors.captcha:
                try:
                    element = await self.tab.query_selector(selector)
                    if element:
                        captcha_present = True
                        break
                except Exception:
                    pass

            if not captcha_present:
                logger.info("CAPTCHA resolved!")
                await asyncio.sleep(2)
                return

            await asyncio.sleep(2)

        logger.error("CAPTCHA was not resolved within timeout.")

    async def stop(self):
        """Disconnect from browser without killing it."""
        self.ready = False
        self.browser = None
        self.tab = None
        logger.info("Disconnected from browser (browser left running).")
