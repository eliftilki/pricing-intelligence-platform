from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseMarketplaceCollector(ABC):
    """
    Standart çıktı şeması:
    {
        "source": str,           # "hepsiburada" | "trendyol" | "amazon"
        "url": str,
        "scraped_at": str,       # ISO 8601 UTC
        "product": {
            "name": str | None,
            "sku": str | None,
            "brand": str | None,
            "rating": float | None,      # ürün puanı
            "review_count": int | None
        },
        "sellers": [
            {
                "rank": int | None,           # buybox sırası
                "seller_name": str | None,
                "seller_score": float | None, # satıcı puanı
                "seller_review_count": int | None,
                "seller_city": str | None,
                "is_authorized": bool,
                "price": float | None,
                "original_price": float | None,
                "discount_rate": float | None,  # yüzde
                "currency": str,
                "stock": int | None,
                "is_in_stock": bool,
                "free_shipping": bool,
                "fast_shipping": bool,
                "shipment_days": int | None
            }
        ]
    }
    """

    @abstractmethod
    async def scrape_product_by_url(self, url: str) -> Dict[str, Any]:
        pass
