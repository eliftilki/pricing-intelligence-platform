from pydantic import BaseModel
from typing import Optional


class SLMExplanationRequest(BaseModel):
    product_name: str
    marketplace: str

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


class SLMExplanationResponse(BaseModel):
    explanation: str
    model_name: str