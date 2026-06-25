from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Marketplace(str, Enum):
    TRENDYOL = "TRENDYOL"
    HEPSIBURADA = "HEPSIBURADA"
    AMAZON = "AMAZON"


class RejectionReason(str, Enum):
    NEGATIVE_OR_ZERO_PRICE = "NEGATIVE_OR_ZERO_PRICE"
    NEGATIVE_EXPECTED_SALES = "NEGATIVE_EXPECTED_SALES"
    MIN_MARGIN_NOT_MET = "MIN_MARGIN_NOT_MET"
    PRICE_INCREASE_TOO_HIGH = "PRICE_INCREASE_TOO_HIGH"
    PRICE_DECREASE_TOO_HIGH = "PRICE_DECREASE_TOO_HIGH"
    INVALID_UNIT_PROFIT = "INVALID_UNIT_PROFIT"
    MISSING_COMMISSION_RULE = "MISSING_COMMISSION_RULE"


class OptimizationConstraintCode(str, Enum):
    MIN_MARGIN_APPLIED = "MIN_MARGIN_APPLIED"
    MAX_PRICE_INCREASE_APPLIED = "MAX_PRICE_INCREASE_APPLIED"
    MAX_PRICE_DECREASE_APPLIED = "MAX_PRICE_DECREASE_APPLIED"
    MARKETPLACE_COMMISSION_APPLIED = "MARKETPLACE_COMMISSION_APPLIED"
    BEST_EXPECTED_PROFIT_SELECTED = "BEST_EXPECTED_PROFIT_SELECTED"


class DemandPredictionItem(BaseModel):
    price: Decimal = Field(..., gt=0)
    expected_sales: Decimal = Field(..., ge=0)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketplaceOptimizationInput(BaseModel):
    marketplace: Marketplace
    current_price: Decimal | None = Field(default=None, gt=0)
    commission_rate: Decimal | None = Field(default=None, ge=0, le=1)
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0)
    packaging_cost: Decimal = Field(default=Decimal("0"), ge=0)
    min_margin_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    max_price_increase_rate: Decimal | None = Field(default=Decimal("0.25"), ge=0, le=10)
    max_price_decrease_rate: Decimal | None = Field(default=Decimal("0.20"), ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("marketplace", mode="before")
    @classmethod
    def normalize_marketplace(cls, value):
        if isinstance(value, str):
            return value.upper()
        return value


class OptimizationRequest(BaseModel):
    seller_product_id: UUID
    product_id: UUID | None = None
    cost_price: Decimal = Field(..., gt=0)
    demand_predictions: list[DemandPredictionItem] = Field(..., min_length=1)
    marketplaces: list[MarketplaceOptimizationInput] = Field(..., min_length=1)
    persist: bool = True
    run_id: UUID | None = None

    @field_validator("demand_predictions")
    @classmethod
    def unique_prices(cls, values: list[DemandPredictionItem]) -> list[DemandPredictionItem]:
        seen_prices: set[str] = set()

        for item in values:
            price_key = str(item.price)
            if price_key in seen_prices:
                raise ValueError(f"Duplicate demand prediction price: {item.price}")
            seen_prices.add(price_key)

        return values


class CandidateOptimizationEvaluation(BaseModel):
    price: Decimal
    expected_sales: Decimal
    commission_amount: Decimal
    unit_profit: Decimal
    unit_margin_rate: Decimal
    expected_profit: Decimal
    is_valid: bool
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    score: Decimal
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketplaceOptimizationResult(BaseModel):
    marketplace: Marketplace
    recommended_price: Decimal | None = None
    current_price: Decimal | None = None
    commission_rate: Decimal | None = None
    expected_sales: Decimal | None = None
    unit_profit: Decimal | None = None
    unit_margin_rate: Decimal | None = None
    expected_profit: Decimal | None = None
    profit_uplift_vs_current: Decimal | None = None
    constraints_applied: list[OptimizationConstraintCode] = Field(default_factory=list)
    selected_reason: str | None = None
    evaluated_candidates: list[CandidateOptimizationEvaluation] = Field(default_factory=list)
    rejected_candidates: list[CandidateOptimizationEvaluation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationResponse(BaseModel):
    seller_product_id: UUID
    product_id: UUID | None = None
    run_id: UUID | None = None
    generated_at: datetime
    marketplace_results: list[MarketplaceOptimizationResult]
    summary: dict[str, Any] = Field(default_factory=dict)


class OptimizationRecordCreate(BaseModel):
    seller_product_id: UUID
    product_id: UUID | None = None
    run_id: UUID | None = None
    marketplace: Marketplace
    recommended_price: Decimal | None = None
    current_price: Decimal | None = None
    cost_price: Decimal
    commission_rate: Decimal | None = None
    shipping_cost: Decimal
    packaging_cost: Decimal
    min_margin_rate: Decimal
    expected_sales: Decimal | None = None
    unit_profit: Decimal | None = None
    unit_margin_rate: Decimal | None = None
    expected_profit: Decimal | None = None
    profit_uplift_vs_current: Decimal | None = None
    selected_reason: str | None = None
    constraints_applied: list[str] = Field(default_factory=list)
    evaluated_candidates: list[dict[str, Any]] = Field(default_factory=list)
    rejected_candidates: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationFromDbRequest(BaseModel):
    demand_predictions: list[DemandPredictionItem] = Field(..., min_length=1)
    cost_price: Decimal | None = Field(default=None, gt=0)
    product_id: UUID | None = None
    run_id: UUID | None = None
    persist: bool = True
