import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CompetitorSeller(Base):
    __tablename__ = "competitor_sellers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    seller_name: Mapped[str] = mapped_column(String(300), nullable=False)
    seller_url: Mapped[str | None] = mapped_column(String)
    seller_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    seller_review_count: Mapped[int | None] = mapped_column(Integer)
    seller_city: Mapped[str | None] = mapped_column(String(200))
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_official_store: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    listings: Mapped[list["CompetitorListing"]] = relationship(back_populates="competitor_seller")
    tiers: Mapped[list["CompetitorTier"]] = relationship(back_populates="competitor_seller")


class CompetitorListing(Base):
    __tablename__ = "competitor_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scrape_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_scrapes.id", ondelete="CASCADE"), nullable=False)
    competitor_seller_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("competitor_sellers.id", ondelete="SET NULL"))
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    rank: Mapped[int | None] = mapped_column(SmallInteger)
    seller_name: Mapped[str] = mapped_column(String(300), nullable=False)
    seller_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    seller_review_count: Mapped[int | None] = mapped_column(Integer)
    seller_city: Mapped[str | None] = mapped_column(String(200))
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    discount_rate: Mapped[float | None] = mapped_column(Numeric(6, 2))
    currency: Mapped[str] = mapped_column(String(10), default="TRY")
    stock: Mapped[int | None] = mapped_column(Integer)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    free_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    fast_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    shipment_days: Mapped[int | None] = mapped_column(SmallInteger)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scrape: Mapped["MarketplaceScrape"] = relationship(back_populates="competitor_listings")
    competitor_seller: Mapped["CompetitorSeller"] = relationship(back_populates="listings")
    tier: Mapped["CompetitorTier"] = relationship(back_populates="competitor_listing", uselist=False)


class CompetitorPriceHistory(Base):
    __tablename__ = "competitor_price_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    competitor_seller_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("competitor_sellers.id", ondelete="SET NULL"))
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    seller_name: Mapped[str] = mapped_column(String(300), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CompetitorTier(Base):
    __tablename__ = "competitor_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    competitor_seller_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("competitor_sellers.id", ondelete="SET NULL"))
    competitor_listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitor_listings.id", ondelete="CASCADE"), nullable=False)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    seller_name: Mapped[str] = mapped_column(String(300), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    competitor_strength_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    buybox_threat_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    price_aggression_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    reason_codes: Mapped[dict | list | None] = mapped_column(JSONB)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product: Mapped["Product"] = relationship(back_populates="competitor_tiers")
    competitor_seller: Mapped["CompetitorSeller"] = relationship(back_populates="tiers")
    competitor_listing: Mapped["CompetitorListing"] = relationship(back_populates="tier")
