from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.schemas.demand_prediction_schema import (
    DemandPredictionRequest,
    DemandPredictionResponse,
    DemandPredictionResult,
)
from app.services.demand_prediciton_builder import (
    DemandPredictionBuildContext,
    DemandPredictionBuilder,
)
from app.services.demand_prediction_client import (
    DemandPredictionClient,
    demand_prediction_client,
)


@dataclass(frozen=True)
class DemandPredictionServiceResult:
    """
    ML tahmin ciktisi + optimization_node'un state'e yazacagi ozet liste.
    """

    predictions: list[dict[str, float]]
    model_name: str
    n_fold_models: int
    ensemble_strategy: str

    def to_state(self) -> dict:
        """Graph state'e yazilacak alanlar."""
        return {
            "demand_predictions": self.predictions,
            "demand_prediction_meta": {
                "model_name": self.model_name,
                "n_fold_models": self.n_fold_models,
                "ensemble_strategy": self.ensemble_strategy,
            },
        }


class DemandPredictionService:
    """
    Demand prediction orkestratoru.

    Akis:
      1. DemandPredictionBuilder  -> ML feature satirlari
      2. DemandPredictionClient   -> POST /predictions/demand
      3. Cevap                    -> optimization formatina map

    DB veya graph state ile dogrudan calismaz; node ince adaptordur.
    """

    def __init__(
        self,
        builder: DemandPredictionBuilder | None = None,
        client: DemandPredictionClient | None = None,
    ) -> None:
        self._builder = builder or DemandPredictionBuilder()
        self._client = client or demand_prediction_client

        def predict(
            self,
            context: DemandPredictionBuildContext,
        ) -> DemandPredictionServiceResult:
            request = self._builder.build_request(context)

            try:
                response = self._client.predict_demand(request)
            except httpx.HTTPError as exc:
                raise DemandPredictionServiceError(
                    f"ML demand prediction request failed: {exc}"
                ) from exc

            predictions = self._map_to_optimization_items(request, response.predictions)

            return DemandPredictionServiceResult(
                predictions=predictions,
                model_name=response.model_name,
                n_fold_models=response.n_fold_models,
                ensemble_strategy=response.ensemble_strategy,
            )

    @staticmethod
    def _map_to_optimization_items(
        request: DemandPredictionRequest,
        ml_predictions: list[DemandPredictionResult],
    ) -> list[dict[str, float]]:
        # optimization_node sadece {price, expected_sales} bekler; ML meta bilgisi burada dusulur.
        if len(ml_predictions) != len(request.items):
            raise DemandPredictionServiceError(
                "ML service returned a different number of predictions than requested "
                f"({len(ml_predictions)} != {len(request.items)})."
            )

        items: list[dict[str, float]] = []
        for feature_row, prediction in zip(request.items, ml_predictions, strict=True):
            expected_price = float(prediction.candidate_price)
            requested_price = float(feature_row.candidate_price)

            if abs(expected_price - requested_price) > 0.01:
                raise DemandPredictionServiceError(
                    "ML prediction candidate_price does not match request item: "
                    f"{expected_price} != {requested_price}."
                )

            expected_sales = float(prediction.expected_sales)
            if expected_sales < 0:
                raise DemandPredictionServiceError(
                    f"ML service returned negative expected_sales for price {requested_price}."
                )

            items.append(
                {
                    "price": requested_price,
                    "expected_sales": expected_sales,
                }
            )

        return items


class DemandPredictionServiceError(RuntimeError):
    """Builder, ML client veya cevap dogrulama hatalari."""


demand_prediction_service = DemandPredictionService()
