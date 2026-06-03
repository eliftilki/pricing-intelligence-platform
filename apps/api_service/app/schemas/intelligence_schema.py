from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class IntelligenceRunRequest(BaseModel):
    product_id: UUID
    marketplaces: List[str] = ["TRENDYOL", "HEPSIBURADA", "AMAZON"]


class ProductSetupRequest(BaseModel):
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    marketplace_urls: Dict[str, str]


class ProductSetupResponse(BaseModel):
    product_id: UUID
    seller_product_ids: Dict[str, UUID]
