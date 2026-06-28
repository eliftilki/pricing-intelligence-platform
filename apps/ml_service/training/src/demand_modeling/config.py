from __future__ import annotations

TARGET_COLUMN = "expected_sales"
DATE_COLUMN = "date"
GROUP_COLUMNS = ["product_id", "date"]
CATEGORICAL_COLUMNS = ["category", "stock_bucket"]
DROP_FROM_FEATURES = [DATE_COLUMN, TARGET_COLUMN]
DEFAULT_FINAL_TEST_RATIO = 0.20
DEFAULT_N_SPLITS = 5
RANDOM_SEED = 42
