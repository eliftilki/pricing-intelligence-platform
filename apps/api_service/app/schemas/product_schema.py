from pydantic import BaseModel
from typing import Literal, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

# event_calendar seed data (agent_service) ile birebir ayni 12 kategori.
# Serbest metin kategori girisi (eski "Mouse", "headset", "Kulaklık" gibi
# tutarsizliklara yol acmisti) event matching'i kirdigi icin kapatildi.
ProductCategory = Literal[
    "Elektronik", "Moda", "Ev", "Gıda", "Kırtasiye", "Spor",
    "Takı", "Güzellik", "Hediye", "Aletler", "Oyuncak", "Kozmetik",
]


class ProductCreate(BaseModel):
    name: str
    normalized_key: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[ProductCategory] = None
    category_id: Optional[UUID] = None
    color: Optional[str] = None
    connection_type: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[ProductCategory] = None
    category_id: Optional[UUID] = None
    color: Optional[str] = None
    connection_type: Optional[str] = None
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
    display_name: Optional[str] = None
    marketplace_url: Optional[str] = None
    marketplace_product_id: Optional[str] = None
    our_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    shipping_cost: Decimal = Decimal("0")
    packaging_cost: Decimal = Decimal("0")
    stock_quantity: int = 0
    min_margin_rate: Decimal = Decimal("0.15")


class SellerProductUpdate(BaseModel):
    display_name: Optional[str] = None
    marketplace_url: Optional[str] = None
    marketplace_product_id: Optional[str] = None
    our_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    packaging_cost: Optional[Decimal] = None
    stock_quantity: Optional[int] = None
    min_margin_rate: Optional[Decimal] = None


class CompanyProductUpdate(ProductUpdate, SellerProductUpdate):
    pass


class SellerProductOut(SellerProductCreate):
    id: UUID
    commission_rate: Decimal = Decimal("0")
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
