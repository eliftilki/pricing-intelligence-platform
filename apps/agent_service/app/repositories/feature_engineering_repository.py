from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.competitor import CompetitorListing, CompetitorTier
from app.models.market_event import MarketEventFeatures
from app.models.product import SellerProduct


class FeatureEngineeringRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_seller_product(
        self,
        product_id: UUID,
        seller_product_id: UUID | None = None,
    ) -> SellerProduct:
        query = self.db.query(SellerProduct)

        if seller_product_id:
            seller_product = query.filter(SellerProduct.id == seller_product_id).first()
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

    def get_competitor_features(
        self,
        product_id: UUID,
        marketplace: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """
        competitor_tiers (tier + skorlar) ile competitor_listings (fiyat + stok)
        tablolarini competitor_listing_id uzerinden join eder. Ayni listing icin
        birden fazla tier kaydi varsa en son analiz edilen (analyzed_at DESC) alinir.
        """
        query = (
            self.db.query(CompetitorTier, CompetitorListing)
            .join(CompetitorListing, CompetitorListing.id == CompetitorTier.competitor_listing_id)
            .filter(CompetitorTier.product_id == product_id)
        )

        if marketplace:
            query = query.filter(CompetitorTier.marketplace == marketplace.upper())

        query = query.order_by(CompetitorTier.analyzed_at.desc()).limit(limit)

        seen_listing_ids: set[UUID] = set()
        features: list[dict] = []

        for tier, listing in query.all():
            if listing.id in seen_listing_ids:
                continue
            seen_listing_ids.add(listing.id)

            features.append(
                {
                    "seller_name": tier.seller_name,
                    "marketplace": tier.marketplace,
                    "tier": tier.tier,
                    "price": float(listing.price) if listing.price is not None else None,
                    "is_in_stock": listing.is_in_stock,
                    "competitor_strength_score": (
                        float(tier.competitor_strength_score)
                        if tier.competitor_strength_score is not None
                        else None
                    ),
                    "buybox_threat_score": (
                        float(tier.buybox_threat_score)
                        if tier.buybox_threat_score is not None
                        else None
                    ),
                    "price_aggression_score": (
                        float(tier.price_aggression_score)
                        if tier.price_aggression_score is not None
                        else None
                    ),
                }
            )

        return features

    def get_fresh_market_event_features(
        self,
        product_id: UUID,
        max_age_hours: int = 48,
    ) -> MarketEventFeatures | None:
        """
        event_agent_node ayni graph calismasinda state'e market_event_features
        yazmamissa (calismadiysa/hata verdiyse) bu DB fallback'i kullanilir.
        market_intelligence_repository.get_fresh_market_event_features ile
        ayni TTL mantigi (varsayilan 48 saat) - iki tablo da MarketEventFeatures'a
        bakiyor, sadece cagiran node farkli.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        return (
            self.db.query(MarketEventFeatures)
            .filter(
                MarketEventFeatures.product_id == product_id,
                MarketEventFeatures.generated_at >= cutoff,
            )
            .order_by(MarketEventFeatures.generated_at.desc())
            .first()
        )

    def create_agent_run(self, product_id: UUID, input_payload: dict) -> AgentRun:
        run = AgentRun(
            product_id=product_id,
            run_type="FEATURE_ENGINEERING",
            status="STARTED",
            input_payload=input_payload,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish_agent_run(
        self,
        run: AgentRun,
        status: str,
        output_payload: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        run.status = status
        run.output_payload = output_payload
        run.error_message = error_message
        run.finished_at = datetime.now(timezone.utc)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
