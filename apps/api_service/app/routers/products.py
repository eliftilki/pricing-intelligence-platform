from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.product_schema import (
    CompanyProductUpdate,
    ProductCreate,
    ProductOut,
    SalesQuantityCreate,
    SalesQuantityOut,
    SellerProductCreate,
    SellerProductOut,
    UpdatePriceRequest,
    UpdateStockRequest,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("", response_model=ProductOut)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return ProductService(db).create_product(payload)

@router.get("", response_model=list[ProductOut])
def list_products(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return ProductService(db).list_products(limit, offset)

@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    return ProductService(db).get_product(product_id)

@router.post("/seller-products", response_model=SellerProductOut)
def create_seller_product(payload: SellerProductCreate, db: Session = Depends(get_db)):
    return ProductService(db).create_seller_product(payload)

@router.get("/seller-products/company/{company_id}", response_model=list[SellerProductOut])
def list_seller_products(
    company_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return ProductService(db).list_seller_products_by_company(company_id, limit, offset)

@router.patch("/company-products/{company_id}/{product_id}", response_model=list[SellerProductOut])
def update_company_product(
    company_id: UUID,
    product_id: UUID,
    payload: CompanyProductUpdate,
    db: Session = Depends(get_db),
):
    return ProductService(db).update_company_product(company_id, product_id, payload)

@router.delete("/company-products/{company_id}/{product_id}")
def delete_company_product(
    company_id: UUID,
    product_id: UUID,
    db: Session = Depends(get_db),
):
    return ProductService(db).delete_company_product(company_id, product_id)

@router.patch("/seller-products/{seller_product_id}/price", response_model=SellerProductOut)
def update_price(seller_product_id: UUID, payload: UpdatePriceRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return ProductService(db).update_price(seller_product_id, payload, user_id=user["id"])

@router.patch("/seller-products/{seller_product_id}/stock", response_model=SellerProductOut)
def update_stock(seller_product_id: UUID, payload: UpdateStockRequest, db: Session = Depends(get_db)):
    return ProductService(db).update_stock(seller_product_id, payload)

@router.post("/seller-products/{seller_product_id}/sales", response_model=SalesQuantityOut)
def create_sales_quantity(
    seller_product_id: UUID,
    payload: SalesQuantityCreate,
    db: Session = Depends(get_db),
):
    return ProductService(db).create_sales_quantity(seller_product_id, payload)
