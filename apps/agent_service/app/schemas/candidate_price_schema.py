from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class CandidateStrategy(str, Enum):
    ALL_MARKETPLACE_RANGE = "ALL_MARKETPLACE_RANGE"


class CandidateCompetitor(BaseModel):
    marketplace: str
    seller_name: str
    price: float = Field(..., gt=0)
    tier: str
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
    competitors: list[CandidateCompetitor] = Field(..., min_length=1)


class CandidatePriceGenerateRequest(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None


class CandidatePriceGenerateResponse(BaseModel):
    product_id: UUID
    seller_product_id: UUID | None = None

    selected_strategy: CandidateStrategy
    candidate_prices: list[float] = Field(..., min_length=1)

    min_competitor_price: float
    max_competitor_price: float
    dynamic_step: int
    marketplaces_included: list[str] = Field(..., min_length=1)

    reason: str
    constraints_applied: list[str] = Field(default_factory=list)
    ignored_competitors: list[IgnoredCompetitor] = Field(default_factory=list)
    dense_regions: list[DenseRegion] = Field(default_factory=list)
