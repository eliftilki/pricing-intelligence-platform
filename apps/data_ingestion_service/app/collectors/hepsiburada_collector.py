import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from playwright.async_api import async_playwright

try:
    from app.collectors.base import BaseMarketplaceCollector
except ImportError:
    from base import BaseMarketplaceCollector

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)


class HepsiburadaCollector(BaseMarketplaceCollector):
    async def scrape_product_by_url(self, url: str) -> Dict[str, Any]:
        return await self._scrape_with_retry(self._scrape_impl, url, max_retries=3)

    async def _scrape_impl(self, url: str) -> Dict[str, Any]:
        queue: asyncio.Queue = asyncio.Queue()

        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="chrome", headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="tr-TR",
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                "window.chrome = { runtime: {} };"
            )
            page = await context.new_page()

            async def handle_response(response):
                try:
                    if "/api/v1/product/listings/" not in response.url:
                        return
                    try:
                        body = await response.json()
                    except Exception:
                        return
                    await queue.put(body)
                except Exception as e:
                    logger.error(f"Response handler error: {e}")

            page.on("response", lambda r: asyncio.create_task(handle_response(r)))

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(6000)

            # Ürün adı, puan ve yorum sayısı sayfanın HTML'inden alınıyor.
            product_info = await page.evaluate("""() => {
                const getText = sel => {
                    const el = document.querySelector(sel);
                    return el ? el.textContent.trim() : null;
                };

                const name = getText("h1[itemprop='name']")
                    || getText("h1.product-name")
                    || getText("h1");

                const ratingEl = document.querySelector(
                    "[itemprop='ratingValue'], .product-rating .score, .star-point"
                );
                const rating = ratingEl
                    ? parseFloat(ratingEl.textContent.trim().replace(",", ".")) || null
                    : null;

                const reviewEl = document.querySelector(
                    "[itemprop='reviewCount'], .review-count, .comment-count"
                );
                const reviewText = reviewEl ? reviewEl.textContent.trim() : null;
                const reviewMatch = reviewText ? reviewText.match(/\\d[\\d.,]*/) : null;
                const reviewCount = reviewMatch
                    ? parseInt(reviewMatch[0].replace(/[.,]/g, ""), 10) || null
                    : null;

                const brandEl = document.querySelector(
                    "[itemprop='brand'] [itemprop='name'], .product-brand-name"
                );
                const brand = brandEl ? brandEl.textContent.trim() : null;

                return { name, rating, reviewCount, brand };
            }""")

            await browser.close()

        sku_match = re.search(r"-p-([A-Z0-9]+)(?:\?.*)?$", url)
        sku = sku_match.group(1) if sku_match else None

        sellers = []
        if not queue.empty():
            raw = await queue.get()
            listings = raw.get("data", {}).get("listings", [])
            for listing in listings:
                rating_summary = listing.get("ratingSummary") or {}
                labels = listing.get("merchantLabels") or []
                is_authorized = any(
                    "yetkili" in (lbl.get("labelName") or "").lower()
                    for lbl in labels
                )
                sellers.append({
                    "rank": listing.get("buyboxOrder"),
                    "seller_name": listing.get("merchantName"),
                    "seller_score": rating_summary.get("lifetimeRating"),
                    "seller_review_count": rating_summary.get("ratingQuantity"),
                    "seller_city": listing.get("merchantCity"),
                    "is_authorized": is_authorized,
                    "price": (listing.get("price") or {}).get("value"),
                    "original_price": (listing.get("originalPrice") or {}).get("value"),
                    "discount_rate": listing.get("discountRate"),
                    "currency": "TRY",
                    "stock": listing.get("quantity"),
                    "is_in_stock": bool(listing.get("isSalable")),
                    "free_shipping": bool(listing.get("freeShipping")),
                    "fast_shipping": bool(listing.get("fastShipping")),
                    "shipment_days": listing.get("shipmentDay"),
                })

        return {
            "source": "hepsiburada",
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "product": {
                "name": product_info.get("name"),
                "sku": sku,
                "brand": product_info.get("brand"),
                "rating": product_info.get("rating"),
                "review_count": product_info.get("reviewCount"),
            },
            "sellers": sellers,
        }


if __name__ == "__main__":
    async def test():
        c = HepsiburadaCollector()
        url = "https://www.hepsiburada.com/jbl-tune-520bt-multi-connect-wireless-kulaklik-beyaz-p-HBCV00004D5VKJ"
        data = await c.scrape_product_by_url(url)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    asyncio.run(test())
