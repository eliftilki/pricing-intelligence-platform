import httpx

from app.core.config import settings
from app.schemas.demand_prediction_schema import (
    DemandPredictionRequest,
    DemandPredictionResponse,
)


class DemandPredictionClient:
    def __init__(self) -> None:
        self.base_url = settings.ml_service_url.rstrip("/")
        self.timeout = settings.ml_prediction_timeout_seconds

    def predict_demand(
        self,
        request: DemandPredictionRequest,
    ) -> DemandPredictionResponse:
        url = f"{self.base_url}/predictions/demand"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                json=request.model_dump(),
            )

        response.raise_for_status()

        return DemandPredictionResponse(**response.json())


demand_prediction_client = DemandPredictionClient()