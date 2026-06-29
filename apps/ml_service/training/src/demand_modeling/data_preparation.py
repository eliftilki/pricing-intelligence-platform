from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .config import (
    CATEGORICAL_COLUMNS,
    DATE_COLUMN,
    DROP_FROM_FEATURES,
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMN,
)


def load_training_dataset(path: str | Path) -> pd.DataFrame:
    """Eğiitm verisi yüklenir, temizlenir ve sıralanır."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)

    if DATE_COLUMN not in df.columns:
        raise ValueError(f"Missing required date column: {DATE_COLUMN}")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing required target column: {TARGET_COLUMN}")

    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN])

    sort_cols = ["product_id", DATE_COLUMN]
    if "candidate_price" in df.columns:
        sort_cols.append("candidate_price")
    df = df.sort_values(sort_cols).reset_index(drop=True)

    return df


def validate_dataset(df: pd.DataFrame) -> Dict[str, object]:
    """Eğiitm öncesi veriler doğrulanır"""
    required_cols = {"product_id", "category", DATE_COLUMN, "candidate_price", TARGET_COLUMN}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    null_count = int(df.isna().sum().sum())
    if null_count > 0:
        raise ValueError(f"Dataset contains missing values: {null_count}")

    product_date_counts = (
        df.groupby("product_id")[DATE_COLUMN]
        .nunique()
        .astype(int)
        .to_dict()
    )

    candidate_rows_per_product_day = (
        df.groupby(["product_id", DATE_COLUMN])
        .size()
        .describe()
        .to_dict()
    )

    return {
        "shape": df.shape,
        "null_count": null_count,
        "product_date_counts": product_date_counts,
        "candidate_rows_per_product_day_summary": candidate_rows_per_product_day,
    }


def get_feature_target_columns(df: pd.DataFrame) -> Tuple[List[str], str, List[str], List[str]]:
    """Modele girecek kolonlar MODEL_FEATURE_COLUMNS allowlist ile secilir."""
    missing = [col for col in MODEL_FEATURE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing columns required for model training: {missing}"
        )

    feature_cols = list(MODEL_FEATURE_COLUMNS)

    categorical_cols = [col for col in CATEGORICAL_COLUMNS if col in feature_cols]
    numeric_cols = [col for col in feature_cols if col not in categorical_cols]

    return feature_cols, TARGET_COLUMN, categorical_cols, numeric_cols


def save_metadata(
    output_dir: str | Path,
    feature_cols: List[str],
    target_col: str,
    categorical_cols: List[str],
    numeric_cols: List[str],
    validation_summary: Dict[str, object],
) -> None:
    """Sütun şeması ve veri doğrulama özeti JSON olarak yazılır. Eğiitm scriptleri bu JSON'ı okur."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "target_col": target_col,
        "feature_cols": feature_cols,
        "categorical_cols": categorical_cols,
        "numeric_cols": numeric_cols,
        "dropped_from_features": DROP_FROM_FEATURES,
        "validation_summary": validation_summary,
    }

    with open(output_dir / "feature_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
