from __future__ import annotations

import joblib 
import numpy as np 
import pandas as pd 

from app.schemas.prediction_schema import DemandFeatureRow 
from app.services.model_loader import LoadedModelBundle 

class PredictionService:

    def __init__(self, bundle: LoadedModelBundle):
        self.bundle = bundle


    def predict_batch(self, items: list[DemandFeatureRow]) -> list[float]:
        rows = [item.model_dump() for item in items]
        frame = pd.DataFrame(rows)

        missing = [
            col for col in self.bundle.feature_columns if col not in frame.columns
        ]
        if missing:
            raise ValueError(f"Eksik feature kolonları: {missing}")

        X = frame[self.bundle.feature_columns].copy()
        predictions = self._ensemble_predict(X)
        return predictions.tolist()


    def _ensemble_predict(self, X: pd.DataFrame) -> np.ndarray:
        all_predictions: list[np.ndarray] = []
        reference_features: list[str] | None = None

        for model_path in self.bundle.model_paths:
            artifact = joblib.load(model_path)

            feature_columns = list(artifact["feature_columns"])
            if reference_features is None:
                reference_features = feature_columns
            elif feature_columns != reference_features:
                raise ValueError("Tüm fold modellerinde feature_columns aynı olmalı.")

            X_subset = X[feature_columns]
            X_transformed = artifact["preprocessor"].transform(X_subset)
            preds = artifact["model"].predict(X_transformed)
            all_predictions.append(np.asarray(preds, dtype=float))

        return np.mean(np.stack(all_predictions, axis=0), axis=0)
    