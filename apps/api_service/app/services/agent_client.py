import asyncio
import logging
from uuid import UUID

import httpx
from app.core.config import settings
from app.schemas.analysis_schema import RunAnalysisRequest

logger = logging.getLogger(__name__)


class AgentClient:
    def __init__(self):
        self.base_url = settings.agent_service_url
        self.timeout_intelligence = httpx.Timeout(60.0, connect=10.0, read=60.0, write=10.0, pool=10.0)

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
                    raise
            except Exception as e:
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

        raise last_exception

    async def run_intelligence(self, session_id: UUID, product_id: UUID) -> dict:
        return await self._request_with_retry(
            "POST",
            f"{self.base_url}/competitor-intelligence/run",
            {
                "session_id": str(session_id),
                "product_id": str(product_id),
            },
            self.timeout_intelligence,
            max_retries=3,
        )

    async def run_analysis(self, payload: RunAnalysisRequest):
        async with httpx.AsyncClient(timeout=settings.agent_request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.agent_service_url}/analysis/run",
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            return response.json()


agent_client = AgentClient()
