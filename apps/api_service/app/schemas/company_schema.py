from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    marketplace_seller_name: Optional[str] = None
    tax_number: Optional[str] = None
    website_url: Optional[str] = None


class CompanyOut(CompanyCreate):
    id: UUID
    created_at: datetime
    class Config:
        from_attributes = True
