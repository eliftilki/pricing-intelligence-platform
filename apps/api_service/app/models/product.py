import uuid
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.models.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    normalized_key = Column(String)
    brand = Column(String)
    model = Column(String)
    category = Column(String)
    category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"))
    color = Column(String)
    connection_type = Column(String)
    storage_capacity = Column(String)
    ram_capacity = Column(String)
    sim_type = Column(String)
    switch_type = Column(String)
    keyboard_layout = Column(String)
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
    display_name = Column(String)
    marketplace_url = Column(String)
    marketplace_product_id = Column(String)
    our_price = Column(Numeric(12, 2))
    cost_price = Column(Numeric(12, 2))
    shipping_cost = Column(Numeric(12, 2), default=0)
    packaging_cost = Column(Numeric(12, 2), default=0)
    stock_quantity = Column(Integer, default=0)
    min_margin_rate = Column(Numeric(5, 4), default=0.15)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("company_id", "product_id", "marketplace"),)


class MarketplaceCommissionRule(Base):
    __tablename__ = "marketplace_commission_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marketplace = Column(String, nullable=False)
    category = Column(String, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="RESTRICT"))
    commission_rate = Column(Numeric, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


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


class SellerSalesHistory(Base):
    __tablename__ = "seller_sales_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    marketplace = Column(String, nullable=False)
    sales_quantity = Column(Integer, nullable=False)
    sales_date = Column(DateTime(timezone=True), nullable=False)
    note = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
