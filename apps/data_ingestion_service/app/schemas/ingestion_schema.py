from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class IngestionRunRequest(BaseModel):
    product_id: UUID
    marketplaces: List[str] = ["TRENDYOL", "HEPSIBURADA", "AMAZON"]


class ProductCreateRequest(BaseModel):
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    marketplace_urls: dict[str, str]


class ProductCreateResponse(BaseModel):
    product_id: UUID
    seller_product_ids: dict[str, UUID]


class IngestionRunResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
    scrape_counts: dict[str, int] = {}
