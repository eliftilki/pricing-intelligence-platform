import statistics
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.intelligence.competitor_scoring import CompetitorScorer
from app.intelligence.competitor_tiering import CompetitorTierer
from app.repositories.competitor_intelligence_repository import CompetitorIntelligenceRepository
from app.schemas.competitor_intelligence_schema import (
    CompetitorIntelligenceRunRequest,
    CompetitorIntelligenceRunResponse,
    PriceRangeSchema,
    PriceRecommendationSchema,
    ScoredCompetitorSchema,
)


class CompetitorIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompetitorIntelligenceRepository(db)
        self.scorer = CompetitorScorer()
        self.tierer = CompetitorTierer()

    def run(
        self, payload: CompetitorIntelligenceRunRequest
    ) -> CompetitorIntelligenceRunResponse:
        listings = self.repo.get_listings_by_session(payload.session_id)

        if not listings:
            return CompetitorIntelligenceRunResponse(
                session_id=payload.session_id,
                product_id=payload.product_id,
                total_competitors=0,
                price_range=PriceRangeSchema(min=None, max=None, median=None, mean=None),
                buybox_prices={},
                recommendation=PriceRecommendationSchema(
                    suggested_price=None,
                    strategy="UNKNOWN",
                    confidence=0.0,
                    rationale="Bu session icin veri bulunamadi.",
                ),
                competitors=[],
            )

        scored = self.scorer.score_all(listings)
        tiered = self.tierer.tier_all(scored)
        recommendation = self.tierer.recommend_price(tiered)

        all_prices = [c.price for c in tiered if c.price is not None and c.is_in_stock]
        price_range = PriceRangeSchema(
            min=min(all_prices) if all_prices else None,
            max=max(all_prices) if all_prices else None,
            median=round(statistics.median(all_prices), 2) if all_prices else None,
            mean=round(statistics.mean(all_prices), 2) if all_prices else None,
        )

        buybox_prices: dict[str, Optional[float]] = {}
        for competitor in tiered:
            mp = competitor.marketplace
            if competitor.is_buybox_winner:
                buybox_prices[mp] = competitor.price

        competitors_out = [
            ScoredCompetitorSchema(
                id=c.id,
                marketplace=c.marketplace,
                rank=c.rank,
                seller_name=c.seller_name,
                seller_score=c.seller_score,
                seller_review_count=c.seller_review_count,
                seller_city=c.seller_city,
                is_authorized=c.is_authorized,
                price=c.price,
                original_price=c.original_price,
                currency=c.currency,
                stock=c.stock,
                is_in_stock=c.is_in_stock,
                free_shipping=c.free_shipping,
                fast_shipping=c.fast_shipping,
                shipment_days=c.shipment_days,
                tier=c.tier,
                threat_score=c.threat_score,
                price_score=c.price_score,
                seller_quality_score=c.seller_quality_score,
                availability_score=c.availability_score,
                shipping_score=c.shipping_score,
                price_gap_pct=c.price_gap_pct,
                is_buybox_winner=c.is_buybox_winner,
            )
            for c in sorted(tiered, key=lambda x: (x.tier, -(x.threat_score or 0)))
        ]

        return CompetitorIntelligenceRunResponse(
            session_id=payload.session_id,
            product_id=payload.product_id,
            total_competitors=len(tiered),
            price_range=price_range,
            buybox_prices=buybox_prices,
            recommendation=PriceRecommendationSchema(
                suggested_price=recommendation.suggested_price,
                strategy=recommendation.strategy,
                confidence=recommendation.confidence,
                rationale=recommendation.rationale,
            ),
            competitors=competitors_out,
        )
