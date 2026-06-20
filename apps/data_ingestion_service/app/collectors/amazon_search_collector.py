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

BASE_URL = "https://www.amazon.com.tr"


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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        encoded = quote(query)
        url = f"{BASE_URL}/s?k={encoded}"
        logger.info(f"Amazon TR'de aranıyor: {query}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        raw = await page.evaluate("""(maxResults) => {
            const cards = document.querySelectorAll('div[data-component-type="s-search-result"]');
            return Array.from(cards).slice(0, maxResults).map(card => {
                // Ürün adı: h2 içindeki .a-text-normal
                const h2 = card.querySelector('h2');
                const title = h2 ? h2.textContent.trim() : null;

                // ASIN data attribute'dan
                const asin = card.getAttribute('data-asin') || null;

                // Ürün sayfası linki - /dp/ içeren ilk link
                const linkEl = card.querySelector('a[href*="/dp/"]');
                const href = linkEl ? linkEl.getAttribute('href') : null;

                // Fiyat
                const priceWholeEl = card.querySelector('.a-price .a-price-whole');
                const priceFractionEl = card.querySelector('.a-price .a-price-fraction');

                // Üzeri çizili orijinal fiyat
                const strikePriceEl = card.querySelector(
                    '.a-price[data-a-strike="true"] .a-offscreen, ' +
                    'span.a-price.a-text-price .a-offscreen'
                );

                // Puan: "5 yıldız üzerinden 4,6"
                const ratingEl = card.querySelector('span.a-icon-alt');

                // Resim
                const imgEl = card.querySelector('img.s-image');

                let priceText = null;
                if (priceWholeEl) {
                    const whole = priceWholeEl.textContent.replace(/[^0-9.]/g, '').replace('.', '');
                    const frac = priceFractionEl ? priceFractionEl.textContent.replace(/[^0-9]/g, '') : '00';
                    priceText = whole + ',' + frac;
                }

                return {
                    title: title,
                    asin: asin,
                    href: href,
                    price_text: priceText,
                    original_price_text: strikePriceEl ? strikePriceEl.textContent.trim() : null,
                    rating_text: ratingEl ? ratingEl.textContent.trim() : null,
                    image_url: imgEl ? imgEl.getAttribute('src') : null,
                };
            });
        }""", max_results)

        await browser.close()
        return raw


class AmazonSearchCollector:
    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        # headless=False gerekli: Amazon headless tarayıcıları CAPTCHA/bot engeline takıyor.
        # Uvicorn event loop çakışmasını önlemek için ayrı thread + yeni loop'ta çalıştırıyoruz.
        raw = await asyncio.to_thread(asyncio.run, _do_search(query, max_results))

        results = []
        for item in raw:
            title = item.get("title")
            asin = item.get("asin") or ""
            href = item.get("href") or ""

            if not title:
                continue

            # Tam URL: ASIN varsa /dp/ASIN, yoksa href'ten
            if asin:
                full_url = f"{BASE_URL}/dp/{asin}"
            elif href:
                full_url = href if href.startswith("http") else BASE_URL + href.split("?")[0]
            else:
                continue

            results.append({
                "name": title,
                "brand": self._extract_brand(title),
                "url": full_url,
                "asin": asin,
                "price": self._parse_price(item.get("price_text")),
                "original_price": self._parse_price(item.get("original_price_text")),
                "rating": self._parse_rating(item.get("rating_text")),
                "image_url": item.get("image_url"),
            })

        return {
            "source": "amazon",
            "query": query,
            "total_found": len(results),
            "results": results,
        }

    def _parse_price(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        # Türkçe format: "1.879,00" veya "1879,00" → 1879.0
        cleaned = re.sub(r"\.", "", text)   # binlik noktayı kaldır
        cleaned = cleaned.replace(",", ".")  # ondalık virgülü noktaya çevir
        m = re.search(r"(\d+\.?\d*)", cleaned)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

    def _parse_rating(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        # "5 yıldız üzerinden 4,6" → 4.6
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
        collector = AmazonSearchCollector()
        result = await collector.search("JBL Tune 520BT")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(test())
