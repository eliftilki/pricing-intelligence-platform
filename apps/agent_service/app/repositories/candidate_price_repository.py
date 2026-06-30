from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pricing_policy import COMPETITOR_DATA_MAX_AGE_HOURS
from app.models.competitor import CompetitorListing, CompetitorTier
from app.models.product import SellerProduct
from app.schemas.candidate_price_schema import (
    CandidateCompetitor,
    CandidatePriceContext,
    CandidatePriceGenerateRequest,
)


class CandidatePriceRepository:
    def __init__(self, db: Session):
        self.db = db

    def build_context_from_product(
        self,
        request: CandidatePriceGenerateRequest,
    ) -> CandidatePriceContext:
        seller_product = self._get_seller_product(
            product_id=request.product_id,
            seller_product_id=request.seller_product_id,
        )

        competitors = self.get_latest_competitors_for_product(request.product_id)

        if not competitors:
            raise ValueError(
                "No current positive TIER_1 or TIER_2 competitor prices were found "
                "across marketplaces."
            )

        return CandidatePriceContext(
            product_id=request.product_id,
            seller_product_id=seller_product.id,
            competitors=competitors,
        )

    def _get_seller_product(
        self,
        product_id: UUID,
        seller_product_id: UUID | None = None,
    ) -> SellerProduct:
        query = self.db.query(SellerProduct)

        if seller_product_id:
            seller_product = (
                query
                .filter(SellerProduct.id == seller_product_id)
                .first()
            )
        else:
            seller_product = (
                query
                .filter(SellerProduct.product_id == product_id)
                .filter(SellerProduct.is_active.is_(True))
                .order_by(SellerProduct.updated_at.desc())
                .first()
            )

        if not seller_product:
            raise ValueError("Seller product not found.")

        return seller_product

    def get_latest_competitors_for_product(
        self,
        product_id: UUID,
        limit: int = 100,
    ) -> list[CandidateCompetitor]:
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=COMPETITOR_DATA_MAX_AGE_HOURS
        )

        rows = (
            self.db.query(CompetitorTier, CompetitorListing)
            .join(
                CompetitorListing,
                CompetitorListing.id == CompetitorTier.competitor_listing_id,
            )
            .filter(CompetitorTier.product_id == product_id)
            .filter(CompetitorTier.tier.in_(("TIER_1", "TIER_2")))
            .filter(CompetitorListing.price.isnot(None))
            .filter(CompetitorListing.scraped_at >= cutoff)
            .filter(CompetitorTier.analyzed_at >= cutoff)
            .order_by(CompetitorTier.analyzed_at.desc())
            .limit(limit)
            .all()
        )

        competitors: list[CandidateCompetitor] = []
        seen_listing_ids: set[UUID] = set()

        for tier, listing in rows:
            if listing.id in seen_listing_ids:
                continue

            seen_listing_ids.add(listing.id)

            if listing.price is None or listing.price <= 0:
                continue

            competitors.append(
                CandidateCompetitor(
                    marketplace=listing.marketplace.upper(),
                    seller_name=tier.seller_name,
                    price=float(listing.price),
                    tier=tier.tier,
                    buybox_threat_score=(
                        float(tier.buybox_threat_score)
                        if tier.buybox_threat_score is not None
                        else None
                    ),
                )
            )

        return competitors

