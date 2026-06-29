from pydantic import BaseModel, Field
from typing import Optional


class ExplanationRequest(BaseModel):
    product_name: str = Field(..., examples=["Logitech G435"])
    marketplace: str = Field(..., examples=["TRENDYOL"])

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


class ExplanationResponse(BaseModel):
    explanation: str
    model_name: str
