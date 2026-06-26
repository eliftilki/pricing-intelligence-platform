from pydantic import BaseModel, Field

class DemandFeatureRow(BaseModel):
    product_id: int
    category: str
    month: int
    is_weekend: int
    is_salary_week: int
    candidate_price: float
    min_competitor_price: float
    avg_competitor_price: float
    market_avg_price: float
    market_price_trend_7d: float
    market_volatility_7d: float
    competitor_count: int
    tier1_competitor_count: int
    price_gap_to_min: float
    price_gap_to_avg: float
    price_gap_to_market_avg: float
    price_rank: int
    market_pressure_score: float
    competitor_aggression_score: float
    trend_score: float
    interest_change_7d: float
    interest_change_30d: float
    event_detected: float
    event_type_id: float
    days_until_event: float
    event_confidence: float
    category_demand_change: float
    recommended_demand_multiplier: float
    sales_7d_avg: float
    sales_30d_avg: float
    stock_quantity: int
    stock_bucket: str


class DemandPredictionRequest(BaseModel):
    items: list[DemandFeatureRow] = Field(..., min_length=1)


class DemandPredictionResult(BaseModel):
    candidate_price: float
    expected_sales: float


class DemandPredictionResponse(BaseModel):
    model_name: str
    n_fold_models: int
    ensemble_strategy: str = "mean"
    predictions: list[DemandPredictionResult]
