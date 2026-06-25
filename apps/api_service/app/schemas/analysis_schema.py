from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RunAnalysisRequest(BaseModel):
    product_id: UUID
    company_id: Optional[UUID] = None
    query: Optional[str] = None
    marketplaces: List[str] = Field(
        default_factory=lambda: ["TRENDYOL", "HEPSIBURADA", "AMAZON"]
    )


class RunProductAnalysisRequest(RunAnalysisRequest):
    company_id: UUID
    query: str


class PriceRangeOut(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    median: Optional[float] = None
    mean: Optional[float] = None


class RecommendationOut(BaseModel):
    suggested_price: Optional[float] = None
    strategy: str
    confidence: float
    rationale: str


class RunAnalysisResponse(BaseModel):
    session_id: UUID
    product_id: UUID
    ingestion_status: str
    ingestion_message: Optional[str] = None
    scrape_counts: dict[str, int] = Field(default_factory=dict)
    total_competitors: int
    price_range: PriceRangeOut
    recommendation: RecommendationOut
    competitors: list = Field(default_factory=list)
