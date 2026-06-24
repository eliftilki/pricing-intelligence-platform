import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200))
    model: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(200))
    barcode: Mapped[str | None] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    seller_products: Mapped[list["SellerProduct"]] = relationship(back_populates="product")
    scrape_sessions: Mapped[list["ScrapeSession"]] = relationship(back_populates="product")


class SellerProduct(Base):
    __tablename__ = "seller_products"

    __table_args__ = (
        UniqueConstraint("company_id", "product_id", "marketplace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    marketplace_url: Mapped[str | None] = mapped_column(Text)
    marketplace_product_id: Mapped[str | None] = mapped_column(String(200))

    our_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    shipping_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), default=0)
    packaging_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), default=0)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_margin_rate: Mapped[float | None] = mapped_column(Numeric(5, 4), default=0.15)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    product: Mapped["Product"] = relationship(back_populates="seller_products")
    marketplace_scrapes: Mapped[list["MarketplaceScrape"]] = relationship(back_populates="seller_product")
