import statistics
from dataclasses import dataclass
from typing import List, Optional

from app.intelligence.competitor_scoring import ScoredCompetitor


@dataclass
class PriceRecommendation:
    suggested_price: Optional[float]
    strategy: str
    confidence: float
    rationale: str


class CompetitorTierer:
    TIER1_THRESHOLD = 0.70
    TIER2_THRESHOLD = 0.40

    def tier_all(self, scored: List[ScoredCompetitor]) -> List[ScoredCompetitor]:
        for competitor in scored:
            competitor.tier = self._assign_tier(competitor)
        self._mark_buybox_winners(scored)
        return scored

    def _assign_tier(self, competitor: ScoredCompetitor) -> int:
        if not competitor.is_in_stock:
            return 3
        if competitor.threat_score >= self.TIER1_THRESHOLD:
            return 1
        if competitor.rank == 1:
            return 1
        if competitor.threat_score >= self.TIER2_THRESHOLD:
            return 2
        return 3

    def _mark_buybox_winners(self, scored: List[ScoredCompetitor]) -> None:
        seen_marketplaces: set[str] = set()
        for competitor in sorted(scored, key=lambda c: (c.rank or 999)):
            if competitor.marketplace not in seen_marketplaces and competitor.is_in_stock:
                competitor.is_buybox_winner = True
                seen_marketplaces.add(competitor.marketplace)

    def recommend_price(self, tiered: List[ScoredCompetitor]) -> PriceRecommendation:
        tier1 = [c for c in tiered if c.tier == 1 and c.price is not None]
        tier2 = [c for c in tiered if c.tier == 2 and c.price is not None]
        all_with_price = [c for c in tiered if c.price is not None and c.is_in_stock]

        all_prices = [c.price for c in all_with_price]
        tier1_prices = [c.price for c in tier1]
        tier2_prices = [c.price for c in tier2]

        if not all_prices:
            return PriceRecommendation(
                suggested_price=None,
                strategy="UNKNOWN",
                confidence=0.1,
                rationale="Fiyat verisi bulunamadi.",
            )

        median_price = statistics.median(all_prices)
        min_price = min(all_prices)
        max_price = max(all_prices)

        buybox_price = min(tier1_prices) if tier1_prices else (min(tier2_prices) if tier2_prices else min_price)

        if len(tier1) >= 3:
            strategy = "PENETRATION"
            suggested_price = round(buybox_price * 0.98, 2)
            leader = min(tier1, key=lambda c: c.price)
            rationale = (
                f"Yuksek rekabet ({len(tier1)} Tier 1 rakip). "
                f"Pazar liderinin ({leader.seller_name}, {buybox_price:.2f} TRY) "
                f"%2 altinda giris oneriliyor."
            )
        elif tier1:
            strategy = "COMPETITIVE"
            suggested_price = buybox_price
            leader = min(tier1, key=lambda c: c.price)
            secondary = sorted(tier1, key=lambda c: c.price)[1] if len(tier1) > 1 else None
            rationale = (
                f"Pazar lideriyle esit fiyat: {leader.seller_name} ({buybox_price:.2f} TRY)."
            )
            if secondary:
                rationale += (
                    f" Ikincil tehdit: {secondary.seller_name} ({secondary.price:.2f} TRY)."
                )
        else:
            strategy = "PREMIUM"
            suggested_price = round(median_price * 1.05, 2)
            rationale = (
                f"Guclu buybox rakibi yok. Medyan fiyatin ({median_price:.2f} TRY) "
                f"%5 uzerinde premium giris oneriliyor."
            )

        confidence = self._confidence_score(tiered, all_prices)

        for competitor in tiered:
            if competitor.price is not None and suggested_price is not None:
                competitor.price_gap_pct = round(
                    ((competitor.price - suggested_price) / suggested_price) * 100, 2
                )

        return PriceRecommendation(
            suggested_price=suggested_price,
            strategy=strategy,
            confidence=confidence,
            rationale=rationale,
        )

    def _confidence_score(
        self, tiered: List[ScoredCompetitor], all_prices: List[float]
    ) -> float:
        confidence = 0.5

        total = len(tiered)
        if total >= 10:
            confidence += 0.10
        elif total >= 5:
            confidence += 0.15

        sources = len({c.marketplace for c in tiered})
        if sources >= 3:
            confidence += 0.15
        elif sources >= 2:
            confidence += 0.10

        none_prices = sum(1 for c in tiered if c.price is None)
        if none_prices > 0:
            confidence -= 0.05 * min(none_prices, 3)

        if total == 1 and sources == 1:
            confidence -= 0.15

        return round(max(0.1, min(0.95, confidence)), 3)
