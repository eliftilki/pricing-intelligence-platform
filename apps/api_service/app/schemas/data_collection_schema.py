from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class DataCollectionRunRequest(BaseModel):
    product_id: UUID
    marketplaces: List[str] = Field(
        default_factory=lambda: ["TRENDYOL", "HEPSIBURADA", "AMAZON"]
    )


class DataCollectionRunResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
    scrape_counts: dict[str, int] = Field(default_factory=dict)


class DataCollectionProductCreateRequest(BaseModel):
    company_id: UUID
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    marketplace_urls: dict[str, str]


class DataCollectionProductCreateResponse(BaseModel):
    product_id: UUID
    seller_product_ids: dict[str, UUID]
