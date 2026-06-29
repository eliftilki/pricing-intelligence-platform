from __future__ import annotations

TARGET_COLUMN = "expected_sales"
DATE_COLUMN = "date"
PRODUCT_ID_COLUMN = "product_id"
PRODUCT_NAME_COLUMN = "product_name"
GROUP_COLUMNS = ["product_id", "date"]
CATEGORICAL_COLUMNS = ["category", "stock_bucket"]
DROP_FROM_FEATURES = [
    DATE_COLUMN,
    TARGET_COLUMN,
    PRODUCT_ID_COLUMN,
    PRODUCT_NAME_COLUMN,
]
MODEL_FEATURE_COLUMNS = [
    "category",
    "month",
    "is_weekend",
    "is_salary_week",
    "candidate_price",
    "min_competitor_price",
    "avg_competitor_price",
    "market_avg_price",
    "market_price_trend_7d",
    "market_volatility_7d",
    "competitor_count",
    "tier1_competitor_count",
    "price_gap_to_min",
    "price_gap_to_avg",
    "price_gap_to_market_avg",
    "price_rank",
    "market_pressure_score",
    "competitor_aggression_score",
    "trend_score",
    "interest_change_7d",
    "interest_change_30d",
    "event_detected",
    "event_type_id",
    "days_until_event",
    "event_confidence",
    "category_demand_change",
    "recommended_demand_multiplier",
    "sales_7d_avg",
    "stock_quantity",
    "stock_bucket",
]
DEFAULT_FINAL_TEST_RATIO = 0.20
DEFAULT_N_SPLITS = 5
RANDOM_SEED = 42
