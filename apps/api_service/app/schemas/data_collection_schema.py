from uuid import UUID
from pydantic import BaseModel
from typing import List


class DataCollectionRunRequest(BaseModel):
    product_id: UUID
    seller_product_id: UUID
    marketplaces: List[str] = ["TRENDYOL", "HEPSIBURADA", "AMAZON"]


class DataCollectionRunResponse(BaseModel):
    job_id: str
    status: str
    message: str