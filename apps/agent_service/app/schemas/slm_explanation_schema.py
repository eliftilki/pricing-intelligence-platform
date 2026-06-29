from pydantic import BaseModel, Field
from typing import Optional


class SLMExplanationRequest(BaseModel):
    product_name: str
    marketplace: str

    current_price: Optional[float] = None
    recommended_price: float
    action: Optional[str] = None

    expected_sales: Optional[float] = None
    unit_profit: Optional[float] = None
    expected_profit: Optional[float] = None
    profit_uplift: Optional[float] = None

    commission_rate: Optional[float] = None
    risk_level: Optional[str] = None
    selected_reason: Optional[str] = None
    reason_codes: list[str] = Field(default_factory=list)

    competitor_min_price: Optional[float] = None
    competitor_avg_price: Optional[float] = None
    tier1_min_price: Optional[float] = None
    analysis_warnings: list[str] = Field(default_factory=list)

    language: str = "tr"


class SLMExplanationResponse(BaseModel):
    explanation: str
    model_name: str
