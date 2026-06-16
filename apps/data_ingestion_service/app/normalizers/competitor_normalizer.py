from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class CompetitorListingCreate:
    scrape_id: UUID
    marketplace: str
    rank: Optional[int]
    seller_name: str
    seller_score: Optional[float]
    seller_review_count: Optional[int]
    seller_city: Optional[str]
    is_authorized: bool
    price: Optional[float]
    original_price: Optional[float]
    discount_rate: Optional[float]
    currency: str
    stock: Optional[int]
    is_in_stock: bool
    free_shipping: bool
    fast_shipping: bool
    shipment_days: Optional[int]
    scraped_at: datetime


@dataclass
class PriceHistoryCreate:
    product_id: UUID
    marketplace: str
    seller_name: str
    price: float
    recorded_at: datetime


class CompetitorNormalizer:
    def normalize(
        self,
        raw: Dict[str, Any],
        scrape_id: UUID,
        product_id: UUID,
    ) -> tuple[List[CompetitorListingCreate], List[PriceHistoryCreate]]:
        marketplace = (raw.get("source") or "").upper()
        scraped_at_str = raw.get("scraped_at")
        try:
            scraped_at = datetime.fromisoformat(scraped_at_str) if scraped_at_str else datetime.now(timezone.utc)
        except ValueError:
            scraped_at = datetime.now(timezone.utc)

        listings: List[CompetitorListingCreate] = []
        price_histories: List[PriceHistoryCreate] = []

        for seller in raw.get("sellers") or []:
            seller_name = seller.get("seller_name") or "Unknown"
            price = self._to_float(seller.get("price"))
            original_price = self._to_float(seller.get("original_price"))

            # Platform'un verdiği discount_rate'e güvenmiyoruz.
            # original_price gerçekten price'tan yüksekse kendimiz hesaplıyoruz.
            if price is not None and original_price is not None and original_price > price:
                discount_rate = round((original_price - price) / original_price * 100, 2)
            else:
                discount_rate = None  # indirim yok veya veri eksik
            displayed_original_price = (
                original_price
                if price is not None and original_price is not None and original_price > price
                else None
            )

            listing = CompetitorListingCreate(
                scrape_id=scrape_id,
                marketplace=marketplace,
                rank=self._to_int(seller.get("rank")),
                seller_name=seller_name,
                seller_score=self._to_float(seller.get("seller_score")),
                seller_review_count=self._to_int(seller.get("seller_review_count")),
                seller_city=seller.get("seller_city"),
                is_authorized=bool(seller.get("is_authorized", False)),
                price=price,
                original_price=displayed_original_price,
                discount_rate=discount_rate,
                currency=seller.get("currency") or "TRY",
                stock=self._to_int(seller.get("stock")),
                is_in_stock=bool(seller.get("is_in_stock", True)),
                free_shipping=bool(seller.get("free_shipping", False)),
                fast_shipping=bool(seller.get("fast_shipping", False)),
                shipment_days=self._to_int(seller.get("shipment_days")),
                scraped_at=scraped_at,
            )
            listings.append(listing)

            if price is not None:
                price_histories.append(PriceHistoryCreate(
                    product_id=product_id,
                    marketplace=marketplace,
                    seller_name=seller_name,
                    price=price,
                    recorded_at=scraped_at,
                ))

        return listings, price_histories

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
