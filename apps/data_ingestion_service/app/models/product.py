import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    seller_products: Mapped[list["SellerProduct"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    scrape_sessions: Mapped[list["ScrapeSession"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan"
    )


class SellerProduct(Base):
    __tablename__ = "seller_products"
    __table_args__ = (
        UniqueConstraint("product_id", "marketplace", name="uq_seller_product_marketplace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    marketplace_url: Mapped[str] = mapped_column(Text, nullable=False)
    marketplace_sku: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    product: Mapped["Product"] = relationship(back_populates="seller_products")
    marketplace_scrapes: Mapped[list["MarketplaceScrape"]] = relationship(  # noqa: F821
        back_populates="seller_product", cascade="all, delete-orphan"
    )
