import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, Boolean, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CompetitorListing(Base):
    __tablename__ = "competitor_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scrape_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_scrapes.id"), nullable=False
    )
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    rank: Mapped[int | None] = mapped_column(SmallInteger)
    seller_name: Mapped[str] = mapped_column(String(300), nullable=False)
    seller_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    seller_review_count: Mapped[int | None] = mapped_column(Integer)
    seller_city: Mapped[str | None] = mapped_column(String(200))
    is_authorized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    discount_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    stock: Mapped[int | None] = mapped_column(Integer)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    free_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fast_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shipment_days: Mapped[int | None] = mapped_column(SmallInteger)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    scrape: Mapped["MarketplaceScrape"] = relationship(  # noqa: F821
        back_populates="competitor_listings"
    )
