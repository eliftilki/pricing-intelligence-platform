from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskReasonCode(str, Enum):
    NO_VALID_OPTIMIZATION_RESULT = "NO_VALID_OPTIMIZATION_RESULT"
    SELLING_BELOW_COST = "SELLING_BELOW_COST"
    MIN_MARGIN_BREACHED = "MIN_MARGIN_BREACHED"
    PRICE_CHANGE_TOO_AGGRESSIVE = "PRICE_CHANGE_TOO_AGGRESSIVE"
    LOW_STOCK_PRICE_DECREASE = "LOW_STOCK_PRICE_DECREASE"
    NOISE_DRIVEN_UNDERCUT = "NOISE_DRIVEN_UNDERCUT"
    LOW_MODEL_CONFIDENCE = "LOW_MODEL_CONFIDENCE"


class RiskCheckSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


class RiskCheckResult(BaseModel):
    rule_code: RiskReasonCode
    passed: bool
    severity: RiskCheckSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class MarketplaceRiskInput(BaseModel):
    marketplace: str
    recommended_price: Decimal | None = None
    current_price: Decimal | None = None
    unit_profit: Decimal | None = None
    unit_margin_rate: Decimal | None = None
    expected_sales: Decimal | None = None
    commission_rate: Decimal | None = None
    selected_reason: str | None = None


class RiskContextInput(BaseModel):
    seller_product_id: UUID
    product_id: UUID | None = None
    cost_price: Decimal
    min_margin_rate: Decimal = Field(default=Decimal("0.15"), ge=0, le=1)
    stock_quantity: int | None = None
    min_competitor_price: Decimal | None = None
    avg_competitor_price: Decimal | None = None
    market_pressure_score: float | None = None
    demand_prediction_meta: dict[str, Any] = Field(default_factory=dict)


class RiskControlRequest(BaseModel):
    context: RiskContextInput
    marketplaces: list[MarketplaceRiskInput] = Field(..., min_length=1)
    optimization_summary_status: str | None = None


class MarketplaceRiskAssessment(BaseModel):
    marketplace: str
    recommended_price: Decimal | None = None
    current_price: Decimal | None = None
    risk_level: RiskLevel
    allowed: bool
    reason_codes: list[RiskReasonCode] = Field(default_factory=list)
    blocking_reasons: list[RiskReasonCode] = Field(default_factory=list)
    checks: list[RiskCheckResult] = Field(default_factory=list)


class RiskControlResponse(BaseModel):
    seller_product_id: UUID
    product_id: UUID | None = None
    evaluated_at: datetime
    assessments: list[MarketplaceRiskAssessment] = Field(default_factory=list)
    overall_risk_level: RiskLevel
    overall_allowed: bool
    best_marketplace: str | None = None