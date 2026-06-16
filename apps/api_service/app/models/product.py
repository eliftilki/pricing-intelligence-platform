import uuid
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.models.base import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    brand = Column(String)
    model = Column(String)
    category = Column(String)
    barcode = Column(String, unique=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class SellerProduct(Base):
    __tablename__ = "seller_products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    marketplace = Column(String, nullable=False)
    marketplace_url = Column(String)
    marketplace_product_id = Column(String)
    our_price = Column(Numeric(12, 2))
    cost_price = Column(Numeric(12, 2))
    commission_rate = Column(Numeric(5, 4), default=0)
    shipping_cost = Column(Numeric(12, 2), default=0)
    packaging_cost = Column(Numeric(12, 2), default=0)
    stock_quantity = Column(Integer, default=0)
    min_margin_rate = Column(Numeric(5, 4), default=0.15)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("company_id", "product_id", "marketplace"),)


class SellerPriceHistory(Base):
    __tablename__ = "seller_price_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    marketplace = Column(String, nullable=False)
    old_price = Column(Numeric(12, 2))
    new_price = Column(Numeric(12, 2), nullable=False)
    change_source = Column(String, nullable=False)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("price_recommendations.id", ondelete="SET NULL"))
    changed_by = Column(UUID(as_uuid=True))
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SellerStockHistory(Base):
    __tablename__ = "seller_stock_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    marketplace = Column(String, nullable=False)
    old_stock = Column(Integer)
    new_stock = Column(Integer, nullable=False)
    change_source = Column(String, nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
