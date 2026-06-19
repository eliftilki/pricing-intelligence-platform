from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.competitor import CompetitorListing, CompetitorSeller
from app.models.price_history import CompetitorPriceHistory
from app.models.product import Product, SellerProduct
from app.models.scrape import MarketplaceScrape, ScrapeSession
from app.normalizers.competitor_normalizer import (
    CompetitorListingCreate,
    PriceHistoryCreate,
)


class CompetitorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_product(
        self,
        name: str,
        brand: Optional[str],
        category: Optional[str],
        model: Optional[str] = None,
        barcode: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Product:
        product = Product(
            name=name,
            brand=brand,
            model=model,
            category=category,
            barcode=barcode,
            description=description,
        )
        self.db.add(product)
        self.db.flush()
        return product

    def create_seller_product(
        self,
        company_id: UUID,
        product_id: UUID,
        marketplace: str,
        url: Optional[str],
        marketplace_product_id: Optional[str] = None,
        our_price: Optional[float] = None,
        cost_price: Optional[float] = None,
        stock_quantity: int = 0,
    ) -> SellerProduct:
        seller_product = SellerProduct(
            company_id=company_id,
            product_id=product_id,
            marketplace=marketplace.upper(),
            marketplace_url=url,
            marketplace_product_id=marketplace_product_id,
            our_price=our_price,
            cost_price=cost_price,
            stock_quantity=stock_quantity,
        )
        self.db.add(seller_product)
        self.db.flush()
        return seller_product

    def get_or_create_seller_product(
        self,
        company_id: UUID,
        product_id: UUID,
        marketplace: str,
        url: str,
    ) -> SellerProduct:
        marketplace = marketplace.upper()
        existing = (
            self.db.query(SellerProduct)
            .filter(
                SellerProduct.company_id == company_id,
                SellerProduct.product_id == product_id,
                SellerProduct.marketplace == marketplace,
            )
            .first()
        )
        if existing:
            if existing.marketplace_url != url:
                existing.marketplace_url = url
                self.db.flush()
            return existing
        return self.create_seller_product(
            company_id=company_id,
            product_id=product_id,
            marketplace=marketplace,
            url=url,
        )

    def get_seller_products_for_marketplaces(
        self,
        product_id: UUID,
        marketplaces: List[str],
    ) -> List[SellerProduct]:
        normalized_marketplaces = [m.upper() for m in marketplaces]

        return (
            self.db.query(SellerProduct)
            .filter(
                SellerProduct.product_id == product_id,
                SellerProduct.marketplace.in_(normalized_marketplaces),
                SellerProduct.is_active.is_(True),
            )
            .all()
        )

    def create_session(self, product_id: UUID) -> ScrapeSession:
        session = ScrapeSession(
            product_id=product_id,
            status="STARTED",
        )
        self.db.add(session)
        self.db.flush()
        return session

    def update_session_status(
        self,
        session_id: UUID,
        status: str,
        completed_at: Optional[datetime] = None,
    ) -> None:
        self.db.query(ScrapeSession).filter(
            ScrapeSession.id == session_id
        ).update(
            {
                "status": status,
                "completed_at": completed_at or datetime.now(timezone.utc),
            }
        )

    def create_marketplace_scrape(
        self,
        session_id: UUID,
        seller_product_id: UUID,
        product_id: UUID,
        marketplace: str,
        url: str,
    ) -> MarketplaceScrape:
        marketplace_scrape = MarketplaceScrape(
            session_id=session_id,
            seller_product_id=seller_product_id,
            product_id=product_id,
            marketplace=marketplace.upper(),
            url=url,
            status="STARTED",
        )
        self.db.add(marketplace_scrape)
        self.db.flush()
        return marketplace_scrape

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
        updates: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }

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

        self.db.query(MarketplaceScrape).filter(
            MarketplaceScrape.id == scrape_id
        ).update(updates)

    def update_seller_product_marketplace_product_id_if_empty(
        self,
        seller_product_id: UUID,
        marketplace_product_id: Optional[str],
    ) -> None:
        if not marketplace_product_id:
            return

        seller_product = (
            self.db.query(SellerProduct)
            .filter(SellerProduct.id == seller_product_id)
            .first()
        )

        if seller_product and not seller_product.marketplace_product_id:
            seller_product.marketplace_product_id = marketplace_product_id
            seller_product.updated_at = datetime.now(timezone.utc)

    def upsert_competitor_seller(
        self,
        marketplace: str,
        seller_name: str,
        seller_score: Optional[float] = None,
        seller_review_count: Optional[int] = None,
        seller_city: Optional[str] = None,
        is_authorized: bool = False,
        seller_url: Optional[str] = None,
    ) -> CompetitorSeller:
        marketplace = marketplace.upper()

        seller = (
            self.db.query(CompetitorSeller)
            .filter(
                CompetitorSeller.marketplace == marketplace,
                CompetitorSeller.seller_name == seller_name,
            )
            .first()
        )

        if seller:
            seller.seller_score = seller_score
            seller.seller_review_count = seller_review_count
            seller.seller_city = seller_city
            seller.is_authorized = is_authorized
            seller.seller_url = seller_url or seller.seller_url
            seller.last_seen_at = datetime.now(timezone.utc)
            self.db.flush()
            return seller

        seller = CompetitorSeller(
            marketplace=marketplace,
            seller_name=seller_name,
            seller_url=seller_url,
            seller_score=seller_score,
            seller_review_count=seller_review_count,
            seller_city=seller_city,
            is_authorized=is_authorized,
            last_seen_at=datetime.now(timezone.utc),
        )

        self.db.add(seller)
        self.db.flush()
        return seller

    def bulk_create_listings(
        self,
        listings: List[CompetitorListingCreate],
    ) -> None:
        for listing in listings:
            competitor_seller = self.upsert_competitor_seller(
                marketplace=listing.marketplace,
                seller_name=listing.seller_name,
                seller_score=listing.seller_score,
                seller_review_count=listing.seller_review_count,
                seller_city=listing.seller_city,
                is_authorized=listing.is_authorized,
            )

            obj = CompetitorListing(
                scrape_id=listing.scrape_id,
                competitor_seller_id=competitor_seller.id,
                marketplace=listing.marketplace.upper(),
                rank=listing.rank,
                seller_name=listing.seller_name,
                seller_score=listing.seller_score,
                seller_review_count=listing.seller_review_count,
                seller_city=listing.seller_city,
                is_authorized=listing.is_authorized,
                price=listing.price,
                original_price=listing.original_price,
                discount_rate=listing.discount_rate,
                currency=listing.currency,
                stock=listing.stock,
                is_in_stock=listing.is_in_stock,
                free_shipping=listing.free_shipping,
                fast_shipping=listing.fast_shipping,
                shipment_days=listing.shipment_days,
                scraped_at=listing.scraped_at,
            )

            self.db.add(obj)

        self.db.flush()

    def bulk_create_price_history(
        self,
        entries: List[PriceHistoryCreate],
    ) -> None:
        for entry in entries:
            competitor_seller = (
                self.db.query(CompetitorSeller)
                .filter(
                    CompetitorSeller.marketplace == entry.marketplace.upper(),
                    CompetitorSeller.seller_name == entry.seller_name,
                )
                .first()
            )

            obj = CompetitorPriceHistory(
                product_id=entry.product_id,
                competitor_seller_id=competitor_seller.id if competitor_seller else None,
                marketplace=entry.marketplace.upper(),
                seller_name=entry.seller_name,
                price=entry.price,
                recorded_at=entry.recorded_at,
            )

            self.db.add(obj)

        self.db.flush()

    def get_listings_by_session(self, session_id: UUID) -> List[dict]:
        rows = (
            self.db.query(CompetitorListing)
            .join(MarketplaceScrape, CompetitorListing.scrape_id == MarketplaceScrape.id)
            .filter(MarketplaceScrape.session_id == session_id)
            .order_by(CompetitorListing.marketplace, CompetitorListing.rank.asc())
            .all()
        )

        return [
            {
                "id": str(row.id),
                "scrape_id": str(row.scrape_id),
                "competitor_seller_id": (
                    str(row.competitor_seller_id)
                    if row.competitor_seller_id
                    else None
                ),
                "marketplace": row.marketplace,
                "rank": row.rank,
                "seller_name": row.seller_name,
                "seller_score": float(row.seller_score)
                if row.seller_score is not None
                else None,
                "seller_review_count": row.seller_review_count,
                "seller_city": row.seller_city,
                "is_authorized": row.is_authorized,
                "price": float(row.price) if row.price is not None else None,
                "original_price": float(row.original_price)
                if row.original_price is not None
                else None,
                "discount_rate": float(row.discount_rate)
                if row.discount_rate is not None
                else None,
                "currency": row.currency,
                "stock": row.stock,
                "is_in_stock": row.is_in_stock,
                "free_shipping": row.free_shipping,
                "fast_shipping": row.fast_shipping,
                "shipment_days": row.shipment_days,
                "scraped_at": row.scraped_at.isoformat()
                if row.scraped_at
                else None,
            }
            for row in rows
        ]