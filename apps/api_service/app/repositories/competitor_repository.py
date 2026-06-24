from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.competitor import CompetitorListing, CompetitorTier, MarketplaceScrape
from app.repositories.base_repository import BaseRepository


class CompetitorRepository(BaseRepository):
    def __init__(self, db: Session):
        self.db = db

    def list_latest_listings(self, product_id: UUID, limit: int = 100, offset: int = 0):
        ranked_listings = (
            self.db.query(
                CompetitorListing.id.label("listing_id"),
                func.row_number()
                .over(
                    partition_by=[
                        CompetitorListing.marketplace,
                        func.lower(func.trim(CompetitorListing.seller_name)),
                    ],
                    order_by=[
                        CompetitorListing.scraped_at.desc(),
                        CompetitorListing.created_at.desc(),
                        CompetitorListing.id.desc(),
                    ],
                )
                .label("row_number"),
            )
            .join(MarketplaceScrape, CompetitorListing.scrape_id == MarketplaceScrape.id)
            .filter(MarketplaceScrape.product_id == product_id)
            .subquery()
        )

        query = (
            self.db.query(CompetitorListing)
            .join(ranked_listings, CompetitorListing.id == ranked_listings.c.listing_id)
            .filter(ranked_listings.c.row_number == 1)
            .order_by(
                CompetitorListing.marketplace,
                CompetitorListing.rank.asc().nullslast(),
                CompetitorListing.scraped_at.desc(),
            )
        )
        return self.paginate(query, limit, offset).all()

    def list_tiers(self, product_id: UUID, limit: int = 100, offset: int = 0):
        ranked_tiers = (
            self.db.query(
                CompetitorTier.id.label("tier_id"),
                func.row_number()
                .over(
                    partition_by=[
                        CompetitorTier.marketplace,
                        func.lower(func.trim(CompetitorTier.seller_name)),
                    ],
                    order_by=[
                        CompetitorTier.analyzed_at.desc(),
                        CompetitorTier.id.desc(),
                    ],
                )
                .label("row_number"),
            )
            .filter(CompetitorTier.product_id == product_id)
            .subquery()
        )

        query = (
            self.db.query(CompetitorTier)
            .join(ranked_tiers, CompetitorTier.id == ranked_tiers.c.tier_id)
            .filter(ranked_tiers.c.row_number == 1)
            .order_by(
                CompetitorTier.marketplace,
                CompetitorTier.buybox_threat_score.desc().nullslast(),
                CompetitorTier.analyzed_at.desc(),
            )
        )
        return self.paginate(query, limit, offset).all()
