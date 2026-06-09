from uuid import UUID
from sqlalchemy.orm import Session
from app.models.product import Product, SellerProduct, SellerPriceHistory, SellerStockHistory
from app.repositories.base_repository import BaseRepository
from app.schemas.product_schema import ProductCreate, SellerProductCreate


class ProductRepository(BaseRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, payload: ProductCreate):
        product = Product(**payload.model_dump())
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def list_products(self, limit: int = 100, offset: int = 0):
        query = self.db.query(Product).order_by(Product.created_at.desc())
        return self.paginate(query, limit, offset).all()

    def get_product(self, product_id: UUID):
        return self.db.query(Product).filter(Product.id == product_id).first()

    def create_seller_product(self, payload: SellerProductCreate):
        seller_product = SellerProduct(**payload.model_dump())
        self.db.add(seller_product)
        self.db.flush()
        if seller_product.our_price is not None:
            self.db.add(SellerPriceHistory(
                company_id=seller_product.company_id,
                product_id=seller_product.product_id,
                seller_product_id=seller_product.id,
                marketplace=seller_product.marketplace,
                old_price=None,
                new_price=seller_product.our_price,
                change_source="INITIAL",
            ))
        self.db.add(SellerStockHistory(
            company_id=seller_product.company_id,
            product_id=seller_product.product_id,
            seller_product_id=seller_product.id,
            marketplace=seller_product.marketplace,
            old_stock=None,
            new_stock=seller_product.stock_quantity or 0,
            change_source="INITIAL",
        ))
        self.db.commit()
        self.db.refresh(seller_product)
        return seller_product

    def list_seller_products_by_company(self, company_id: UUID, limit: int = 100, offset: int = 0):
        query = (
            self.db.query(SellerProduct)
            .filter(SellerProduct.company_id == company_id)
            .order_by(SellerProduct.created_at.desc())
        )
        return self.paginate(query, limit, offset).all()

    def get_seller_product(self, seller_product_id: UUID):
        return self.db.query(SellerProduct).filter(SellerProduct.id == seller_product_id).first()

    def update_price(self, seller_product: SellerProduct, new_price, change_source: str, changed_by=None, recommendation_id=None):
        old_price = seller_product.our_price
        seller_product.our_price = new_price
        self.db.add(SellerPriceHistory(
            company_id=seller_product.company_id,
            product_id=seller_product.product_id,
            seller_product_id=seller_product.id,
            marketplace=seller_product.marketplace,
            old_price=old_price,
            new_price=new_price,
            change_source=change_source,
            changed_by=changed_by,
            recommendation_id=recommendation_id,
        ))
        self.db.commit()
        self.db.refresh(seller_product)
        return seller_product

    def update_stock(self, seller_product: SellerProduct, new_stock: int, change_source: str):
        old_stock = seller_product.stock_quantity
        seller_product.stock_quantity = new_stock
        self.db.add(SellerStockHistory(
            company_id=seller_product.company_id,
            product_id=seller_product.product_id,
            seller_product_id=seller_product.id,
            marketplace=seller_product.marketplace,
            old_stock=old_stock,
            new_stock=new_stock,
            change_source=change_source,
        ))
        self.db.commit()
        self.db.refresh(seller_product)
        return seller_product
