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

BASE_URL = "https://www.trendyol.com"


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
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        encoded = quote(query)
        url = f"{BASE_URL}/sr?q={encoded}"
        logger.info(f"Trendyol'da aranıyor: {query}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        raw = await page.evaluate("""(maxResults) => {
            const cards = document.querySelectorAll('a.product-card');
            return Array.from(cards).slice(0, maxResults).map(card => {
                const getText = sel => {
                    const el = card.querySelector(sel);
                    return el ? el.textContent.trim() : null;
                };
                const img = card.querySelector('img');
                return {
                    href: card.getAttribute('href'),
                    brand: getText('.product-brand'),
                    name: getText('.product-name'),
                    // Karttaki ayni anda gorunen indirimli/uzeri-cizili/TY+
                    // fiyatlarini ayirt etmek icin Trendyol'un kendi
                    // data-testid'lerini kullaniyoruz (class*="price" hepsini
                    // birden yakalayip metinlerini birlestiriyordu).
                    // Indirimli urunlerde "price-value", indirimsiz (tek
                    // fiyatli) urunlerde ise "price-section" kullaniliyor.
                    price_text: getText('[data-testid="price-value"]') || getText('[data-testid="price-section"]'),
                    rating_text: getText('.productRating, [class*="rating"]'),
                    image_url: img ? (img.getAttribute('src') || img.getAttribute('data-src')) : null,
                };
            });
        }""", max_results)

        await browser.close()
        return raw


class TrendyolSearchCollector:
    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        # Uvicorn event loop çakışmasını önlemek için ayrı thread + yeni loop'ta çalıştırıyoruz.
        raw = await asyncio.to_thread(asyncio.run, _do_search(query, max_results))

        results = []
        for item in raw:
            href = item.get("href") or ""
            if not href:
                continue
            full_url = href if href.startswith("http") else BASE_URL + href.split("?")[0]

            results.append({
                "name": item.get("name"),
                "brand": item.get("brand"),
                "url": full_url,
                "price": self._parse_price(item.get("price_text")),
                "rating": self._parse_rating(item.get("rating_text")),
                "image_url": item.get("image_url"),
            })

        return {
            "source": "trendyol",
            "query": query,
            "total_found": len(results),
            "results": results,
        }

    def _parse_price(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        # Secici bazen birden fazla fiyat/taksit metnini ic ice yakalayip
        # birlestiriyor (orn. indirimli + orijinal fiyat ayni textContent'te).
        # Tum metni temizlemek yerine gecerli bir TL fiyat kalibini ariyoruz:
        # nokta=binlik ayraci (opsiyonel), virgul=kurus.
        m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)", text)
        if not m:
            return None
        cleaned = m.group(1).replace(".", "").replace(",", ".")
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


if __name__ == "__main__":
    async def test():
        collector = TrendyolSearchCollector()
        result = await collector.search("JBL Tune 520BT")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(test())
