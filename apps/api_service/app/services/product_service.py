from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import ProductCreate, SellerProductCreate


class ProductService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)

    def create_product(self, payload: ProductCreate):
        return self.repo.create_product(payload)

    def list_products(self, limit: int = 100, offset: int = 0):
        return self.repo.list_products(limit, offset)

    def get_product(self, product_id: UUID):
        obj = self.repo.get_product(product_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Product not found")
        return obj

    def create_seller_product(self, payload: SellerProductCreate):
        return self.repo.create_seller_product(payload)

    def list_seller_products_by_company(self, company_id: UUID, limit: int = 100, offset: int = 0):
        return self.repo.list_seller_products_by_company(company_id, limit, offset)

    def update_price(self, seller_product_id: UUID, payload, user_id=None):
        sp = self.repo.get_seller_product(seller_product_id)
        if not sp:
            raise HTTPException(status_code=404, detail="Seller product not found")
        return self.repo.update_price(sp, payload.new_price, payload.change_source, user_id, payload.recommendation_id)

    def update_stock(self, seller_product_id: UUID, payload):
        sp = self.repo.get_seller_product(seller_product_id)
        if not sp:
            raise HTTPException(status_code=404, detail="Seller product not found")
        return self.repo.update_stock(sp, payload.new_stock, payload.change_source)
