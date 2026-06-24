import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


from app.models.base import Base


class EventCalendar(Base):
    """
    Kampanya/ozel gun takvimi (Black Friday, Anneler Gunu, Ramazan vb.).
    Seed veri olarak doldurulur, Event Calendar Tool buradan okur.
    """

    __tablename__ = "event_calendar"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    affected_categories: Mapped[list] = mapped_column(JSONB, nullable=False)
    base_impact_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MarketEventFeatures(Base):
    """
    Market Intelligence Agent'in 3 tool ciktisini birlestirip urettigi nihai
    sinyal seti. feature_engineering_node bu tabloyu okur (competitor_tiers'i
    okudugu gibi). Ayni product_id icin birden fazla satir olabilir; en son
    (generated_at DESC) gecerli kabul edilir (trend cache TTL bu alana bakar).
    """

    __tablename__ = "market_event_features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(200))

    # Tool 1 - Google Trends
    trend_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    interest_change_7d: Mapped[float | None] = mapped_column(Numeric(6, 4))
    interest_change_30d: Mapped[float | None] = mapped_column(Numeric(6, 4))

    # Tool 2 - Event Calendar
    event_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    event_type: Mapped[str | None] = mapped_column(String(50))
    days_until_event: Mapped[int | None] = mapped_column(SmallInteger)
    base_event_impact: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Tool 3 - Category Analyzer
    category_trend_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    category_demand_change: Mapped[float | None] = mapped_column(Numeric(6, 4))

    # Agent'in kendi hesapladigi nihai sinyaller
    event_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    recommended_demand_multiplier: Mapped[float | None] = mapped_column(Numeric(5, 4))
    market_demand_signal: Mapped[str | None] = mapped_column(String(20))
    reason_codes: Mapped[list | None] = mapped_column(JSONB)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
