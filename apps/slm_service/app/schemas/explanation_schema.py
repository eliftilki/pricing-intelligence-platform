from pydantic import BaseModel, Field
from typing import Optional


class ExplanationRequest(BaseModel):
    product_name: str = Field(..., examples=["Logitech G435"])
    marketplace: str = Field(..., examples=["TRENDYOL"])

    current_price: float
    recommended_price: float

    expected_sales: Optional[float] = None
    unit_profit: Optional[float] = None
    expected_profit: Optional[float] = None

    commission_rate: Optional[float] = None
    risk_level: Optional[str] = None
    selected_reason: Optional[str] = None

    competitor_min_price: Optional[float] = None
    competitor_avg_price: Optional[float] = None
    tier1_min_price: Optional[float] = None

    language: str = "tr"


class ExplanationResponse(BaseModel):
    explanation: str
    model_name: str