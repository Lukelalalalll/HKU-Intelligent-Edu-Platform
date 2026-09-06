from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import quote_plus


def build_query(section_title: str, title: str, bullets: list[str], page_role: str = "") -> str:
    parts = [section_title, title, *bullets[:6], page_role]
    return " ".join(dict.fromkeys(str(x).strip() for x in parts if str(x).strip()))[:240]


class BrowserImageSearch:
    def __init__(self, *, mode="browser_worker", proxy=None, timeout=15, headless=True, executable_path=None):
        self.mode, self.proxy, self.timeout, self.headless, self.executable_path = mode, proxy, timeout, headless, executable_path

    async def search(self, query: str, limit: int = 12) -> list[dict]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright 未安装") from exc
        async with async_playwright() as pw:
            launch = {"headless": self.headless}
            if self.executable_path: launch["executable_path"] = self.executable_path
            if self.proxy: launch["proxy"] = {"server": self.proxy}
            browser = await pw.chromium.launch(**launch)
            page = await browser.new_page()
            try:
                await page.goto(f"https://www.bing.com/images/search?q={quote_plus(query)}", wait_until="domcontentloaded", timeout=self.timeout * 1000)
                await page.wait_for_timeout(500)
                rows = await page.locator("a.iusc").evaluate_all("els => els.map(e => e.getAttribute('m')).filter(Boolean)")
                out = []
                import json
                for raw in rows[:limit]:
                    try: data = json.loads(raw)
                    except Exception: continue
                    image = data.get("turl") or data.get("murl")
                    if image: out.append({"image_url": image, "thumbnail": data.get("turl"), "url": data.get("purl") or data.get("murl"), "title": data.get("t") or query, "license": data.get("desc") or "Bing Images source", "source": "bing", "search_query": query, "fetched_at": datetime.now(timezone.utc).isoformat()})
                return out
            finally:
                await browser.close()

    def search_sync(self, query: str, limit: int = 12) -> list[dict]:
        return asyncio.run(self.search(query, limit))
