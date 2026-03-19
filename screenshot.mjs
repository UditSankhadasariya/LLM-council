import { chromium } from 'playwright-core';

const browser = await chromium.launch({
  executablePath: '/home/node/.cache/ms-playwright/chromium-1208/chrome-linux/chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage({ viewport: { width: 2560, height: 1440 } });
await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);
await page.screenshot({ path: '/workspace/screenshot-dark-mode.png', fullPage: false });
console.log('Screenshot saved to /workspace/screenshot-dark-mode.png');
await browser.close();
