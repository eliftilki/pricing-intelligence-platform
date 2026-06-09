from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class PriceRecommendationOut(BaseModel):
    id: UUID
    company_id: UUID
    product_id: UUID
    seller_product_id: UUID
    current_price: Decimal
    recommended_price: Decimal
    action: str
    expected_sales_quantity: Optional[Decimal]
    expected_profit: Optional[Decimal]
    profit_uplift: Optional[Decimal]
    confidence_score: Optional[Decimal]
    risk_level: Optional[str]
    reason_codes: Optional[Any]
    explanation: Optional[str]
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


class RecommendationDecisionRequest(BaseModel):
    decision_note: Optional[str] = None
