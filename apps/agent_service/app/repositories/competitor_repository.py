from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.competitor import CompetitorListing, CompetitorPriceHistory, CompetitorTier
from app.models.scrape import MarketplaceScrape
from app.models.agent_run import AgentRun


class CompetitorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_competitor_listings(self, product_id: UUID, lookback_hours: int) -> list[CompetitorListing]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        subquery = (
            self.db.query(
                CompetitorListing.marketplace.label("marketplace"),
                CompetitorListing.seller_name.label("seller_name"),
                func.max(CompetitorListing.scraped_at).label("max_scraped_at"),
            )
            .join(MarketplaceScrape, MarketplaceScrape.id == CompetitorListing.scrape_id)
            .filter(MarketplaceScrape.product_id == product_id, CompetitorListing.scraped_at >= cutoff)
            .group_by(CompetitorListing.marketplace, CompetitorListing.seller_name)
            .subquery()
        )

        return (
            self.db.query(CompetitorListing)
            .join(MarketplaceScrape, MarketplaceScrape.id == CompetitorListing.scrape_id)
            .join(
                subquery,
                and_(
                    CompetitorListing.marketplace == subquery.c.marketplace,
                    CompetitorListing.seller_name == subquery.c.seller_name,
                    CompetitorListing.scraped_at == subquery.c.max_scraped_at,
                ),
            )
            .filter(MarketplaceScrape.product_id == product_id)
            .order_by(CompetitorListing.marketplace, CompetitorListing.rank.asc().nullslast())
            .all()
        )

    def get_price_history_summary(self, product_id: UUID, marketplace: str, seller_name: str, lookback_hours: int = 168) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        row = (
            self.db.query(
                func.min(CompetitorPriceHistory.price).label("min_price"),
                func.max(CompetitorPriceHistory.price).label("max_price"),
                func.avg(CompetitorPriceHistory.price).label("avg_price"),
                func.count(CompetitorPriceHistory.id).label("price_point_count"),
            )
            .filter(
                CompetitorPriceHistory.product_id == product_id,
                CompetitorPriceHistory.marketplace == marketplace,
                CompetitorPriceHistory.seller_name == seller_name,
                CompetitorPriceHistory.recorded_at >= cutoff,
            )
            .first()
        )

        if row is None:
            return {"min_price": None, "max_price": None, "avg_price": None, "price_point_count": 0}

        return {
            "min_price": self._to_float(row.min_price),
            "max_price": self._to_float(row.max_price),
            "avg_price": self._to_float(row.avg_price),
            "price_point_count": int(row.price_point_count or 0),
        }

    def delete_existing_tiers_for_listings(self, listing_ids: list[UUID]) -> None:
        if not listing_ids:
            return

        (
            self.db.query(CompetitorTier)
            .filter(CompetitorTier.competitor_listing_id.in_(listing_ids))
            .delete(synchronize_session=False)
        )

    def create_competitor_tier(
        self,
        product_id: UUID,
        listing: CompetitorListing,
        tier: str,
        competitor_strength_score: float,
        buybox_threat_score: float,
        price_aggression_score: float,
        reason_codes: list[str],
    ) -> CompetitorTier:
        obj = CompetitorTier(
            product_id=product_id,
            competitor_seller_id=listing.competitor_seller_id,
            competitor_listing_id=listing.id,
            marketplace=listing.marketplace,
            seller_name=listing.seller_name,
            tier=tier,
            competitor_strength_score=competitor_strength_score,
            buybox_threat_score=buybox_threat_score,
            price_aggression_score=price_aggression_score,
            reason_codes=reason_codes,
            analyzed_at=datetime.now(timezone.utc),
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_agent_run(self, product_id: UUID, input_payload: dict) -> AgentRun:
        run = AgentRun(
            product_id=product_id,
            run_type="COMPETITOR_INTELLIGENCE",
            status="STARTED",
            input_payload=input_payload,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish_agent_run(self, run: AgentRun, status: str, output_payload: dict | None = None, error_message: str | None = None) -> None:
        run.status = status
        run.output_payload = output_payload
        run.error_message = error_message
        run.finished_at = datetime.now(timezone.utc)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def _to_float(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
