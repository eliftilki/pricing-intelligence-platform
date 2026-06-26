from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .config import DATE_COLUMN


def split_final_test_by_product_time(
    df: pd.DataFrame,
    final_test_ratio: float = 0.20,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Her ürün için zaman çizelgesini ikiye böler. 

    Aynı günün 7 candidate_price satırı birlikte taşınır; 
    model eğitiminde görülen bir günün fiyat senaryoları test setine sızamaz.
    """
    train_val_parts = []
    final_test_parts = []
    summary_rows = []

    for product_id, product_df in df.groupby("product_id", sort=True):
        product_dates = list(sorted(product_df[DATE_COLUMN].unique()))
        n_dates = len(product_dates)
        n_test = max(1, int(np.ceil(n_dates * final_test_ratio)))

        train_val_dates = set(product_dates[:-n_test])
        final_test_dates = set(product_dates[-n_test:])

        product_train_val = product_df[product_df[DATE_COLUMN].isin(train_val_dates)].copy()
        product_final_test = product_df[product_df[DATE_COLUMN].isin(final_test_dates)].copy()

        train_val_parts.append(product_train_val)
        final_test_parts.append(product_final_test)

        summary_rows.append({
            "product_id": product_id,
            "total_dates": n_dates,
            "train_val_dates": len(train_val_dates),
            "final_test_dates": len(final_test_dates),
            "train_val_start": min(train_val_dates),
            "train_val_end": max(train_val_dates),
            "final_test_start": min(final_test_dates),
            "final_test_end": max(final_test_dates),
            "train_val_rows": len(product_train_val),
            "final_test_rows": len(product_final_test),
        })

    train_val_df = pd.concat(train_val_parts, ignore_index=True)
    final_test_df = pd.concat(final_test_parts, ignore_index=True)
    split_summary = pd.DataFrame(summary_rows)

    train_val_df = train_val_df.sort_values(["product_id", DATE_COLUMN, "candidate_price"]).reset_index(drop=True)
    final_test_df = final_test_df.sort_values(["product_id", DATE_COLUMN, "candidate_price"]).reset_index(drop=True)

    return train_val_df, final_test_df, split_summary


def create_expanding_time_folds_by_product(
    train_val_df: pd.DataFrame,
    n_splits: int = 5,
) -> Tuple[List[Dict[str, pd.DataFrame]], pd.DataFrame]:
    """Her ürün için 5 adet genişleyen pencere cross validation oluşturulur ve birleştirilir.

    Train penceresi her fold'da büyür, validaiton her seferinde bir sonraki zaman bloğunu kullanır.
    """
    product_fold_dates: Dict[int, List[Tuple[set, set]]] = {}

    for product_id, product_df in train_val_df.groupby("product_id", sort=True):
        dates = list(sorted(product_df[DATE_COLUMN].unique()))
        n_dates = len(dates)
        val_size = n_dates // (n_splits + 1)
        if val_size < 1:
            raise ValueError(f"Not enough dates for {n_splits} splits for product {product_id}")

        initial_train_size = n_dates - (n_splits * val_size)
        if initial_train_size < 1:
            raise ValueError(f"Initial train size became invalid for product {product_id}")

        folds_for_product = []
        for fold_idx in range(n_splits):
            train_end = initial_train_size + fold_idx * val_size
            val_start = train_end
            val_end = val_start + val_size

            train_dates = set(dates[:train_end])
            val_dates = set(dates[val_start:val_end])
            folds_for_product.append((train_dates, val_dates))

        product_fold_dates[int(product_id)] = folds_for_product

    folds = []
    summary_rows = []

    for fold_idx in range(n_splits):
        fold_train_parts = []
        fold_val_parts = []

        for product_id, product_df in train_val_df.groupby("product_id", sort=True):
            train_dates, val_dates = product_fold_dates[int(product_id)][fold_idx]
            train_part = product_df[product_df[DATE_COLUMN].isin(train_dates)].copy()
            val_part = product_df[product_df[DATE_COLUMN].isin(val_dates)].copy()
            fold_train_parts.append(train_part)
            fold_val_parts.append(val_part)

            summary_rows.append({
                "fold": fold_idx + 1,
                "product_id": product_id,
                "train_dates": len(train_dates),
                "validation_dates": len(val_dates),
                "train_start": min(train_dates),
                "train_end": max(train_dates),
                "validation_start": min(val_dates),
                "validation_end": max(val_dates),
                "train_rows": len(train_part),
                "validation_rows": len(val_part),
            })

        fold_train_df = pd.concat(fold_train_parts, ignore_index=True)
        fold_val_df = pd.concat(fold_val_parts, ignore_index=True)

        fold_train_df = fold_train_df.sort_values(["product_id", DATE_COLUMN, "candidate_price"]).reset_index(drop=True)
        fold_val_df = fold_val_df.sort_values(["product_id", DATE_COLUMN, "candidate_price"]).reset_index(drop=True)

        folds.append({
            "fold": fold_idx + 1,
            "train": fold_train_df,
            "validation": fold_val_df,
        })

    fold_summary = pd.DataFrame(summary_rows)
    return folds, fold_summary


def save_splits(
    train_val_df: pd.DataFrame,
    final_test_df: pd.DataFrame,
    folds: List[Dict[str, pd.DataFrame]],
    split_summary: pd.DataFrame,
    fold_summary: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    output_dir = Path(output_dir)
    folds_dir = output_dir / "folds"
    folds_dir.mkdir(parents=True, exist_ok=True)

    train_val_df.to_csv(output_dir / "train_val.csv", index=False)
    final_test_df.to_csv(output_dir / "final_test.csv", index=False)
    split_summary.to_csv(output_dir / "final_test_split_summary.csv", index=False)
    fold_summary.to_csv(output_dir / "cv_fold_summary.csv", index=False)

    for fold in folds:
        fold_id = fold["fold"]
        fold["train"].to_csv(folds_dir / f"fold_{fold_id:02d}_train.csv", index=False)
        fold["validation"].to_csv(folds_dir / f"fold_{fold_id:02d}_validation.csv", index=False)
