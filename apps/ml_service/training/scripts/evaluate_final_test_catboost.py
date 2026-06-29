from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_ROOT = PROJECT_ROOT / "training"
SRC_DIR = TRAINING_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from demand_modeling.config import TARGET_COLUMN

MODEL_NAME = "catboost"
DEFAULT_MODELS_DIR = TRAINING_ROOT / "models" / "raw" / "catboost"
DEFAULT_FINAL_TEST_PATH = TRAINING_ROOT / "data" / "model_splits" / "final_test.csv"
DEFAULT_METADATA_PATH = TRAINING_ROOT / "data" / "model_splits" / "feature_metadata.json"
DEFAULT_REPORTS_DIR = TRAINING_ROOT / "reports" / "catboost" / "final_test"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_feature_columns(metadata: dict) -> List[str]:
    if "feature_columns" in metadata:
        return list(metadata["feature_columns"])
    if "feature_cols" in metadata:
        return list(metadata["feature_cols"])
    raise ValueError("feature_metadata.json içinde feature listesi bulunamadı.")


def discover_fold_models(models_dir: Path) -> List[Path]:
    paths = sorted(models_dir.glob(f"{MODEL_NAME}_fold_*.joblib"))
    if not paths:
        raise FileNotFoundError(
            f"Model dosyası bulunamadı: {models_dir}. "
            f"Beklenen: catboost_fold_01.joblib ... catboost_fold_05.joblib"
        )
    return paths


def safe_rmse(y_true: pd.Series, y_pred: np.ndarray) -> float:
    try:
        return float(mean_squared_error(y_true, y_pred, squared=False))
    except TypeError:
        return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def safe_mape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    y_true_array = np.asarray(y_true)
    y_pred_array = np.asarray(y_pred)
    mask = y_true_array != 0
    if not np.any(mask):
        return float("nan")
    return float(
        np.mean(np.abs((y_true_array[mask] - y_pred_array[mask]) / y_true_array[mask])) * 100
    )


def evaluate_predictions(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": safe_rmse(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
        "mape_percent": safe_mape(y_true, y_pred),
    }


def ensemble_predict(
    X: pd.DataFrame,
    model_paths: List[Path],
) -> tuple[np.ndarray, List[str]]:
    """
  Her satır için 5 fold model tahmin üretir, tahminlerin ortalamasını alır.
  """
    all_predictions: List[np.ndarray] = []
    reference_features: List[str] | None = None

    for model_path in model_paths:
        artifact = joblib.load(model_path)

        if "preprocessor" not in artifact or "model" not in artifact:
            raise ValueError(f"Desteklenmeyen model formatı: {model_path}")

        feature_columns = list(artifact["feature_columns"])
        if reference_features is None:
            reference_features = feature_columns
        elif feature_columns != reference_features:
            raise ValueError("Tüm fold modellerinde feature_columns aynı olmalı.")

        missing = [col for col in feature_columns if col not in X.columns]
        if missing:
            raise ValueError(f"Final test verisinde eksik kolonlar: {missing}")

        X_subset = X[feature_columns]
        X_transformed = artifact["preprocessor"].transform(X_subset)
        preds = artifact["model"].predict(X_transformed)
        all_predictions.append(np.asarray(preds, dtype=float))

    ensemble = np.mean(np.stack(all_predictions, axis=0), axis=0)
    return ensemble, reference_features or []


def build_prediction_report(
    df: pd.DataFrame,
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> pd.DataFrame:
    context_columns = [
        col
        for col in ["product_id", "date", "candidate_price", "category", "stock_bucket"]
        if col in df.columns
    ]
    report = df[context_columns].copy()
    report["actual_expected_sales"] = y_true.values
    report["predicted_expected_sales"] = y_pred
    report["error"] = report["actual_expected_sales"] - report["predicted_expected_sales"]
    report["abs_error"] = report["error"].abs()
    report["ape_percent"] = np.where(
        report["actual_expected_sales"] != 0,
        (report["abs_error"] / report["actual_expected_sales"]) * 100,
        np.nan,
    )
    return report


def calculate_product_metrics(report_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product_id, group in report_df.groupby("product_id"):
        metrics = evaluate_predictions(
            group["actual_expected_sales"],
            group["predicted_expected_sales"].to_numpy(),
        )
        rows.append({"product_id": product_id, "rows": len(group), **metrics})
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="5 fold CatBoost modeli ile final_test.csv üzerinde ensemble değerlendirme."
    )
    parser.add_argument("--final-test", type=Path, default=DEFAULT_FINAL_TEST_PATH)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.final_test.exists():
        raise FileNotFoundError(f"Final test dosyası bulunamadı: {args.final_test}")

    metadata = load_json(args.metadata)
    feature_columns = get_feature_columns(metadata)

    final_test_df = pd.read_csv(args.final_test)
    model_paths = discover_fold_models(args.models_dir)

    missing_features = [col for col in feature_columns if col not in final_test_df.columns]
    if missing_features:
        raise ValueError(f"Final test verisinde eksik feature kolonları: {missing_features}")

    if TARGET_COLUMN not in final_test_df.columns:
        raise ValueError(f"Final test verisinde hedef kolon yok: {TARGET_COLUMN}")

    X = final_test_df[feature_columns].copy()
    y_true = final_test_df[TARGET_COLUMN].copy()

    predictions, used_features = ensemble_predict(X, model_paths)
    metrics = evaluate_predictions(y_true, predictions)

    report_df = build_prediction_report(final_test_df, y_true, predictions)
    product_metrics_df = calculate_product_metrics(report_df)

    args.reports_dir.mkdir(parents=True, exist_ok=True)

    predictions_path = args.reports_dir / "final_test_predictions.csv"
    product_metrics_path = args.reports_dir / "final_test_product_metrics.csv"
    summary_path = args.reports_dir / "final_test_summary.json"

    report_df.to_csv(predictions_path, index=False)
    product_metrics_df.to_csv(product_metrics_path, index=False)

    summary = {
        "evaluation_type": "held_out_final_test",
        "model_name": MODEL_NAME,
        "n_fold_models": len(model_paths),
        "ensemble_strategy": "mean",
        "final_test_path": str(args.final_test.resolve()),
        "models_dir": str(args.models_dir.resolve()),
        "rows": len(final_test_df),
        "feature_count": len(used_features),
        "metrics": metrics,
        "fold_model_files": [path.name for path in model_paths],
        "notes": [
            "Her satır için 5 fold tahmin üretildi ve tahmin ortalaması alındı.",
            "final_test.csv eğitim sırasında kullanılmadı.",
            "Bu sonuçlara göre hyperparameter ayarı yapmayın.",
        ],
    }
    save_json(summary, summary_path)

    print("\nFinal test değerlendirmesi tamamlandı.")
    print(f"Satır sayısı: {len(final_test_df)}")
    print(f"Kullanılan fold model sayısı: {len(model_paths)}")
    print(
        f"MAE: {metrics['mae']:.4f} | "
        f"RMSE: {metrics['rmse']:.4f} | "
        f"R2: {metrics['r2']:.4f} | "
        f"MAPE: {metrics['mape_percent']:.2f}%"
    )
    print("\nRaporlar:")
    print(f"- {summary_path}")
    print(f"- {predictions_path}")
    print(f"- {product_metrics_path}")


if __name__ == "__main__":
    main()