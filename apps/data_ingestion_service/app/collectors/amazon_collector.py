import asyncio
import json
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


class AmazonCollector(BaseMarketplaceCollector):
    async def scrape_product_by_url(self, url: str) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                locale="tr-TR",
                extra_http_headers={"Accept-Language": "tr-TR,tr;q=0.9"},
            )
            page = await context.new_page()

            print(f"[-] Amazon verisi cekiliyor: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            # \\ in Python string → single \ in JavaScript  (e.g. \\d → \d in JS regex)
            product_info = await page.evaluate("""() => {
                const getText = (sel) => {
                    const el = document.querySelector(sel);
                    return el ? el.textContent.trim() : null;
                };

                const name = getText("#productTitle");

                let priceText = null;
                const priceSelectors = [
                    "#priceblock_ourprice",
                    "#priceblock_dealprice",
                    "#priceblock_saleprice",
                    ".a-price.a-text-price.a-size-medium .a-offscreen",
                    "#apex_desktop .a-price .a-offscreen",
                    "#apex_desktop_newAccordionRow .a-price .a-offscreen",
                    "#corePrice_feature_div .a-price .a-offscreen",
                    ".a-price .a-offscreen"
                ];
                for (const sel of priceSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        priceText = el.textContent.trim();
                        break;
                    }
                }

                const parsePrice = (text) => {
                    if (!text) return null;
                    const match = text.replace(/\\s/g, "").match(/[\\d.,]+/);
                    if (!match) return null;
                    return parseFloat(match[0].replace(/\\./g, "").replace(",", ".")) || null;
                };

                // Ustu cizili orijinal fiyat — sadece gercek indirimde gorunur, liste fiyatini almiyoruz
                const originalPriceText = getText(".basisPrice .a-offscreen");

                const ratingEl = document.querySelector("#acrPopover");
                let rating = null;
                if (ratingEl) {
                    const title = ratingEl.getAttribute("title") || "";
                    const m = title.match(/([0-9][,.][0-9])/);
                    rating = m ? parseFloat(m[1].replace(",", ".")) : null;
                }

                const reviewText = getText("#acrCustomerReviewText");
                let reviewCount = null;
                if (reviewText) {
                    const m = reviewText.replace(/[.,\\s]/g, "").match(/\\d+/);
                    reviewCount = m ? parseInt(m[0], 10) : null;
                }

                const brandEl = document.querySelector("#bylineInfo");
                let brand = null;
                if (brandEl) {
                    brand = brandEl.textContent.trim()
                        .replace(/^(Marka:|Brand:|Ziyaret:|Visit the)\\s*/i, "")
                        .replace(/[''']?(u|yu|i|yi|nu|nü|nı|yı)?\\s*(ziyaret edin|Store|Mağazası|Magazasi|Store'u|ziyaret).*$/i, "")
                        .trim() || null;
                }

                const sellerEl = document.querySelector(
                    "#merchant-info a, #sellerProfileTriggerId, #tabular-buybox-truncate-0 .tabular-buybox-text a"
                );
                const sellerName = sellerEl ? sellerEl.textContent.trim() : "Amazon";

                const stockText = getText("#availability span, #outOfStock span");
                const isInStock = stockText
                    ? !/(stokta yok|out of stock|unavailable)/i.test(stockText)
                    : true;

                const asinEl = document.querySelector("[data-asin]");
                const asin = asinEl ? asinEl.getAttribute("data-asin") : null;

                return {
                    name,
                    brand,
                    asin,
                    price: parsePrice(priceText),
                    original_price: parsePrice(originalPriceText),
                    rating,
                    review_count: reviewCount,
                    seller_name: sellerName,
                    is_in_stock: isInStock,
                    stock_text: stockText
                };
            }""")

            await browser.close()

        price = product_info.get("price")
        original_price = product_info.get("original_price")
        discount_rate = None
        if price and original_price and original_price > price:
            discount_rate = round((1 - price / original_price) * 100, 1)

        return {
            "source": "amazon",
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "product": {
                "name": product_info.get("name"),
                "sku": product_info.get("asin"),
                "brand": product_info.get("brand"),
                "rating": product_info.get("rating"),
                "review_count": product_info.get("review_count"),
            },
            "sellers": [
                {
                    "rank": 1,
                    "seller_name": product_info.get("seller_name"),
                    "seller_score": None,
                    "seller_review_count": None,
                    "seller_city": None,
                    "is_authorized": False,
                    "price": price,
                    "original_price": original_price,
                    "discount_rate": discount_rate,
                    "currency": "TRY",
                    "stock": None,
                    "is_in_stock": product_info.get("is_in_stock", True),
                    "free_shipping": False,
                    "fast_shipping": False,
                    "shipment_days": None,
                }
            ],
        }


if __name__ == "__main__":
    async def test():
        c = AmazonCollector()
        url = "https://www.amazon.com.tr/dp/B0BZ8HHTFV"
        data = await c.scrape_product_by_url(url)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    asyncio.run(test())
