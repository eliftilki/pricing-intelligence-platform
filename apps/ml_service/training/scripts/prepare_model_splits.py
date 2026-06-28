from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = PROJECT_ROOT / "training"
SRC_DIR = TRAINING_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from demand_modeling.config import DEFAULT_FINAL_TEST_RATIO, DEFAULT_N_SPLITS
from demand_modeling.data_preparation import (
    get_feature_target_columns,
    load_training_dataset,
    save_metadata,
    validate_dataset,
)
from demand_modeling.split_strategy import (
    create_expanding_time_folds_by_product,
    save_splits,
    split_final_test_by_product_time,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare model-ready time-based data splits.")
    parser.add_argument(
        "--input",
        default=TRAINING_ROOT / "data" / "processed" / "final_training_dataset.csv",
        help="Path to final_training_dataset.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=TRAINING_ROOT / "data" / "model_splits",
        help="Directory where split files will be written",
    )
    parser.add_argument(
        "--final-test-ratio",
        type=float,
        default=DEFAULT_FINAL_TEST_RATIO,
        help="Final holdout test ratio per product timeline",
    )
    parser.add_argument(
        "--n-splits",
        type=int,
        default=DEFAULT_N_SPLITS,
        help="Number of expanding-window CV folds",
    )
    args = parser.parse_args()

    df = load_training_dataset(args.input)
    validation_summary = validate_dataset(df)

    feature_cols, target_col, categorical_cols, numeric_cols = get_feature_target_columns(df)

    train_val_df, final_test_df, split_summary = split_final_test_by_product_time(
        df,
        final_test_ratio=args.final_test_ratio,
    )

    folds, fold_summary = create_expanding_time_folds_by_product(
        train_val_df,
        n_splits=args.n_splits,
    )

    output_dir = Path(args.output_dir)
    save_splits(
        train_val_df=train_val_df,
        final_test_df=final_test_df,
        folds=folds,
        split_summary=split_summary,
        fold_summary=fold_summary,
        output_dir=output_dir,
    )
    save_metadata(
        output_dir=output_dir,
        feature_cols=feature_cols,
        target_col=target_col,
        categorical_cols=categorical_cols,
        numeric_cols=numeric_cols,
        validation_summary=validation_summary,
    )

    print("Model split preparation completed.")
    print(f"Input shape: {df.shape}")
    print(f"Train+validation shape: {train_val_df.shape}")
    print(f"Final test shape: {final_test_df.shape}")
    print(f"Number of CV folds: {len(folds)}")
    print(f"Output directory: {output_dir}")
    print("\nFinal test split summary:")
    print(split_summary)
    print("\nCV fold summary head:")
    print(fold_summary.head(10))


if __name__ == "__main__":
    main()
