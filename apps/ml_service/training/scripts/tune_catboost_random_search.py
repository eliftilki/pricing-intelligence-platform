from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer

# train_catboost.py ile aynı klasörde olduğu için import edilebilir
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from train_catboost import (  # noqa: E402
    DEFAULT_N_FOLDS,
    RANDOM_SEED,
    evaluate_predictions,
    get_categorical_columns,
    get_feature_columns,
    get_project_root,
    load_json,
    make_one_hot_encoder,
    prepare_xy,
    save_json,
)

# --- Arama uzayı (1. tur) ---
DEPTH_MIN = 3
DEPTH_MAX = 7
LEARNING_RATE_MIN = 0.02
LEARNING_RATE_MAX = 0.2
ITERATIONS_MIN = 100
ITERATIONS_MAX = 600
L2_LEAF_REG_MIN = 1.0
L2_LEAF_REG_MAX = 10.0

DEFAULT_N_TRIALS = 30
DEFAULT_LOSS_FUNCTION = "RMSE"
PRIMARY_METRIC = "mae"

RESULT_COLUMNS = [
    "trial_id",
    "status",
    "duration_seconds",
    "depth",
    "learning_rate",
    "iterations",
    "l2_leaf_reg",
    "mae_fold_01",
    "mae_fold_02",
    "mae_fold_03",
    "mae_fold_04",
    "mae_fold_05",
    "mae_mean",
    "mae_std",
    "rmse_mean",
    "r2_mean",
    "mae_improvement_vs_baseline",
    "is_best_trial",
]


def default_parameter_ranges() -> Dict[str, Dict[str, Any]]:
    """1. tur varsayılan hiperparametre aralıkları."""
    return {
        "depth": {"min": DEPTH_MIN, "max": DEPTH_MAX, "sampling": "uniform_int"},
        "learning_rate": {
            "min": LEARNING_RATE_MIN,
            "max": LEARNING_RATE_MAX,
            "sampling": "log_uniform",
        },
        "iterations": {
            "min": ITERATIONS_MIN,
            "max": ITERATIONS_MAX,
            "sampling": "uniform_int",
        },
        "l2_leaf_reg": {
            "min": L2_LEAF_REG_MIN,
            "max": L2_LEAF_REG_MAX,
            "sampling": "log_uniform",
        },
    }


def load_parameter_ranges(ranges_path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """JSON dosyasından veya varsayılanlardan parametre aralıklarını yükler."""
    if ranges_path is None:
        return default_parameter_ranges()

    if not ranges_path.exists():
        raise FileNotFoundError(f"Parametre aralıkları dosyası bulunamadı: {ranges_path}")

    loaded = load_json(ranges_path)
    if not loaded:
        raise ValueError(f"Geçersiz parametre aralıkları dosyası: {ranges_path}")

    required_params = ("depth", "learning_rate", "iterations", "l2_leaf_reg")
    for param in required_params:
        if param not in loaded or "min" not in loaded[param] or "max" not in loaded[param]:
            raise ValueError(
                f"Parametre aralıkları dosyasında eksik alan: {param} (min/max gerekli)"
            )

    return loaded


def sample_hyperparameters(
    rng: np.random.Generator,
    parameter_ranges: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Random Search için hiperparametre örnekleme."""
    depth_range = parameter_ranges["depth"]
    learning_rate_range = parameter_ranges["learning_rate"]
    iterations_range = parameter_ranges["iterations"]
    l2_range = parameter_ranges["l2_leaf_reg"]

    return {
        "depth": int(rng.integers(depth_range["min"], depth_range["max"] + 1)),
        "learning_rate": float(
            10
            ** rng.uniform(
                np.log10(learning_rate_range["min"]),
                np.log10(learning_rate_range["max"]),
            )
        ),
        "iterations": int(
            rng.integers(iterations_range["min"], iterations_range["max"] + 1)
        ),
        "l2_leaf_reg": float(
            10
            ** rng.uniform(
                np.log10(l2_range["min"]),
                np.log10(l2_range["max"]),
            )
        ),
    }


def build_catboost_model(
    feature_columns: List[str],
    categorical_columns: List[str],
    hyperparameters: Dict[str, Any],
    loss_function: str = DEFAULT_LOSS_FUNCTION,
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
        loss_function=loss_function,
        iterations=int(hyperparameters["iterations"]),
        depth=int(hyperparameters["depth"]),
        learning_rate=float(hyperparameters["learning_rate"]),
        l2_leaf_reg=float(hyperparameters["l2_leaf_reg"]),
        random_seed=RANDOM_SEED,
        verbose=False,
        allow_writing_files=False,
    )

    return preprocessor, model


def load_baseline_mae(cv_summary_path: Path) -> float:
    """
    Sabit parametreli referans CV sonucundan baseline MAE okur.

    Varsayılan kaynak: reports/catboost/cv_summary_baseline.json
    """
    if not cv_summary_path.exists():
        raise FileNotFoundError(
            f"Baseline cv_summary dosyası bulunamadı: {cv_summary_path}\n"
            "reports/catboost/cv_summary_baseline.json dosyasının mevcut olduğundan emin olun."
        )

    cv_summary = load_json(cv_summary_path)
    if not cv_summary or "metrics_summary" not in cv_summary:
        raise ValueError(
            f"Geçersiz cv_summary dosyası (metrics_summary eksik): {cv_summary_path}"
        )

    return float(cv_summary["metrics_summary"]["mae"]["mean"])


def run_single_trial(
    trial_id: int,
    hyperparameters: Dict[str, Any],
    folds_dir: Path,
    n_folds: int,
    feature_columns: List[str],
    categorical_columns: List[str],
    loss_function: str,
    baseline_mae: float,
) -> Dict[str, Any]:
    trial_started = time.perf_counter()
    fold_mae_values: List[float] = []
    fold_rmse_values: List[float] = []
    fold_r2_values: List[float] = []

    try:
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

            preprocessor, model = build_catboost_model(
                feature_columns=feature_columns,
                categorical_columns=categorical_columns,
                hyperparameters=hyperparameters,
                loss_function=loss_function,
            )

            X_train_transformed = preprocessor.fit_transform(X_train)
            X_validation_transformed = preprocessor.transform(X_validation)

            model.fit(X_train_transformed, y_train)
            predictions = model.predict(X_validation_transformed)
            metrics = evaluate_predictions(y_validation, predictions)

            fold_mae_values.append(metrics["mae"])
            fold_rmse_values.append(metrics["rmse"])
            fold_r2_values.append(metrics["r2"])

        mae_mean = float(np.mean(fold_mae_values))
        mae_std = float(np.std(fold_mae_values, ddof=0))

        row: Dict[str, Any] = {
            "trial_id": trial_id,
            "status": "completed",
            "duration_seconds": round(time.perf_counter() - trial_started, 2),
            "depth": int(hyperparameters["depth"]),
            "learning_rate": float(hyperparameters["learning_rate"]),
            "iterations": int(hyperparameters["iterations"]),
            "l2_leaf_reg": float(hyperparameters["l2_leaf_reg"]),
            "mae_fold_01": fold_mae_values[0],
            "mae_fold_02": fold_mae_values[1],
            "mae_fold_03": fold_mae_values[2],
            "mae_fold_04": fold_mae_values[3],
            "mae_fold_05": fold_mae_values[4],
            "mae_mean": mae_mean,
            "mae_std": mae_std,
            "rmse_mean": float(np.mean(fold_rmse_values)),
            "r2_mean": float(np.mean(fold_r2_values)),
            "mae_improvement_vs_baseline": float(baseline_mae - mae_mean),
            "is_best_trial": False,
        }
        return row

    except Exception as exc:
        return {
            "trial_id": trial_id,
            "status": "failed",
            "duration_seconds": round(time.perf_counter() - trial_started, 2),
            "depth": hyperparameters.get("depth"),
            "learning_rate": hyperparameters.get("learning_rate"),
            "iterations": hyperparameters.get("iterations"),
            "l2_leaf_reg": hyperparameters.get("l2_leaf_reg"),
            "mae_fold_01": np.nan,
            "mae_fold_02": np.nan,
            "mae_fold_03": np.nan,
            "mae_fold_04": np.nan,
            "mae_fold_05": np.nan,
            "mae_mean": np.nan,
            "mae_std": np.nan,
            "rmse_mean": np.nan,
            "r2_mean": np.nan,
            "mae_improvement_vs_baseline": np.nan,
            "is_best_trial": False,
            "_error": str(exc),
        }


def mark_best_trial(results_df: pd.DataFrame) -> pd.DataFrame:
    results_df = results_df.copy()
    results_df["is_best_trial"] = False

    completed_mask = results_df["status"] == "completed"
    if not completed_mask.any():
        return results_df

    best_index = results_df.loc[completed_mask, "mae_mean"].idxmin()
    results_df.loc[best_index, "is_best_trial"] = True
    return results_df


def save_trial_results(trial_rows: List[Dict[str, Any]], output_path: Path) -> pd.DataFrame:
    """Her trial sonrası ara kayıt; kesinti durumunda tamamlanan trial'lar korunur."""
    results_df = pd.DataFrame(trial_rows)
    results_df = mark_best_trial(results_df)
    results_df = results_df[RESULT_COLUMNS]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_path, index=False)
    return results_df


def run_random_search(
    folds_dir: Path,
    output_dir: Path,
    metadata_path: Path,
    cv_summary_path: Path,
    n_trials: int,
    n_folds: int,
    loss_function: str,
    random_seed: int,
    parameter_ranges_path: Optional[Path] = None,
) -> pd.DataFrame:
    metadata = load_json(metadata_path)
    baseline_mae = load_baseline_mae(cv_summary_path)
    parameter_ranges = load_parameter_ranges(parameter_ranges_path)

    first_train_path = folds_dir / "fold_01_train.csv"
    if not first_train_path.exists():
        raise FileNotFoundError(f"İlk fold train dosyası bulunamadı: {first_train_path}")

    first_train_df = pd.read_csv(first_train_path)
    feature_columns = get_feature_columns(first_train_df, metadata)
    categorical_columns = get_categorical_columns(feature_columns, metadata)

    output_dir.mkdir(parents=True, exist_ok=True)

    save_json(
        {
            "search_type": "random_search",
            "primary_metric": PRIMARY_METRIC,
            "loss_function": loss_function,
            "random_seed": random_seed,
            "n_trials": n_trials,
            "n_folds": n_folds,
            "baseline_mae_mean": baseline_mae,
            "cv_summary_path": str(cv_summary_path),
            "parameter_ranges_path": str(parameter_ranges_path)
            if parameter_ranges_path
            else None,
            "parameter_ranges": parameter_ranges,
        },
        output_dir / "search_config.json",
    )

    rng = np.random.default_rng(random_seed)
    trial_rows: List[Dict[str, Any]] = []
    output_path = output_dir / "random_search_trials.csv"

    print(f"\nCatBoost Random Search başlıyor")
    print(f"Trial sayısı: {n_trials}")
    print(f"Fold sayısı: {n_folds}")
    print(f"Baseline MAE: {baseline_mae:.6f}")
    print(f"Parametre aralıkları: {parameter_ranges_path or 'varsayılan (1. tur)'}")
    print(f"Çıktı klasörü: {output_dir}\n")

    for trial_id in range(1, n_trials + 1):
        hyperparameters = sample_hyperparameters(rng, parameter_ranges)
        print(
            f"Trial {trial_id:02d}/{n_trials} | "
            f"depth={hyperparameters['depth']} | "
            f"lr={hyperparameters['learning_rate']:.4f} | "
            f"iter={hyperparameters['iterations']} | "
            f"l2={hyperparameters['l2_leaf_reg']:.4f}"
        )

        row = run_single_trial(
            trial_id=trial_id,
            hyperparameters=hyperparameters,
            folds_dir=folds_dir,
            n_folds=n_folds,
            feature_columns=feature_columns,
            categorical_columns=categorical_columns,
            loss_function=loss_function,
            baseline_mae=baseline_mae,
        )

        if row.get("_error"):
            print(f"  -> FAILED: {row['_error']}")
            row.pop("_error", None)
        else:
            print(
                f"  -> MAE mean={row['mae_mean']:.4f} | "
                f"improvement={row['mae_improvement_vs_baseline']:.4f} | "
                f"duration={row['duration_seconds']}s"
            )

        trial_rows.append(row)
        save_trial_results(trial_rows, output_path)

    results_df = save_trial_results(trial_rows, output_path)

    print(f"\nRandom Search tamamlandı.")
    print(f"- {output_path}")
    print(f"- {output_dir / 'search_config.json'}")

    best_rows = results_df[results_df["is_best_trial"]]
    if not best_rows.empty:
        best_row = best_rows.iloc[0]
        print("\nEn iyi trial:")
        print(
            f"trial_id={int(best_row['trial_id'])} | "
            f"mae_mean={best_row['mae_mean']:.4f} | "
            f"depth={int(best_row['depth'])} | "
            f"lr={best_row['learning_rate']:.4f} | "
            f"iter={int(best_row['iterations'])} | "
            f"l2={best_row['l2_leaf_reg']:.4f}"
        )

    return results_df


def parse_args() -> argparse.Namespace:
    project_root = get_project_root()
    training_root = project_root / "training"

    parser = argparse.ArgumentParser(
        description="CatBoost için Random Search hyperparameter tuning."
    )
    parser.add_argument(
        "--folds-dir",
        type=Path,
        default=training_root / "data" / "model_splits" / "folds",
        help="Fold train/validation CSV dosyalarının bulunduğu klasör.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=training_root / "data" / "model_splits" / "feature_metadata.json",
        help="feature_metadata.json dosya yolu.",
    )
    parser.add_argument(
        "--cv-summary",
        type=Path,
        default=training_root / "reports" / "catboost" / "cv_summary_baseline.json",
        help="Baseline MAE kaynağı: sabit parametreli cv_summary_baseline.json.",
    )
    parser.add_argument(
        "--parameter-ranges",
        type=Path,
        default=None,
        help="Daraltılmış aralıklar JSON dosyası (derive_refined_search_space.py çıktısı).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=training_root / "reports" / "catboost" / "hyperparameter_search",
        help="Random Search çıktılarının kaydedileceği klasör.",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=DEFAULT_N_TRIALS,
        help="Çalıştırılacak trial sayısı.",
    )
    parser.add_argument(
        "--n-folds",
        type=int,
        default=DEFAULT_N_FOLDS,
        help="Cross-validation fold sayısı.",
    )
    parser.add_argument(
        "--loss-function",
        type=str,
        default=DEFAULT_LOSS_FUNCTION,
        help="CatBoost loss_function (1. tur için RMSE önerilir).",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=RANDOM_SEED,
        help="Hem model hem parametre örnekleme için seed.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_random_search(
        folds_dir=args.folds_dir,
        output_dir=args.output_dir,
        metadata_path=args.metadata,
        cv_summary_path=args.cv_summary,
        n_trials=args.n_trials,
        n_folds=args.n_folds,
        loss_function=args.loss_function,
        random_seed=args.random_seed,
        parameter_ranges_path=args.parameter_ranges,
    )


if __name__ == "__main__":
    main()