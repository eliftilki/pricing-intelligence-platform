from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None


class ProductOut(ProductCreate):
    id: UUID
    created_at: datetime
    class Config:
        from_attributes = True


class SellerProductCreate(BaseModel):
    company_id: UUID
    product_id: UUID
    marketplace: str
    marketplace_url: Optional[str] = None
    marketplace_product_id: Optional[str] = None
    our_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    commission_rate: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")
    packaging_cost: Decimal = Decimal("0")
    stock_quantity: int = 0
    min_margin_rate: Decimal = Decimal("0.15")


class SellerProductOut(SellerProductCreate):
    id: UUID
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


class UpdatePriceRequest(BaseModel):
    new_price: Decimal
    change_source: str = "MANUAL"
    recommendation_id: Optional[UUID] = None


class UpdateStockRequest(BaseModel):
    new_stock: int
    change_source: str = "MANUAL"
