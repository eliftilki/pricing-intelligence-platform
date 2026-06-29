from __future__ import annotations

import json 
from dataclasses import dataclass 
from pathlib import Path 
from typing import Any 

import joblib 

@dataclass
class LoadedModelBundle:
    model_paths: list[Path]
    feature_columns: list[str]
    metadata: dict[str, Any]


def load_feature_metadata(metadata_path: Path) -> dict[str, Any]:
    with metadata_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_feature_columns(metadata: dict[str, Any]) -> list[str]:
    if "feature_columns" in metadata:
        return list(metadata["feature_columns"])
    if "feature_cols" in metadata:
        return list(metadata["feature_cols"])
    raise ValueError("feature_metadata.json içinde feature listesi bulunamadı.")


def discover_fold_models(models_dir: Path, model_name: str) -> list[Path]:
    paths = sorted(models_dir.glob(f"{model_name}_fold_*.joblib"))
    if not paths:
        raise FileNotFoundError(
            f"Model dosyası bulunamadı: {models_dir}. "
            f"Beklenen: {model_name}_fold_01.joblib ..."
        )
    return paths


def load_model_bundle(
    models_dir: Path,
    metadata_path: Path,
    model_name: str,
) -> LoadedModelBundle:
    metadata = load_feature_metadata(metadata_path)
    feature_columns = get_feature_columns(metadata)
    model_paths = discover_fold_models(models_dir, model_name)

    first_artifact = joblib.load(model_paths[0])
    if "preprocessor" not in first_artifact or "model" not in first_artifact:
        raise ValueError(f"Desteklenmeyen model formatı: {model_paths[0]}")

    return LoadedModelBundle(
        model_paths=model_paths,
        feature_columns=feature_columns,
        metadata=metadata,
    )