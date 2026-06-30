from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CompetitorIntelligenceRunRequest(BaseModel):
    product_id: UUID
    lookback_hours: int = Field(default=24, ge=1, le=168)


class CompetitorTierResult(BaseModel):
    competitor_listing_id: UUID
    competitor_seller_id: UUID | None = None
    marketplace: str
    seller_name: str
    tier: str
    competitor_strength_score: float
    buybox_threat_score: float
    price_aggression_score: float
    reason_codes: list[str]
    price: float | None = None
    original_price: float | None = None
    currency: str = "TRY"
    rank: int | None = None
    stock: int | None = None
    is_in_stock: bool = True
    free_shipping: bool = False
    fast_shipping: bool = False
    shipment_days: int | None = None
    scraped_at: datetime | None = None


class CompetitorIntelligenceRunResponse(BaseModel):
    product_id: UUID
    status: str
    analyzed_count: int
    inserted_count: int
    message: str
    results: list[CompetitorTierResult]
    pricing_features: dict | None = None
    market_event_features: dict | None = None
