from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class RunAnalysisRequest(BaseModel):
    company_id: UUID
    product_id: UUID
    seller_product_id: UUID
    trigger_type: str = "manual"
    question: Optional[str] = None


class RunAnalysisResponse(BaseModel):
    run_id: str
    status: str
    message: str
