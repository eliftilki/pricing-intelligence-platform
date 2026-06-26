from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

# category: kullanicinin girdigi/sectigi serbest metin alt kategori (orn.
# "Kulaklık", "Telefon"). Ust kategoriye ("Elektronik" vb.) cevirme islemi
# event eslestirmesi icin agent_service/category_taxonomy.normalize_category
# tarafindan dinamik yapilir - burada kisitlanmaz, aksi halde Elif'in
# frontend'teki alt kategori secimleri (Kulaklık, Mouse, Klavye...) reddedilir.


class ProductCreate(BaseModel):
    name: str
    normalized_key: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[UUID] = None
    color: Optional[str] = None
    connection_type: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
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
