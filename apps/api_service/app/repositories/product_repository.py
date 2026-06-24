from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.product import (
    MarketplaceCommissionRule,
    Product,
    SellerProduct,
    SellerPriceHistory,
    SellerStockHistory,
)
from app.repositories.base_repository import BaseRepository
from app.schemas.product_schema import ProductCreate, SellerProductCreate, SellerProductUpdate
from app.services.product_resolver import normalize_token


class ProductRepository(BaseRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, payload: ProductCreate):
        product = Product(**payload.model_dump())
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_product_by_normalized_key(self, normalized_key: str):
        return (
            self.db.query(Product)
            .filter(Product.normalized_key == normalized_key)
            .first()
        )

    def find_product_by_fingerprint(self, payload: ProductCreate):
        if not payload.brand:
            return None

        candidates = (
            self.db.query(Product)
            .filter(func.lower(Product.brand) == payload.brand.lower())
            .all()
        )

        payload_model = normalize_token(payload.model)
        payload_category = normalize_token(payload.category)
        payload_color = normalize_token(payload.color)
        payload_connection = normalize_token(payload.connection_type)

        for product in candidates:
            same_identity = (
                normalize_token(product.model) == payload_model
                and normalize_token(product.category) == payload_category
                and normalize_token(product.color) == payload_color
            )
            if not same_identity:
                continue

            product_connection = normalize_token(product.connection_type)
            if product_connection in (payload_connection, None):
                return product

        return None

    def complete_product_resolution(
        self,
        product: Product,
        payload: ProductCreate,
        normalized_key: str | None,
    ):
        if normalized_key and not product.normalized_key:
            product.normalized_key = normalized_key
        if payload.connection_type and not product.connection_type:
            product.connection_type = payload.connection_type
        if payload.color and not product.color:
            product.color = payload.color
        if payload.model and not product.model:
            product.model = payload.model
        if payload.category and not product.category:
            product.category = payload.category

        self.db.commit()
        self.db.refresh(product)
        return product

    def list_products(self, limit: int = 100, offset: int = 0):
        query = self.db.query(Product).order_by(Product.created_at.desc())
        return self.paginate(query, limit, offset).all()

    def get_product(self, product_id: UUID):
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_commission_rate(self, marketplace: str, category: str | None):
        if not category:
            return None

        rule = (
            self.db.query(MarketplaceCommissionRule)
            .filter(MarketplaceCommissionRule.marketplace == marketplace.upper())
            .filter(MarketplaceCommissionRule.category == category)
            .filter(MarketplaceCommissionRule.is_active.is_(True))
            .first()
        )
        return rule.commission_rate if rule else None

    def update_product(self, product: Product, values: dict):
        for field, value in values.items():
            setattr(product, field, value)

        self.db.commit()
        self.db.refresh(product)
        return product

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

    def get_seller_product_by_company_product_marketplace(
        self,
        company_id: UUID,
        product_id: UUID,
        marketplace: str,
    ):
        return (
            self.db.query(SellerProduct)
            .filter(SellerProduct.company_id == company_id)
            .filter(SellerProduct.product_id == product_id)
            .filter(SellerProduct.marketplace == marketplace.upper())
            .first()
        )

    def list_seller_products_by_company(self, company_id: UUID, limit: int = 100, offset: int = 0):
        query = (
            self.db.query(SellerProduct)
            .filter(SellerProduct.company_id == company_id)
            .filter(SellerProduct.is_active.is_(True))
            .order_by(SellerProduct.created_at.desc())
        )
        return self.paginate(query, limit, offset).all()

    def list_seller_products_by_company_product(self, company_id: UUID, product_id: UUID):
        return (
            self.db.query(SellerProduct)
            .filter(SellerProduct.company_id == company_id)
            .filter(SellerProduct.product_id == product_id)
            .filter(SellerProduct.is_active.is_(True))
            .all()
        )

    def get_seller_product(self, seller_product_id: UUID):
        return self.db.query(SellerProduct).filter(SellerProduct.id == seller_product_id).first()

    def update_seller_product(self, seller_product: SellerProduct, payload: SellerProductUpdate):
        values = payload.model_dump(exclude_unset=True)

        new_price = values.pop("our_price", None)
        new_stock = values.pop("stock_quantity", None)

        for field, value in values.items():
            setattr(seller_product, field, value)

        if new_price is not None and seller_product.our_price != new_price:
            old_price = seller_product.our_price
            seller_product.our_price = new_price
            self.db.add(SellerPriceHistory(
                company_id=seller_product.company_id,
                product_id=seller_product.product_id,
                seller_product_id=seller_product.id,
                marketplace=seller_product.marketplace,
                old_price=old_price,
                new_price=new_price,
                change_source="MANUAL",
            ))

        if new_stock is not None and seller_product.stock_quantity != new_stock:
            old_stock = seller_product.stock_quantity
            seller_product.stock_quantity = new_stock
            self.db.add(SellerStockHistory(
                company_id=seller_product.company_id,
                product_id=seller_product.product_id,
                seller_product_id=seller_product.id,
                marketplace=seller_product.marketplace,
                old_stock=old_stock,
                new_stock=new_stock,
                change_source="MANUAL",
            ))

        self.db.commit()
        self.db.refresh(seller_product)
        return seller_product

    def deactivate_seller_products_by_company_product(self, company_id: UUID, product_id: UUID):
        seller_products = self.list_seller_products_by_company_product(company_id, product_id)
        for seller_product in seller_products:
            seller_product.is_active = False

        self.db.commit()
        return seller_products

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
