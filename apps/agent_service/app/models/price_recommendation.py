import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PriceRecommendation(Base):
    """
    api_service/app/models/pricing.py:PriceRecommendation ile ayni tabloyu
    (price_recommendations) hedefler - iki servis ayni Postgres DB'yi
    paylasiyor (DATABASE_URL), Product/SellerProduct'ta oldugu gibi model
    her serviste kendi dosyasinda ayrica tanimli.

    Bu model sadece persist_recommendation_node'dan INSERT icin kullanilir;
    status/approve/reject/apply akisi api_service'in sorumlulugunda.
    """

    __tablename__ = "price_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE")
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    seller_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE")
    )
    pricing_feature_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pricing_features.id", ondelete="SET NULL")
    )

    current_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    recommended_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)

    expected_sales_quantity: Mapped[float | None] = mapped_column(Numeric(12, 2))
    expected_profit: Mapped[float | None] = mapped_column(Numeric(12, 2))
    profit_uplift: Mapped[float | None] = mapped_column(Numeric(12, 2))
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    risk_level: Mapped[str | None] = mapped_column(String)
    reason_codes: Mapped[list | None] = mapped_column(JSONB)
    explanation: Mapped[str | None] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
