import asyncio
import json
import logging
import re
import sys
from typing import Any, Dict, Optional
from urllib.parse import quote

from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

BASE_URL = "https://www.hepsiburada.com"


async def _do_search(query: str, max_results: int) -> list:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="tr-TR",
            extra_http_headers={
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            },
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        encoded = quote(query)
        url = f"{BASE_URL}/ara?q={encoded}"
        logger.info(f"Hepsiburada'da aranıyor: {query}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        raw = await page.evaluate("""(maxResults) => {
            const cards = document.querySelectorAll('article[class*="productCard-module_article"]');
            return Array.from(cards).slice(0, maxResults).map(card => {
                const linkEl = card.querySelector('a[class*="productCardLink"]');
                const priceEl = card.querySelector('[class*="price-module_finalPrice"]');
                const originalPriceEl = card.querySelector('[class*="price-module_originalPrice"]');
                const ratingEl = card.querySelector('[class*="rate-module_rating"]');
                const imgEl = card.querySelector('img');

                const href = linkEl ? linkEl.getAttribute('href') : null;
                const name = linkEl ? linkEl.getAttribute('title') : null;

                return {
                    name,
                    href,
                    price_text: priceEl ? priceEl.textContent.trim() : null,
                    original_price_text: originalPriceEl ? originalPriceEl.textContent.trim() : null,
                    rating_text: ratingEl ? ratingEl.textContent.trim() : null,
                    image_url: imgEl ? imgEl.getAttribute('src') : null,
                };
            });
        }""", max_results)

        await browser.close()
        return raw


class HepsiburadaSearchCollector:
    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        # headless=False gerekli: Hepsiburada headless tarayıcıları bot olarak algılıyor.
        # Uvicorn event loop çakışmasını önlemek için ayrı thread + yeni loop'ta çalıştırıyoruz.
        raw = await asyncio.to_thread(asyncio.run, _do_search(query, max_results))

        results = []
        for item in raw:
            href = item.get("href") or ""
            if not href or not item.get("name"):
                continue
            full_url = href if href.startswith("http") else BASE_URL + href

            results.append({
                "name": item.get("name"),
                "brand": self._extract_brand(item.get("name")),
                "url": full_url,
                "price": self._parse_price(item.get("price_text")),
                "original_price": self._parse_price(item.get("original_price_text")),
                "rating": self._parse_rating(item.get("rating_text")),
                "image_url": item.get("image_url"),
            })

        return {
            "source": "hepsiburada",
            "query": query,
            "total_found": len(results),
            "results": results,
        }

    def _parse_price(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        # "1.879,00 TL" → 1879.0  (Türkçe: nokta=binlik, virgül=ondalık)
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_rating(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        m = re.search(r"(\d+[.,]\d+)", text)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                return None
        return None

    def _extract_brand(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        return name.split()[0] if name else None


if __name__ == "__main__":
    async def test():
        collector = HepsiburadaSearchCollector()
        result = await collector.search("JBL Tune 520BT")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(test())
