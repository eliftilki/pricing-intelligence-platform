import uuid
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.models.base import Base


class PricingFeature(Base):
    __tablename__ = "pricing_features"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    feature_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    our_price = Column(Numeric(12, 2))
    cost_price = Column(Numeric(12, 2))
    commission_rate = Column(Numeric(5, 4))
    shipping_cost = Column(Numeric(12, 2))
    packaging_cost = Column(Numeric(12, 2))
    stock_quantity = Column(Integer)
    min_competitor_price = Column(Numeric(12, 2))
    avg_competitor_price = Column(Numeric(12, 2))
    max_competitor_price = Column(Numeric(12, 2))
    weighted_avg_competitor_price = Column(Numeric(12, 2))
    competitor_count = Column(Integer)
    tier1_competitor_count = Column(Integer)
    tier2_competitor_count = Column(Integer)
    noise_competitor_count = Column(Integer)
    price_gap_to_min = Column(Numeric(8, 4))
    price_gap_to_avg = Column(Numeric(8, 4))
    price_rank = Column(Integer)
    market_pressure_score = Column(Numeric(5, 2))
    stock_pressure_score = Column(Numeric(5, 2))
    buybox_threat_score = Column(Numeric(5, 2))
    price_volatility_24h = Column(Numeric(8, 4))
    competitor_aggression_score = Column(Numeric(5, 2))
    day_of_week = Column(Integer)
    hour_of_day = Column(Integer)
    is_weekend = Column(Boolean)
    campaign_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    pricing_feature_id = Column(UUID(as_uuid=True), ForeignKey("pricing_features.id", ondelete="SET NULL"))
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    candidate_price = Column(Numeric(12, 2), nullable=False)
    expected_sales_quantity = Column(Numeric(12, 2))
    confidence_score = Column(Numeric(5, 2))
    input_features = Column(JSONB)
    prediction_output = Column(JSONB)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())


class PriceRecommendation(Base):
    __tablename__ = "price_recommendations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    pricing_feature_id = Column(UUID(as_uuid=True), ForeignKey("pricing_features.id", ondelete="SET NULL"))
    current_price = Column(Numeric(12, 2), nullable=False)
    recommended_price = Column(Numeric(12, 2), nullable=False)
    action = Column(String, nullable=False)
    expected_sales_quantity = Column(Numeric(12, 2))
    expected_profit = Column(Numeric(12, 2))
    profit_uplift = Column(Numeric(12, 2))
    confidence_score = Column(Numeric(5, 2))
    risk_level = Column(String)
    reason_codes = Column(JSONB)
    explanation = Column(String)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class PricingDecision(Base):
    __tablename__ = "pricing_decisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("price_recommendations.id", ondelete="SET NULL"))
    old_price = Column(Numeric(12, 2))
    new_price = Column(Numeric(12, 2))
    decision_status = Column(String, nullable=False)
    decided_by = Column(UUID(as_uuid=True))
    decision_note = Column(String)
    decided_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    seller_product_id = Column(UUID(as_uuid=True), ForeignKey("seller_products.id", ondelete="CASCADE"))
    run_type = Column(String, nullable=False)
    status = Column(String, default="STARTED")
    input_payload = Column(JSONB)
    output_payload = Column(JSONB)
    error_message = Column(String)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))


class TrainingDatasetExport(Base):
    __tablename__ = "training_dataset_exports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_name = Column(String, nullable=False)
    dataset_version = Column(String, nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    date_from = Column(Date)
    date_to = Column(Date)
    row_count = Column(Integer)
    file_path = Column(String)
    feature_schema = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    target_variable = Column(String)
    training_dataset_export_id = Column(UUID(as_uuid=True), ForeignKey("training_dataset_exports.id", ondelete="SET NULL"))
    metrics = Column(JSONB)
    artifact_path = Column(String)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
