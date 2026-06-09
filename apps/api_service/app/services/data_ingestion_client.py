import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.data_collection_schema import (
    DataCollectionProductCreateRequest,
    DataCollectionRunRequest,
)


class DataIngestionClient:
    def __init__(self):
        self.base_url = settings.data_ingestion_service_url.rstrip("/")

    async def _post(self, path: str, payload):
        try:
            async with httpx.AsyncClient(
                timeout=settings.data_ingestion_request_timeout_seconds
            ) as client:
                response = await client.post(
                    f"{self.base_url}{path}",
                    json=payload.model_dump(mode="json"),
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail = exc.response.json()
            except ValueError:
                pass
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=detail,
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Data ingestion service is unavailable: {exc}",
            ) from exc

    async def run_collection(self, payload: DataCollectionRunRequest):
        return await self._post("/ingestion/run", payload)

    async def create_product(self, payload: DataCollectionProductCreateRequest):
        return await self._post("/ingestion/products", payload)


data_ingestion_client = DataIngestionClient()
