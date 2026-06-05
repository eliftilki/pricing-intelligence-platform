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


class TrendyolCollector(BaseMarketplaceCollector):
    async def scrape_product_by_url(self, url: str) -> Dict[str, Any]:
        return await self._scrape_with_retry(self._scrape_impl, url, max_retries=3)

    async def _scrape_impl(self, url: str) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            logger.info(f"Scraping Trendyol: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            result = await page.evaluate("""() => {
                try {
                    const data = window.__envoy__SHARED_PROPS;
                    const product = data.product;
                    if (!product) return { error: "product not found" };

                    const listing = product.merchantListing || {};
                    // otherMerchants zaten rank sirasina gore dizilmis (index 0 = rank 1)
                    const allMerchants = listing.otherMerchants || [];

                    const mapMerchant = (m, rank) => {
                        // Fiyat bilgisi: once variants[0], yoksa m.price
                        const variant = (m.variants && m.variants[0]) ? m.variants[0] : null;
                        const priceObj = variant ? variant.price : (m.price || {});

                        const price = (priceObj.discountedPrice || {}).value
                            ?? (priceObj.sellingPrice || {}).value
                            ?? null;
                        const originalPrice = (priceObj.originalPrice || {}).value ?? null;
                        const discountRate = priceObj.discountPercentage
                            ?? priceObj.discountRatio
                            ?? null;

                        // Stok: once variants[0].quantity, yoksa m.stockCount
                        const stock = variant ? (variant.quantity ?? null) : (m.stockCount ?? null);
                        const inStock = variant ? (variant.inStock !== false) : (m.inStock !== false);

                        // Kargo: freeCargo / rushDelivery
                        const freeShipping = !!(m.freeCargo || m.freeShipping || (variant && variant.freeCargo));
                        const fastShipping = !!(m.rushDelivery || m.fastDelivery);

                        return {
                            rank: rank,
                            seller_name: m.name || m.merchantName || null,
                            seller_score: (m.sellerScore || {}).value || null,
                            seller_review_count: null,
                            seller_city: null,
                            is_authorized: !!(m.official || m.isOfficial),
                            price: typeof price === "number" ? price : null,
                            original_price: typeof originalPrice === "number" ? originalPrice : null,
                            discount_rate: typeof discountRate === "number" ? discountRate : null,
                            currency: "TRY",
                            stock: typeof stock === "number" ? stock : null,
                            is_in_stock: inStock,
                            free_shipping: freeShipping,
                            fast_shipping: fastShipping,
                            shipment_days: null
                        };
                    };

                    const sellers = allMerchants.map((m, i) => mapMerchant(m, i + 1));

                    const ratingScore = product.ratingScore || product.rating || {};
                    const brand = (product.brand || {}).name || null;

                    return {
                        product: {
                            name: product.name || null,
                            sku: String(product.id || product.productCode || ""),
                            brand: brand,
                            rating: typeof ratingScore.averageRating === "number"
                                ? ratingScore.averageRating
                                : (typeof ratingScore.point === "number" ? ratingScore.point : null),
                            review_count: typeof ratingScore.totalCount === "number"
                                ? ratingScore.totalCount
                                : (typeof ratingScore.total === "number" ? ratingScore.total : null)
                        },
                        sellers: sellers
                    };
                } catch (e) {
                    return { error: e.message };
                }
            }""")

            await browser.close()

        if "error" in result:
            logger.error(f"JS evaluation error: {result['error']}")
            result["product"] = {"name": None, "sku": None, "brand": None, "rating": None, "review_count": None}
            result["sellers"] = []

        # SKU URL'den de çıkarılabilir (fallback)
        sku_match = re.search(r"-p-(\d+)(?:\?.*)?$", url)
        if sku_match and not (result.get("product", {}).get("sku")):
            result["product"]["sku"] = sku_match.group(1)

        return {
            "source": "trendyol",
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "product": result.get("product", {}),
            "sellers": result.get("sellers", []),
        }


if __name__ == "__main__":
    async def test():
        c = TrendyolCollector()
        url = "https://www.trendyol.com/jbl/tune-520bt-multi-connect-wireless-kulaklik-beyaz-p-701999209"
        data = await c.scrape_product_by_url(url)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    asyncio.run(test())
