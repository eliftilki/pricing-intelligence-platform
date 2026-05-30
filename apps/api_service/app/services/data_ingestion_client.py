import httpx
from app.core.config import settings
from app.schemas.data_collection_schema import DataCollectionRunRequest


class DataIngestionClient:
    def __init__(self):
        self.base_url = settings.data_ingestion_service_url

    async def run_collection(self, payload: DataCollectionRunRequest) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/ingestion/run",
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            return response.json()


data_ingestion_client = DataIngestionClient()