import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PricingOptimizationResult(Base):
    __tablename__ = "pricing_optimization_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    seller_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seller_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    marketplace: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    recommended_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    commission_rate: Mapped[float | None] = mapped_column(Numeric(8, 6))
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    packaging_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    min_margin_rate: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False, default=0)

    expected_sales: Mapped[float | None] = mapped_column(Numeric(12, 4))
    unit_profit: Mapped[float | None] = mapped_column(Numeric(12, 2))
    unit_margin_rate: Mapped[float | None] = mapped_column(Numeric(8, 6))
    expected_profit: Mapped[float | None] = mapped_column(Numeric(14, 2))
    profit_uplift_vs_current: Mapped[float | None] = mapped_column(Numeric(12, 6))

    selected_reason: Mapped[str | None] = mapped_column(Text)
    constraints_applied: Mapped[list | None] = mapped_column(JSONB)
    evaluated_candidates: Mapped[list | None] = mapped_column(JSONB)
    rejected_candidates: Mapped[list | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


Index(
    "idx_pricing_optimization_results_seller_marketplace_created",
    PricingOptimizationResult.seller_product_id,
    PricingOptimizationResult.marketplace,
    PricingOptimizationResult.created_at.desc(),
)
