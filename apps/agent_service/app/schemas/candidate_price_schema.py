from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class CandidateStrategy(str, Enum):
    AUTO = "AUTO"
    BASIC_COMPETITOR_RANGE = "BASIC_COMPETITOR_RANGE"
    TIER_BASED_COMPETITOR_WINDOW = "TIER_BASED_COMPETITOR_WINDOW"
    ADAPTIVE_DENSE_MARKET_WINDOW = "ADAPTIVE_DENSE_MARKET_WINDOW"


class CandidateCompetitor(BaseModel):
    seller_name: str
    price: float
    tier: str | None = None
    buybox_threat_score: float | None = None


class DenseRegion(BaseModel):
    start_price: float
    end_price: float
    reason: str


class IgnoredCompetitor(BaseModel):
    seller_name: str
    price: float
    reason: str


class CandidatePriceContext(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None

    current_price: float

    min_competitor_price: float | None = None
    avg_competitor_price: float | None = None
    max_competitor_price: float | None = None

    competitors: list[CandidateCompetitor] = Field(default_factory=list)

    price_step: int = 250
    base_price_step: int = 250
    dense_price_step: int = 50


class CandidatePriceGenerateRequest(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None
    strategy: CandidateStrategy = CandidateStrategy.AUTO
    persist: bool = Field(
        default=False,
        description="Candidate prices are kept in the response/state and are not persisted.",
    )

    price_step: int = 250
    base_price_step: int = 250
    dense_price_step: int = 50


class CandidatePriceGenerateResponse(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None

    selected_strategy: CandidateStrategy
    candidate_prices: list[float]

    reason: str
    constraints_applied: list[str] = Field(default_factory=list)
    ignored_competitors: list[IgnoredCompetitor] = Field(default_factory=list)
    dense_regions: list[DenseRegion] = Field(default_factory=list)
