from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OneHotEncoder


MODEL_NAME = "catboost"
TARGET_COLUMN = "expected_sales"
DATE_COLUMN = "date"
DEFAULT_CATEGORICAL_COLUMNS = ["category", "stock_bucket"]
DEFAULT_DROP_COLUMNS = [DATE_COLUMN, TARGET_COLUMN]
RANDOM_SEED = 42
DEFAULT_N_FOLDS = 5

# Baseline — random search karşılaştırma referansı
BASELINE_ITERATIONS = 100
BASELINE_DEPTH = 4
BASELINE_LEARNING_RATE = 0.08
BASELINE_L2_LEAF_REG = 3.0

SELECTED_HYPERPARAMETERS_REL_PATH = (
    Path("reports") / "catboost" / "hyperparameter_search" / "selected_hyperparameters.json"
)
REQUIRED_HYPERPARAMETER_KEYS = ("iterations", "depth", "learning_rate", "l2_leaf_reg")


def get_project_root() -> Path:
    """
    Beklenen konum:
    apps/ml_service/training/scripts/train_catboost.py

    parents[2] -> apps/ml_service
    """
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_default_selected_hyperparameters_path(training_root: Path) -> Path:
    return training_root / SELECTED_HYPERPARAMETERS_REL_PATH


def baseline_hyperparameters() -> Dict[str, Any]:
    return {
        "iterations": BASELINE_ITERATIONS,
        "depth": BASELINE_DEPTH,
        "learning_rate": BASELINE_LEARNING_RATE,
        "l2_leaf_reg": BASELINE_L2_LEAF_REG,
    }


def load_selected_hyperparameters(path: Path) -> Tuple[Dict[str, Any], str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Seçili hiperparametre dosyası bulunamadı: {path}\n"
            "Random search sonrası selected_hyperparameters.json oluşturulmalı."
        )

    payload = load_json(path)
    if not payload:
        raise ValueError(f"Geçersiz hiperparametre dosyası: {path}")

    missing_keys = [key for key in REQUIRED_HYPERPARAMETER_KEYS if key not in payload]
    if missing_keys:
        raise ValueError(
            f"selected_hyperparameters.json içinde eksik alanlar: {missing_keys}"
        )

    hyperparameters = {
        "iterations": int(payload["iterations"]),
        "depth": int(payload["depth"]),
        "learning_rate": float(payload["learning_rate"]),
        "l2_leaf_reg": float(payload["l2_leaf_reg"]),
    }

    trial_id = payload.get("trial_id")
    if trial_id is not None:
        tuning_source = f"random_search trial_id={int(trial_id)}"
    else:
        tuning_source = str(payload.get("source", path.name))

    return hyperparameters, tuning_source


def resolve_run_configuration(
    run_mode: str,
    training_root: Path,
    selected_hyperparameters_path: Optional[Path],
) -> Tuple[Dict[str, Any], str, str, str]:
    if run_mode == "baseline":
        return (
            baseline_hyperparameters(),
            "baseline_fixed_parameters",
            "cv_summary_baseline.json",
            "cv_results_baseline.csv",
        )

    if run_mode == "tuned":
        hyperparameters_path = (
            selected_hyperparameters_path
            or get_default_selected_hyperparameters_path(training_root)
        )
        hyperparameters, tuning_source = load_selected_hyperparameters(hyperparameters_path)
        return (
            hyperparameters,
            tuning_source,
            "cv_summary.json",
            "cv_results.csv",
        )

    raise ValueError(f"Desteklenmeyen run_mode: {run_mode}")


def make_one_hot_encoder() -> OneHotEncoder:
    """
    sklearn sürüm farkları için güvenli OneHotEncoder oluşturur.
    Yeni sürümlerde sparse_output, eski sürümlerde sparse kullanılır.
    """
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def get_feature_columns(
    df: pd.DataFrame,
    metadata: Optional[Dict],
) -> List[str]:
    if metadata and "feature_columns" in metadata:
        feature_columns = metadata["feature_columns"]
    elif metadata and "feature_cols" in metadata:
        feature_columns = metadata["feature_cols"]
    else:
        feature_columns = [
            column for column in df.columns
            if column not in DEFAULT_DROP_COLUMNS
        ]

    missing_columns = [column for column in feature_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Metadata içinde olup veri setinde bulunmayan feature kolonları: {missing_columns}")

    leakage_columns = [column for column in feature_columns if column in [TARGET_COLUMN, DATE_COLUMN]]
    if leakage_columns:
        raise ValueError(f"Feature listesinde olmaması gereken kolonlar var: {leakage_columns}")

    return feature_columns


def get_categorical_columns(
    feature_columns: List[str],
    metadata: Optional[Dict],
) -> List[str]:
    if metadata and "categorical_columns" in metadata:
        categorical_columns = metadata["categorical_columns"]
    elif metadata and "categorical_cols" in metadata:
        categorical_columns = metadata["categorical_cols"]
    else:
        categorical_columns = DEFAULT_CATEGORICAL_COLUMNS

    return [
        column for column in categorical_columns
        if column in feature_columns
    ]


def prepare_xy(
    df: pd.DataFrame,
    feature_columns: List[str],
) -> Tuple[pd.DataFrame, pd.Series]:
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column bulunamadı: {TARGET_COLUMN}")

    missing_features = [column for column in feature_columns if column not in df.columns]
    if missing_features:
        raise ValueError(f"Veri setinde eksik feature kolonları var: {missing_features}")

    X = df[feature_columns].copy()
    y = df[TARGET_COLUMN].copy()

    return X, y


def build_catboost_components(
    feature_columns: List[str],
    categorical_columns: List[str],
    hyperparameters: Dict[str, Any],
) -> Tuple[ColumnTransformer, CatBoostRegressor]:
    numeric_columns = [
        column for column in feature_columns
        if column not in categorical_columns
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", make_one_hot_encoder(), categorical_columns),
            ("numeric", "passthrough", numeric_columns),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    model = CatBoostRegressor(
        loss_function="RMSE",
        iterations=int(hyperparameters["iterations"]),
        depth=int(hyperparameters["depth"]),
        learning_rate=float(hyperparameters["learning_rate"]),
        l2_leaf_reg=float(hyperparameters["l2_leaf_reg"]),
        random_seed=RANDOM_SEED,
        verbose=False,
        allow_writing_files=False,
    )

    return preprocessor, model


def safe_rmse(y_true: pd.Series, y_pred: np.ndarray) -> float:
    try:
        return float(mean_squared_error(y_true, y_pred, squared=False))
    except TypeError:
        return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def safe_mape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    y_true_array = np.asarray(y_true)
    y_pred_array = np.asarray(y_pred)

    non_zero_mask = y_true_array != 0
    if not np.any(non_zero_mask):
        return np.nan

    return float(
        np.mean(
            np.abs(
                (y_true_array[non_zero_mask] - y_pred_array[non_zero_mask])
                / y_true_array[non_zero_mask]
            )
        )
        * 100
    )


def evaluate_predictions(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": safe_rmse(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
        "mape_percent": safe_mape(y_true, y_pred),
    }


def build_prediction_report(
    validation_df: pd.DataFrame,
    y_true: pd.Series,
    y_pred: np.ndarray,
    fold_number: int,
) -> pd.DataFrame:
    context_columns = [
        "product_id",
        "date",
        "candidate_price",
        "category",
        "stock_bucket",
    ]

    available_context_columns = [
        column for column in context_columns
        if column in validation_df.columns
    ]

    report_df = validation_df[available_context_columns].copy()
    report_df["fold"] = fold_number
    report_df["actual_expected_sales"] = y_true.values
    report_df["predicted_expected_sales"] = y_pred
    report_df["error"] = report_df["actual_expected_sales"] - report_df["predicted_expected_sales"]
    report_df["abs_error"] = report_df["error"].abs()

    report_df["percentage_error"] = np.where(
        report_df["actual_expected_sales"] != 0,
        (report_df["abs_error"] / report_df["actual_expected_sales"]) * 100,
        np.nan,
    )

    return report_df


def get_feature_importance(
    preprocessor: ColumnTransformer,
    model: CatBoostRegressor,
    fold_number: int,
) -> pd.DataFrame:

    try:
        transformed_feature_names = preprocessor.get_feature_names_out()
    except Exception:
        transformed_feature_names = np.array(
            [f"feature_{index}" for index in range(len(model.feature_importances_))]
        )

    return pd.DataFrame(
        {
            "fold": fold_number,
            "feature": transformed_feature_names,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)


def calculate_product_metrics(
    prediction_df: pd.DataFrame,
) -> pd.DataFrame:
    if "product_id" not in prediction_df.columns:
        return pd.DataFrame()

    rows = []

    for product_id, group in prediction_df.groupby("product_id"):
        metrics = evaluate_predictions(
            group["actual_expected_sales"],
            group["predicted_expected_sales"].to_numpy(),
        )

        rows.append(
            {
                "fold": int(group["fold"].iloc[0]),
                "product_id": product_id,
                "row_count": len(group),
                **metrics,
            }
        )

    return pd.DataFrame(rows)


def summarize_cv_results(results_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    metric_columns = ["mae", "rmse", "r2", "mape_percent"]

    summary = {}

    for metric in metric_columns:
        summary[metric] = {
            "mean": float(results_df[metric].mean()),
            "std": float(results_df[metric].std(ddof=0)),
            "min": float(results_df[metric].min()),
            "max": float(results_df[metric].max()),
        }

    summary["rows"] = {
        "mean_train_rows": float(results_df["train_rows"].mean()),
        "mean_validation_rows": float(results_df["validation_rows"].mean()),
    }

    return summary


def train_and_validate_folds(
    folds_dir: Path,
    reports_dir: Path,
    models_dir: Path,
    metadata_path: Path,
    n_folds: int,
    save_fold_models: bool,
    run_mode: str,
    selected_hyperparameters_path: Optional[Path],
) -> pd.DataFrame:
    metadata = load_json(metadata_path)
    training_root = get_project_root() / "training"
    hyperparameters, tuning_source, cv_summary_filename, cv_results_filename = (
        resolve_run_configuration(
            run_mode=run_mode,
            training_root=training_root,
            selected_hyperparameters_path=selected_hyperparameters_path,
        )
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    model_report_dir = reports_dir / MODEL_NAME
    predictions_dir = model_report_dir / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)

    first_train_path = folds_dir / "fold_01_train.csv"
    if not first_train_path.exists():
        raise FileNotFoundError(f"İlk fold train dosyası bulunamadı: {first_train_path}")

    first_train_df = pd.read_csv(first_train_path)

    feature_columns = get_feature_columns(first_train_df, metadata)
    categorical_columns = get_categorical_columns(feature_columns, metadata)

    cv_results: List[Dict] = []
    all_feature_importance: List[pd.DataFrame] = []
    all_product_metrics: List[pd.DataFrame] = []

    print(f"\nModel: CatBoostRegressor")
    print(f"Run mode: {run_mode}")
    print(f"Fold klasörü: {folds_dir}")
    print(f"Kullanılan feature sayısı: {len(feature_columns)}")
    print(f"Kategorik kolonlar: {categorical_columns}")
    print(
        "Hiperparametreler: "
        f"depth={hyperparameters['depth']} | "
        f"lr={hyperparameters['learning_rate']} | "
        f"iter={hyperparameters['iterations']} | "
        f"l2={hyperparameters['l2_leaf_reg']}\n"
    )

    for fold_number in range(1, n_folds + 1):
        train_path = folds_dir / f"fold_{fold_number:02d}_train.csv"
        validation_path = folds_dir / f"fold_{fold_number:02d}_validation.csv"

        if not train_path.exists():
            raise FileNotFoundError(f"Train dosyası bulunamadı: {train_path}")

        if not validation_path.exists():
            raise FileNotFoundError(f"Validation dosyası bulunamadı: {validation_path}")

        train_df = pd.read_csv(train_path)
        validation_df = pd.read_csv(validation_path)

        X_train, y_train = prepare_xy(train_df, feature_columns)
        X_validation, y_validation = prepare_xy(validation_df, feature_columns)

        preprocessor, model = build_catboost_components(
            feature_columns=feature_columns,
            categorical_columns=categorical_columns,
            hyperparameters=hyperparameters,
        )

        X_train_transformed = preprocessor.fit_transform(X_train)
        X_validation_transformed = preprocessor.transform(X_validation)

        model.fit(X_train_transformed, y_train)
        predictions = model.predict(X_validation_transformed)

        metrics = evaluate_predictions(y_validation, predictions)

        cv_results.append(
            {
                "model": "CatBoostRegressor",
                "fold": fold_number,
                "train_rows": len(train_df),
                "validation_rows": len(validation_df),
                "feature_count": len(feature_columns),
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "r2": metrics["r2"],
                "mape_percent": metrics["mape_percent"],
            }
        )

        prediction_report = build_prediction_report(
            validation_df=validation_df,
            y_true=y_validation,
            y_pred=predictions,
            fold_number=fold_number,
        )
        prediction_report.to_csv(
            predictions_dir / f"fold_{fold_number:02d}_predictions.csv",
            index=False,
        )

        product_metrics = calculate_product_metrics(prediction_report)
        if not product_metrics.empty:
            all_product_metrics.append(product_metrics)

        feature_importance = get_feature_importance(
            preprocessor=preprocessor,
            model=model,
            fold_number=fold_number,
        )
        all_feature_importance.append(feature_importance)

        if save_fold_models:
            model_path = models_dir / f"{MODEL_NAME}_fold_{fold_number:02d}.joblib"
            joblib.dump({"preprocessor": preprocessor, "model": model, "feature_columns": feature_columns}, model_path)

        print(
            f"Fold {fold_number:02d} | "
            f"Train: {len(train_df)} | "
            f"Validation: {len(validation_df)} | "
            f"MAE: {metrics['mae']:.4f} | "
            f"RMSE: {metrics['rmse']:.4f} | "
            f"R2: {metrics['r2']:.4f} | "
            f"MAPE: {metrics['mape_percent']:.2f}%"
        )

    cv_results_df = pd.DataFrame(cv_results)
    cv_summary = summarize_cv_results(cv_results_df)

    average_row = {
        "model": "CatBoostRegressor",
        "fold": "average",
        "train_rows": cv_results_df["train_rows"].mean(),
        "validation_rows": cv_results_df["validation_rows"].mean(),
        "feature_count": cv_results_df["feature_count"].mean(),
        "mae": cv_summary["mae"]["mean"],
        "rmse": cv_summary["rmse"]["mean"],
        "r2": cv_summary["r2"]["mean"],
        "mape_percent": cv_summary["mape_percent"]["mean"],
    }

    cv_results_with_average = pd.concat(
        [cv_results_df, pd.DataFrame([average_row])],
        ignore_index=True,
    )

    cv_results_path = model_report_dir / cv_results_filename
    cv_results_with_average.to_csv(cv_results_path, index=False)

    cv_summary_path = model_report_dir / cv_summary_filename
    save_json(
        {
            "model": "CatBoostRegressor",
            "run_mode": run_mode,
            "random_seed": RANDOM_SEED,
            "n_folds": n_folds,
            "target_column": TARGET_COLUMN,
            "feature_columns": feature_columns,
            "categorical_columns": categorical_columns,
            "metrics_summary": cv_summary,
            "model_parameters": {
                "loss_function": "RMSE",
                "iterations": hyperparameters["iterations"],
                "depth": hyperparameters["depth"],
                "learning_rate": hyperparameters["learning_rate"],
                "l2_leaf_reg": hyperparameters["l2_leaf_reg"],
                "tuning_source": tuning_source,
            },
            "output_files": {
                "cv_results": str(cv_results_path),
                "cv_summary": str(cv_summary_path),
                "feature_importance": str(model_report_dir / "feature_importance.csv"),
                "product_metrics": str(model_report_dir / "product_metrics.csv"),
                "predictions_dir": str(predictions_dir),
            },
        },
        cv_summary_path,
    )

    feature_importance_df = pd.concat(all_feature_importance, ignore_index=True)
    feature_importance_summary = (
        feature_importance_df
        .groupby("feature", as_index=False)
        .agg(
            mean_importance=("importance", "mean"),
            std_importance=("importance", "std"),
            min_importance=("importance", "min"),
            max_importance=("importance", "max"),
        )
        .sort_values("mean_importance", ascending=False)
    )
    feature_importance_summary.to_csv(
        model_report_dir / "feature_importance.csv",
        index=False,
    )

    if all_product_metrics:
        product_metrics_df = pd.concat(all_product_metrics, ignore_index=True)
        product_metrics_df.to_csv(
            model_report_dir / "product_metrics.csv",
            index=False,
        )

    print("\nCatBoost CV raporları oluşturuldu:")
    print(f"- {cv_results_path}")
    print(f"- {cv_summary_path}")
    print(f"- {model_report_dir / 'feature_importance.csv'}")
    print(f"- {model_report_dir / 'product_metrics.csv'}")
    print(f"- {predictions_dir}")

    print("\nOrtalama validation sonucu:")
    print(
        f"MAE: {cv_summary['mae']['mean']:.4f} | "
        f"RMSE: {cv_summary['rmse']['mean']:.4f} | "
        f"R2: {cv_summary['r2']['mean']:.4f} | "
        f"MAPE: {cv_summary['mape_percent']['mean']:.2f}%"
    )

    return cv_results_with_average


def parse_args() -> argparse.Namespace:
    project_root = get_project_root()
    training_root = project_root / "training"

    parser = argparse.ArgumentParser(
        description="CatBoostRegressor için 5-fold validation eğitimi ve detaylı raporlama yapar."
    )

    parser.add_argument(
        "--folds-dir",
        type=Path,
        default=training_root / "data" / "model_splits" / "folds",
        help="Fold train/validation CSV dosyalarının bulunduğu klasör.",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=training_root / "reports",
        help="Raporların kaydedileceği klasör.",
    )

    parser.add_argument(
        "--models-dir",
        type=Path,
        default=training_root / "models" / "raw" / "catboost",
        help="Model dosyalarının kaydedileceği klasör.",
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=training_root / "data" / "model_splits" / "feature_metadata.json",
        help="feature_metadata.json dosya yolu.",
    )

    parser.add_argument(
        "--n-folds",
        type=int,
        default=DEFAULT_N_FOLDS,
        help="Çalıştırılacak fold sayısı.",
    )

    parser.add_argument(
        "--save-fold-models",
        action="store_true",
        help="Her fold için eğitilen modeli models/raw/catboost klasörüne kaydeder.",
    )

    parser.add_argument(
        "--run-mode",
        choices=["baseline", "tuned"],
        default="baseline",
        help=(
            "baseline: sabit baseline parametreleriyle eğitir ve cv_summary_baseline.json yazar. "
            "tuned: selected_hyperparameters.json dosyasından parametre okur ve cv_summary.json yazar."
        ),
    )

    parser.add_argument(
        "--selected-hyperparameters",
        type=Path,
        default=None,
        help=(
            "run-mode=tuned iken kullanılacak JSON dosyası. "
            "Varsayılan: training/reports/catboost/hyperparameter_search/selected_hyperparameters.json"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    train_and_validate_folds(
        folds_dir=args.folds_dir,
        reports_dir=args.reports_dir,
        models_dir=args.models_dir,
        metadata_path=args.metadata,
        n_folds=args.n_folds,
        save_fold_models=args.save_fold_models,
        run_mode=args.run_mode,
        selected_hyperparameters_path=args.selected_hyperparameters,
    )


if __name__ == "__main__":
    main()
