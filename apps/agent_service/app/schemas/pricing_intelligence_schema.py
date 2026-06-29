from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.competitor_schema import CompetitorTierResult
from app.schemas.optimization_schema import DemandPredictionItem


class PricingIntelligenceRunRequest(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None
    lookback_hours: int = Field(default=24, ge=1, le=168)
    run_candidate_prices: bool = True
    run_optimization: bool = False
    persist_candidate_prices: bool = Field(
        default=False,
        description="Candidate prices are kept in graph state and are not persisted.",
    )
    persist_optimization: bool = False
    price_step: int = 250
    base_price_step: int = 250
    dense_price_step: int = 50
    demand_predictions: list[DemandPredictionItem] = Field(default_factory=list)


class PricingIntelligenceRunResponse(BaseModel):
    product_id: UUID
    status: str
    error_code: str | None = None
    analyzed_count: int = 0
    inserted_count: int = 0
    message: str
    results: list[CompetitorTierResult] = Field(default_factory=list)
    candidate_price_result: dict | None = None
    candidate_prices: list[float] | None = None
    selected_candidate_strategy: str | None = None
    optimization_result: dict | None = None
    marketplace_recommendations: list[dict] | None = None
    slm_explanation: dict | None = None
    errors: list[str] = Field(default_factory=list)
