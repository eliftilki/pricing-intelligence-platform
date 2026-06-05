from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class CompetitorIntelligenceRunRequest(BaseModel):
    session_id: UUID
    product_id: UUID


class ScoredCompetitorSchema(BaseModel):
    id: Optional[str] = None
    marketplace: str
    rank: Optional[int] = None
    seller_name: str
    seller_score: Optional[float] = None
    seller_review_count: Optional[int] = None
    seller_city: Optional[str] = None
    is_authorized: bool
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "TRY"
    stock: Optional[int] = None
    is_in_stock: bool
    free_shipping: bool
    fast_shipping: bool
    shipment_days: Optional[int] = None
    tier: int
    threat_score: float
    price_score: float
    seller_quality_score: float
    availability_score: float
    shipping_score: float
    price_gap_pct: Optional[float] = None
    is_buybox_winner: bool = False


class PriceRecommendationSchema(BaseModel):
    suggested_price: Optional[float]
    strategy: str
    confidence: float
    rationale: str


class PriceRangeSchema(BaseModel):
    min: Optional[float]
    max: Optional[float]
    median: Optional[float]
    mean: Optional[float]


class CompetitorIntelligenceRunResponse(BaseModel):
    session_id: UUID
    product_id: UUID
    total_competitors: int
    price_range: PriceRangeSchema
    buybox_prices: dict[str, Optional[float]]
    recommendation: PriceRecommendationSchema
    competitors: List[ScoredCompetitorSchema]
