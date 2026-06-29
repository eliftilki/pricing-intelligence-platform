from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TRAINING_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = TRAINING_ROOT / "models" / "raw" / "catboost"
OUTPUT_DIR = TRAINING_ROOT / "reports" / "feature_importance"
TOP_N_FEATURES = 20


def load_artifact(path: Path) -> tuple:
    artifact = joblib.load(path)

    if isinstance(artifact, dict) and "preprocessor" in artifact and "model" in artifact:
        return artifact["preprocessor"], artifact["model"]

    if hasattr(artifact, "named_steps"):
        return artifact.named_steps["preprocessor"], artifact.named_steps["model"]

    raise ValueError(f"Desteklenmeyen model formatı: {path}")


def get_feature_importance(preprocessor, model) -> tuple[list[str], np.ndarray]:
    importances = np.asarray(model.feature_importances_, dtype=float)

    try:
        feature_names = list(preprocessor.get_feature_names_out())
    except Exception:
        feature_names = [f"feature_{index}" for index in range(len(importances))]

    if len(feature_names) != len(importances):
        raise ValueError(
            f"Feature sayısı uyuşmuyor: {len(feature_names)} isim, {len(importances)} importance"
        )

    return feature_names, importances


def discover_fold_models(models_dir: Path) -> list[Path]:
    model_paths = sorted(models_dir.glob("catboost_fold_*.joblib"))
    if not model_paths:
        raise FileNotFoundError(
            f"Model bulunamadı: {models_dir}\n"
            "Önce şunu çalıştır: python scripts/train_catboost.py --save-fold-models"
        )
    return model_paths


def build_importance_table(model_paths: list[Path]) -> pd.DataFrame:
    fold_frames: list[pd.DataFrame] = []

    for fold_idx, model_path in enumerate(model_paths, start=1):
        print(f"Fold {fold_idx}: {model_path.name}")
        preprocessor, model = load_artifact(model_path)
        feature_names, importances = get_feature_importance(preprocessor, model)

        fold_frames.append(
            pd.DataFrame(
                {
                    "feature": feature_names,
                    f"fold_{fold_idx}_importance": importances,
                }
            )
        )

    importance_df = fold_frames[0]
    for fold_df in fold_frames[1:]:
        importance_df = importance_df.merge(fold_df, on="feature", how="inner")

    fold_cols = [col for col in importance_df.columns if col.startswith("fold_")]
    importance_df["mean_importance"] = importance_df[fold_cols].mean(axis=1)
    importance_df["std_importance"] = importance_df[fold_cols].std(axis=1)

    return importance_df.sort_values("mean_importance", ascending=False).reset_index(drop=True)


def save_results(importance_df: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "feature_importance_5fold.csv"
    importance_df.to_csv(csv_path, index=False)

    plot_df = (
        importance_df.head(TOP_N_FEATURES)
        .sort_values("mean_importance", ascending=True)
    )

    plt.figure(figsize=(10, 8))
    plt.barh(plot_df["feature"], plot_df["mean_importance"])
    plt.xlabel("Ortalama Feature Importance")
    plt.ylabel("Feature")
    plt.title("5 Fold Ortalama Feature Importance")
    plt.tight_layout()

    plot_path = output_dir / "feature_importance_5fold.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()

    return csv_path, plot_path


def main() -> None:
    model_paths = discover_fold_models(MODELS_DIR)
    print(f"{len(model_paths)} fold modeli bulundu.\n")

    importance_df = build_importance_table(model_paths)
    csv_path, plot_path = save_results(importance_df, OUTPUT_DIR)

    print("\nEn önemli 10 feature:")
    print(importance_df[["feature", "mean_importance", "std_importance"]].head(10).to_string(index=False))
    print(f"\nCSV: {csv_path}")
    print(f"Grafik: {plot_path}")


if __name__ == "__main__":
    main()
