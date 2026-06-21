from uuid import UUID

from sqlalchemy.orm import Session

from app.models.candidate_price import CandidatePrice, CandidatePriceBatch
from app.models.competitor import CompetitorListing, CompetitorTier
from app.models.product import SellerProduct
from app.schemas.candidate_price_schema import (
    CandidateCompetitor,
    CandidatePriceContext,
    CandidatePriceGenerateRequest,
    CandidatePriceGenerateResponse,
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

        if seller_product.our_price is None:
            raise ValueError("Seller product current price is missing.")

        competitors = self.get_latest_competitors_for_product(request.product_id)

        competitor_prices = [
            competitor.price
            for competitor in competitors
            if competitor.price > 0
        ]

        min_price = min(competitor_prices) if competitor_prices else None
        avg_price = (
            sum(competitor_prices) / len(competitor_prices)
            if competitor_prices
            else None
        )
        max_price = max(competitor_prices) if competitor_prices else None

        return CandidatePriceContext(
            product_id=request.product_id,
            seller_product_id=seller_product.id,
            current_price=float(seller_product.our_price),
            min_competitor_price=min_price,
            avg_competitor_price=avg_price,
            max_competitor_price=max_price,
            competitors=competitors,
            price_step=request.price_step,
            base_price_step=request.base_price_step,
            dense_price_step=request.dense_price_step,
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
        rows = (
            self.db.query(CompetitorTier, CompetitorListing)
            .join(
                CompetitorListing,
                CompetitorListing.id == CompetitorTier.competitor_listing_id,
            )
            .filter(CompetitorTier.product_id == product_id)
            .filter(CompetitorListing.price.isnot(None))
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

            if listing.price is None:
                continue

            competitors.append(
                CandidateCompetitor(
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

    def save_result(
        self,
        result: CandidatePriceGenerateResponse,
    ) -> CandidatePriceBatch:
        batch = CandidatePriceBatch(
            product_id=result.product_id,
            seller_product_id=result.seller_product_id,
            selected_strategy=result.selected_strategy.value,
            reason=result.reason,
            constraints_applied=result.constraints_applied,
            ignored_competitors=[
                item.model_dump()
                for item in result.ignored_competitors
            ],
            dense_regions=[
                item.model_dump()
                for item in result.dense_regions
            ],
        )

        self.db.add(batch)
        self.db.flush()

        for price in result.candidate_prices:
            candidate = CandidatePrice(
                batch_id=batch.id,
                product_id=result.product_id,
                price=price,
                source_strategy=result.selected_strategy.value,
                reason_codes=result.constraints_applied,
            )
            self.db.add(candidate)

        self.db.commit()
        self.db.refresh(batch)

        return batch