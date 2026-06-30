from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.competitor_schema import CompetitorTierResult
from app.schemas.optimization_schema import DemandPredictionItem


class PricingIntelligenceRunRequest(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None
    seller_product_ids: dict[str, UUID] = Field(default_factory=dict)
    lookback_hours: int = Field(default=12, ge=1, le=168)
    ingestion_marketplaces: list[str] = Field(
        default_factory=lambda: ["TRENDYOL", "HEPSIBURADA", "AMAZON"],
        min_length=1,
    )
    ingestion_query: str | None = Field(default=None, min_length=2)
    ingestion_company_id: UUID | None = None
    run_candidate_prices: bool = True
    run_optimization: bool = False
    persist_optimization: bool = False
    # GECICI: Frontend hazir olunca satıcıdan gelecek. Simdilik opsiyonel.
    sales_7d_avg: float | None = Field(default=None, ge=0)
    demand_predictions: list[DemandPredictionItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ingestion_options(self):
        supported_marketplaces = {"TRENDYOL", "HEPSIBURADA", "AMAZON"}
        normalized_marketplaces = list(
            dict.fromkeys(item.strip().upper() for item in self.ingestion_marketplaces)
        )
        unsupported = set(normalized_marketplaces) - supported_marketplaces
        if unsupported:
            raise ValueError(
                "Unsupported ingestion marketplaces: "
                + ", ".join(sorted(unsupported))
            )
        self.ingestion_marketplaces = normalized_marketplaces

        normalized_seller_product_ids = {
            marketplace.strip().upper(): seller_product_id
            for marketplace, seller_product_id in self.seller_product_ids.items()
        }
        unsupported_seller_marketplaces = (
            set(normalized_seller_product_ids) - supported_marketplaces
        )
        if unsupported_seller_marketplaces:
            raise ValueError(
                "Unsupported seller product marketplaces: "
                + ", ".join(sorted(unsupported_seller_marketplaces))
            )
        self.seller_product_ids = normalized_seller_product_ids

        if self.seller_product_id is None and normalized_seller_product_ids:
            primary_marketplace = next(
                (
                    marketplace
                    for marketplace in normalized_marketplaces
                    if marketplace in normalized_seller_product_ids
                ),
                next(iter(normalized_seller_product_ids)),
            )
            self.seller_product_id = normalized_seller_product_ids[primary_marketplace]

        has_query = self.ingestion_query is not None
        has_company = self.ingestion_company_id is not None
        if has_query != has_company:
            raise ValueError(
                "ingestion_query and ingestion_company_id must be provided together."
            )

        return self


class PricingIntelligenceRunResponse(BaseModel):
    product_id: UUID
    status: str
    error_code: str | None = None
    failed_stage: str | None = None
    analyzed_count: int = 0
    inserted_count: int = 0
    message: str
    results: list[CompetitorTierResult] = Field(default_factory=list)
    ingestion_job_id: UUID | None = None
    ingestion_result: dict | None = None
    warnings: list[str] = Field(default_factory=list)
    candidate_price_result: dict | None = None
    candidate_prices: list[float] | None = None
    selected_candidate_strategy: str | None = None
    optimization_result: dict | None = None
    marketplace_results: list[dict] | None = None
    marketplace_recommendations: list[dict] | None = None
    risk_control_result: dict | None = None
    recommendation: dict | None = None
    recommendation_persistence: dict | None = None
    slm_explanation: dict | None = None
    pipeline_summary: dict | None = None
    errors: list[str] = Field(default_factory=list)
