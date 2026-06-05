import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScoredCompetitor:
    id: Optional[str]
    marketplace: str
    rank: Optional[int]
    seller_name: str
    seller_score: Optional[float]
    seller_review_count: Optional[int]
    seller_city: Optional[str]
    is_authorized: bool
    price: Optional[float]
    original_price: Optional[float]
    currency: str
    stock: Optional[int]
    is_in_stock: bool
    free_shipping: bool
    fast_shipping: bool
    shipment_days: Optional[int]
    threat_score: float = 0.0
    price_score: float = 0.0
    seller_quality_score: float = 0.0
    availability_score: float = 0.0
    shipping_score: float = 0.0
    tier: int = 3
    price_gap_pct: Optional[float] = None
    is_buybox_winner: bool = False


class CompetitorScorer:
    WEIGHT_PRICE = 0.40
    WEIGHT_QUALITY = 0.25
    WEIGHT_AVAILABILITY = 0.20
    WEIGHT_SHIPPING = 0.15
    AUTHORIZED_BONUS = 0.05

    def score_all(self, listings: List[Dict[str, Any]]) -> List[ScoredCompetitor]:
        in_stock = [lst for lst in listings if lst.get("is_in_stock", True)]
        prices = [lst["price"] for lst in in_stock if lst.get("price") is not None]

        p10 = statistics.quantiles(prices, n=10)[0] if len(prices) >= 2 else (min(prices) if prices else 0.0)
        p90 = statistics.quantiles(prices, n=10)[-1] if len(prices) >= 2 else (max(prices) if prices else 0.0)
        price_range = p90 - p10 if p90 > p10 else 1.0

        scored = []
        for lst in listings:
            competitor = ScoredCompetitor(
                id=lst.get("id"),
                marketplace=lst.get("marketplace", ""),
                rank=lst.get("rank"),
                seller_name=lst.get("seller_name", "Unknown"),
                seller_score=lst.get("seller_score"),
                seller_review_count=lst.get("seller_review_count"),
                seller_city=lst.get("seller_city"),
                is_authorized=bool(lst.get("is_authorized", False)),
                price=lst.get("price"),
                original_price=lst.get("original_price"),
                currency=lst.get("currency", "TRY"),
                stock=lst.get("stock"),
                is_in_stock=bool(lst.get("is_in_stock", True)),
                free_shipping=bool(lst.get("free_shipping", False)),
                fast_shipping=bool(lst.get("fast_shipping", False)),
                shipment_days=lst.get("shipment_days"),
            )

            competitor.price_score = self._price_score(competitor.price, p10, p90, price_range)
            competitor.seller_quality_score = self._seller_quality_score(
                competitor.seller_score, competitor.seller_review_count
            )
            competitor.availability_score = self._availability_score(
                competitor.is_in_stock, competitor.stock
            )
            competitor.shipping_score = self._shipping_score(
                competitor.fast_shipping, competitor.free_shipping, competitor.shipment_days
            )

            raw = (
                self.WEIGHT_PRICE * competitor.price_score
                + self.WEIGHT_QUALITY * competitor.seller_quality_score
                + self.WEIGHT_AVAILABILITY * competitor.availability_score
                + self.WEIGHT_SHIPPING * competitor.shipping_score
            )
            if competitor.is_authorized:
                raw += self.AUTHORIZED_BONUS

            competitor.threat_score = round(max(0.0, min(1.0, raw)), 4)
            scored.append(competitor)

        return scored

    def _price_score(
        self, price: Optional[float], p10: float, p90: float, price_range: float
    ) -> float:
        if price is None:
            return 0.0
        raw = (p90 - price) / price_range
        return round(max(0.0, min(1.0, raw)), 4)

    def _seller_quality_score(
        self, seller_score: Optional[float], review_count: Optional[int]
    ) -> float:
        if seller_score is None:
            return 0.5

        normalized = max(0.0, min(1.0, seller_score / 10.0))
        credibility = self._review_credibility(review_count)
        blended = credibility * normalized + (1 - credibility) * 0.5
        return round(blended, 4)

    def _review_credibility(self, review_count: Optional[int]) -> float:
        if review_count is None:
            return 0.5
        if review_count >= 1000:
            return 1.0
        if review_count >= 100:
            return 0.85
        if review_count >= 10:
            return 0.6
        return 0.3

    def _availability_score(self, is_in_stock: bool, stock: Optional[int]) -> float:
        if not is_in_stock:
            return 0.0
        if stock is None:
            return 0.6
        if stock >= 100:
            return 1.0
        if stock >= 20:
            return 0.8
        if stock >= 5:
            return 0.5
        return 0.2

    def _shipping_score(
        self, fast_shipping: bool, free_shipping: bool, shipment_days: Optional[int]
    ) -> float:
        if fast_shipping:
            return 1.0
        if free_shipping:
            return 0.8
        if shipment_days is None:
            return 0.5
        if shipment_days == 0:
            return 0.9
        if shipment_days == 1:
            return 0.75
        if shipment_days == 2:
            return 0.6
        return max(0.1, round(0.6 - (shipment_days - 2) * 0.1, 2))
