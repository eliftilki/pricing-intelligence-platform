from uuid import UUID
from sqlalchemy.orm import Session
from app.models.competitor import CompetitorListing, CompetitorTier, MarketplaceScrape
from app.repositories.base_repository import BaseRepository


class CompetitorRepository(BaseRepository):
    def __init__(self, db: Session):
        self.db = db

    def list_latest_listings(self, product_id: UUID, limit: int = 100, offset: int = 0):
        query = (
            self.db.query(CompetitorListing)
            .join(MarketplaceScrape, CompetitorListing.scrape_id == MarketplaceScrape.id)
            .filter(MarketplaceScrape.product_id == product_id)
            .order_by(CompetitorListing.scraped_at.desc())
        )
        return self.paginate(query, limit, offset).all()

    def list_tiers(self, product_id: UUID, limit: int = 100, offset: int = 0):
        query = (
            self.db.query(CompetitorTier)
            .filter(CompetitorTier.product_id == product_id)
            .order_by(CompetitorTier.analyzed_at.desc())
        )
        return self.paginate(query, limit, offset).all()
