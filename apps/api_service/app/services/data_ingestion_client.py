import asyncio
import logging

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.data_collection_schema import (
    DataCollectionProductCreateRequest,
    DataCollectionRunRequest,
)

logger = logging.getLogger(__name__)


class DataIngestionClient:
    def __init__(self):
        self.base_url = settings.data_ingestion_service_url
        self.timeout_run = httpx.Timeout(180.0, connect=10.0, read=180.0, write=10.0, pool=10.0)
        self.timeout_create = httpx.Timeout(30.0, connect=10.0, read=30.0, write=10.0, pool=10.0)

    async def _request_with_retry(
        self, method: str, url: str, json_payload: dict, timeout: httpx.Timeout, max_retries: int = 3
    ) -> dict:
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, json=json_payload)
                    response.raise_for_status()
                    return response.json()
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{max_retries} for {method} {url}, "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} retries exhausted for {url}: {type(e).__name__}")
                    raise HTTPException(status_code=503, detail=f"Data ingestion service timeout: {e}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    last_exception = e
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Server error {e.response.status_code} on attempt {attempt + 1}/{max_retries}, "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise HTTPException(
                        status_code=e.response.status_code,
                        detail=e.response.text,
                    ) from e
            except httpx.RequestError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Error on attempt {attempt + 1}/{max_retries}: {type(e).__name__}, "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} retries exhausted: {type(e).__name__}: {e}")
                    raise HTTPException(status_code=503, detail=f"Data ingestion service is unavailable: {e}")

        raise last_exception

    async def run_collection(self, payload: DataCollectionRunRequest) -> dict:
        return await self._request_with_retry(
            "POST",
            f"{self.base_url}/ingestion/run",
            payload.model_dump(mode="json"),
            self.timeout_run,
            max_retries=3,
        )

    async def create_product(self, payload: DataCollectionProductCreateRequest) -> dict:
        return await self._request_with_retry(
            "POST",
            f"{self.base_url}/ingestion/products",
            payload.model_dump(mode="json"),
            self.timeout_create,
            max_retries=2,
        )


data_ingestion_client = DataIngestionClient()
