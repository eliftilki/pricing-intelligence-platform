import uuid
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.models.base import Base


class CompetitorSeller(Base):
    __tablename__ = "competitor_sellers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marketplace = Column(String, nullable=False)
    seller_name = Column(String, nullable=False)
    seller_url = Column(String)
    seller_score = Column(Numeric(5, 2))
    seller_review_count = Column(Integer)
    seller_city = Column(String)
    is_authorized = Column(Boolean, default=False)
    is_official_store = Column(Boolean, default=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("marketplace", "seller_name"),)


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    status = Column(String, nullable=False, default="STARTED")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketplaceScrape(Base):
    __tablename__ = "marketplace_scrapes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("scrape_sessions.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    marketplace = Column(String, nullable=False)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="STARTED")
    product_name = Column(String)
    product_sku = Column(String)
    product_brand = Column(String)
    product_rating = Column(Numeric(3, 2))
    product_review_count = Column(Integer)
    raw_payload = Column(JSONB)
    error_message = Column(String)
    scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorListing(Base):
    __tablename__ = "competitor_listings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scrape_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_scrapes.id", ondelete="CASCADE"))
    competitor_seller_id = Column(UUID(as_uuid=True), ForeignKey("competitor_sellers.id", ondelete="SET NULL"))
    marketplace = Column(String, nullable=False)
    rank = Column(Integer)
    seller_name = Column(String, nullable=False)
    seller_score = Column(Numeric(5, 2))
    seller_review_count = Column(Integer)
    seller_city = Column(String)
    is_authorized = Column(Boolean, default=False)
    price = Column(Numeric(12, 2))
    original_price = Column(Numeric(12, 2))
    discount_rate = Column(Numeric(6, 2))
    currency = Column(String, default="TRY")
    stock = Column(Integer)
    is_in_stock = Column(Boolean, default=True)
    free_shipping = Column(Boolean, default=False)
    fast_shipping = Column(Boolean, default=False)
    shipment_days = Column(Integer)
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorPriceHistory(Base):
    __tablename__ = "competitor_price_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    competitor_seller_id = Column(UUID(as_uuid=True), ForeignKey("competitor_sellers.id", ondelete="SET NULL"))
    marketplace = Column(String, nullable=False)
    seller_name = Column(String, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorTier(Base):
    __tablename__ = "competitor_tiers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    competitor_seller_id = Column(UUID(as_uuid=True), ForeignKey("competitor_sellers.id", ondelete="SET NULL"))
    competitor_listing_id = Column(UUID(as_uuid=True), ForeignKey("competitor_listings.id", ondelete="CASCADE"))
    marketplace = Column(String, nullable=False)
    seller_name = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    competitor_strength_score = Column(Numeric(5, 2))
    buybox_threat_score = Column(Numeric(5, 2))
    price_aggression_score = Column(Numeric(5, 2))
    reason_codes = Column(JSONB)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
