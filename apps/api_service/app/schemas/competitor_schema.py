from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class CompetitorListingOut(BaseModel):
    id: UUID
    marketplace: str
    rank: Optional[int]
    seller_name: str
    seller_score: Optional[Decimal]
    seller_review_count: Optional[int]
    seller_city: Optional[str]
    is_authorized: bool
    price: Optional[Decimal]
    original_price: Optional[Decimal]
    discount_rate: Optional[Decimal]
    currency: str
    stock: Optional[int]
    is_in_stock: bool
    free_shipping: bool
    fast_shipping: bool
    shipment_days: Optional[int]
    scraped_at: datetime
    class Config:
        from_attributes = True


class CompetitorTierOut(BaseModel):
    id: UUID
    marketplace: str
    seller_name: str
    tier: str
    competitor_strength_score: Optional[Decimal]
    buybox_threat_score: Optional[Decimal]
    price_aggression_score: Optional[Decimal]
    reason_codes: Optional[Any]
    analyzed_at: datetime
    class Config:
        from_attributes = True
