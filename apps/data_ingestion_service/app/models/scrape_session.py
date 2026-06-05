import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship(back_populates="scrape_sessions")  # noqa: F821
    marketplace_scrapes: Mapped[list["MarketplaceScrape"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class MarketplaceScrape(Base):
    __tablename__ = "marketplace_scrapes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scrape_sessions.id"), nullable=False
    )
    seller_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_products.id"), nullable=False
    )
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    product_name: Mapped[str | None] = mapped_column(String(500))
    product_sku: Mapped[str | None] = mapped_column(String(200))
    product_brand: Mapped[str | None] = mapped_column(String(200))
    product_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    product_review_count: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    session: Mapped["ScrapeSession"] = relationship(back_populates="marketplace_scrapes")
    seller_product: Mapped["SellerProduct"] = relationship(  # noqa: F821
        back_populates="marketplace_scrapes"
    )
    competitor_listings: Mapped[list["CompetitorListing"]] = relationship(  # noqa: F821
        back_populates="scrape", cascade="all, delete-orphan"
    )
