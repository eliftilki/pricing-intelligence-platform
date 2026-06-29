from typing import TypedDict
from uuid import UUID


class CompetitorGraphState(TypedDict, total=False):
    product_id: UUID
    seller_product_id: UUID | None
    company_id: UUID | None

    lookback_hours: int
    refresh_market_data: bool
    ingestion_marketplaces: list[str]
    ingestion_query: str | None
    ingestion_company_id: UUID | None
    ingestion_job_id: UUID
    ingestion_result: dict
    run_candidate_prices: bool
    run_optimization: bool
    persist_optimization: bool

    status: str
    error_code: str
    analyzed_count: int
    inserted_count: int
    message: str
    results: list[dict]

    price_step: int
    base_price_step: int
    dense_price_step: int

    candidate_price_result: dict
    candidate_prices: list[float]
    selected_candidate_strategy: str

    pricing_features: dict
    market_event_features: dict
    product_name: str | None

    demand_predictions: list[dict]
    optimization_result: dict
    marketplace_recommendations: list[dict]

    recommendation: dict
    slm_explanation: dict | None
    errors: list[str]
    warnings: list[str]
