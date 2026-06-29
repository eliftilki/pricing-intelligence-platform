import asyncio
import logging

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.data_ingestion_schema import (
    DataIngestionRunRequest,
    DataIngestionRunResponse,
    DataIngestionSearchAndRunRequest,
)


logger = logging.getLogger(__name__)


class DataIngestionClientError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DataIngestionClient:
    def __init__(self) -> None:
        self.base_url = settings.data_ingestion_service_url.rstrip("/")
        self.timeout = httpx.Timeout(
            settings.data_ingestion_request_timeout_seconds,
            connect=min(10.0, settings.data_ingestion_request_timeout_seconds),
            read=settings.data_ingestion_request_timeout_seconds,
            write=10.0,
            pool=10.0,
        )
        self.max_retries = settings.data_ingestion_max_retries

    async def run_ingestion(
        self,
        request: DataIngestionRunRequest | DataIngestionSearchAndRunRequest,
    ) -> DataIngestionRunResponse:
        if isinstance(request, DataIngestionSearchAndRunRequest):
            path = "/ingestion/search-and-run"
        else:
            path = "/ingestion/run"

        payload = await self._post_with_retry(
            path=path,
            json_payload=request.model_dump(mode="json"),
        )

        try:
            return DataIngestionRunResponse.model_validate(payload)
        except ValidationError as exc:
            raise DataIngestionClientError(
                code="DATA_INGESTION_INVALID_RESPONSE",
                message="Data ingestion service returned an invalid response.",
            ) from exc

    async def _post_with_retry(self, path: str, json_payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        max_attempts = self.max_retries + 1

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=json_payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                retryable = exc.response.status_code >= 500
                if retryable and attempt < max_attempts:
                    await self._wait_before_retry(attempt, path)
                    continue

                raise DataIngestionClientError(
                    code="DATA_INGESTION_HTTP_ERROR",
                    message=(
                        "Data ingestion service request failed with HTTP "
                        f"{exc.response.status_code}."
                    ),
                ) from exc
            except httpx.TimeoutException as exc:
                if attempt < max_attempts:
                    await self._wait_before_retry(attempt, path)
                    continue

                raise DataIngestionClientError(
                    code="DATA_INGESTION_TIMEOUT",
                    message="Data ingestion service request timed out.",
                ) from exc
            except httpx.RequestError as exc:
                if attempt < max_attempts:
                    await self._wait_before_retry(attempt, path)
                    continue

                raise DataIngestionClientError(
                    code="DATA_INGESTION_UNAVAILABLE",
                    message="Data ingestion service is unavailable.",
                ) from exc
            except ValueError as exc:
                raise DataIngestionClientError(
                    code="DATA_INGESTION_INVALID_RESPONSE",
                    message="Data ingestion service returned non-JSON content.",
                ) from exc

        raise DataIngestionClientError(
            code="DATA_INGESTION_UNAVAILABLE",
            message="Data ingestion service request failed.",
        )

    async def _wait_before_retry(self, attempt: int, path: str) -> None:
        wait_seconds = min(2 ** (attempt - 1), 4)
        logger.warning(
            "Data ingestion request failed; retrying: path=%s attempt=%d wait=%ds",
            path,
            attempt,
            wait_seconds,
        )
        await asyncio.sleep(wait_seconds)


data_ingestion_client = DataIngestionClient()
