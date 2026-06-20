import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="STARTED")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    marketplace_scrapes: Mapped[list["MarketplaceScrape"]] = relationship(back_populates="session")


class MarketplaceScrape(Base):
    __tablename__ = "marketplace_scrapes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scrape_sessions.id", ondelete="CASCADE"), nullable=False)
    seller_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="STARTED")
    product_name: Mapped[str | None] = mapped_column(String(500))
    product_sku: Mapped[str | None] = mapped_column(String(200))
    product_brand: Mapped[str | None] = mapped_column(String(200))
    product_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    product_review_count: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped["ScrapeSession"] = relationship(back_populates="marketplace_scrapes")
    product: Mapped["Product"] = relationship(back_populates="marketplace_scrapes")
    seller_product: Mapped["SellerProduct"] = relationship(back_populates="marketplace_scrapes")
    competitor_listings: Mapped[list["CompetitorListing"]] = relationship(back_populates="scrape")
