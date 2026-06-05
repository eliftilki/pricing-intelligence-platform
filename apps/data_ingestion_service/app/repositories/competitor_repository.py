from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.competitor_listing import CompetitorListing
from app.models.price_history import PriceHistory
from app.models.product import Product, SellerProduct
from app.models.scrape_session import MarketplaceScrape, ScrapeSession
from app.normalizers.competitor_normalizer import CompetitorListingCreate, PriceHistoryCreate


class CompetitorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, name: str, brand: Optional[str], category: Optional[str]) -> Product:
        product = Product(name=name, brand=brand, category=category)
        self.db.add(product)
        self.db.flush()
        return product

    def create_seller_product(
        self, product_id: UUID, marketplace: str, url: str, sku: Optional[str] = None
    ) -> SellerProduct:
        sp = SellerProduct(
            product_id=product_id,
            marketplace=marketplace,
            marketplace_url=url,
            marketplace_sku=sku,
        )
        self.db.add(sp)
        self.db.flush()
        return sp

    def get_seller_products_for_marketplaces(
        self, product_id: UUID, marketplaces: List[str]
    ) -> List[SellerProduct]:
        return (
            self.db.query(SellerProduct)
            .filter(
                SellerProduct.product_id == product_id,
                SellerProduct.marketplace.in_(marketplaces),
            )
            .all()
        )

    def create_session(self, product_id: UUID) -> ScrapeSession:
        session = ScrapeSession(product_id=product_id, status="RUNNING")
        self.db.add(session)
        self.db.flush()
        return session

    def update_session_status(
        self,
        session_id: UUID,
        status: str,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        self.db.query(ScrapeSession).filter(ScrapeSession.id == session_id).update(
            {
                "status": status,
                "completed_at": completed_at or datetime.now(timezone.utc),
                "error_message": error_message,
            }
        )

    def create_marketplace_scrape(
        self,
        session_id: UUID,
        seller_product_id: UUID,
        marketplace: str,
        url: str,
    ) -> MarketplaceScrape:
        ms = MarketplaceScrape(
            session_id=session_id,
            seller_product_id=seller_product_id,
            marketplace=marketplace,
            url=url,
            status="PENDING",
        )
        self.db.add(ms)
        self.db.flush()
        return ms

    def update_marketplace_scrape(
        self,
        scrape_id: UUID,
        status: str,
        product_name: Optional[str] = None,
        product_sku: Optional[str] = None,
        product_brand: Optional[str] = None,
        product_rating: Optional[float] = None,
        product_review_count: Optional[int] = None,
        scraped_at: Optional[datetime] = None,
        raw_payload: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        updates: dict = {"status": status}
        if product_name is not None:
            updates["product_name"] = product_name
        if product_sku is not None:
            updates["product_sku"] = product_sku
        if product_brand is not None:
            updates["product_brand"] = product_brand
        if product_rating is not None:
            updates["product_rating"] = product_rating
        if product_review_count is not None:
            updates["product_review_count"] = product_review_count
        if scraped_at is not None:
            updates["scraped_at"] = scraped_at
        if raw_payload is not None:
            updates["raw_payload"] = raw_payload
        if error_message is not None:
            updates["error_message"] = error_message

        self.db.query(MarketplaceScrape).filter(MarketplaceScrape.id == scrape_id).update(updates)

    def bulk_create_listings(
        self, listings: List[CompetitorListingCreate]
    ) -> None:
        objs = [
            CompetitorListing(
                scrape_id=lst.scrape_id,
                marketplace=lst.marketplace,
                rank=lst.rank,
                seller_name=lst.seller_name,
                seller_score=lst.seller_score,
                seller_review_count=lst.seller_review_count,
                seller_city=lst.seller_city,
                is_authorized=lst.is_authorized,
                price=lst.price,
                original_price=lst.original_price,
                discount_rate=lst.discount_rate,
                currency=lst.currency,
                stock=lst.stock,
                is_in_stock=lst.is_in_stock,
                free_shipping=lst.free_shipping,
                fast_shipping=lst.fast_shipping,
                shipment_days=lst.shipment_days,
                scraped_at=lst.scraped_at,
            )
            for lst in listings
        ]
        self.db.bulk_save_objects(objs)

    def bulk_create_price_history(self, entries: List[PriceHistoryCreate]) -> None:
        objs = [
            PriceHistory(
                product_id=e.product_id,
                marketplace=e.marketplace,
                seller_name=e.seller_name,
                price=e.price,
                recorded_at=e.recorded_at,
            )
            for e in entries
        ]
        self.db.bulk_save_objects(objs)

    def get_listings_by_session(self, session_id: UUID) -> List[dict]:
        rows = (
            self.db.query(CompetitorListing)
            .join(MarketplaceScrape, CompetitorListing.scrape_id == MarketplaceScrape.id)
            .filter(MarketplaceScrape.session_id == session_id)
            .all()
        )
        return [
            {
                "id": str(row.id),
                "scrape_id": str(row.scrape_id),
                "marketplace": row.marketplace,
                "rank": row.rank,
                "seller_name": row.seller_name,
                "seller_score": float(row.seller_score) if row.seller_score is not None else None,
                "seller_review_count": row.seller_review_count,
                "seller_city": row.seller_city,
                "is_authorized": row.is_authorized,
                "price": float(row.price) if row.price is not None else None,
                "original_price": float(row.original_price) if row.original_price is not None else None,
                "discount_rate": float(row.discount_rate) if row.discount_rate is not None else None,
                "currency": row.currency,
                "stock": row.stock,
                "is_in_stock": row.is_in_stock,
                "free_shipping": row.free_shipping,
                "fast_shipping": row.fast_shipping,
                "shipment_days": row.shipment_days,
                "scraped_at": row.scraped_at.isoformat() if row.scraped_at else None,
            }
            for row in rows
        ]
