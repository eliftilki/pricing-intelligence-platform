import httpx

from app.core.config import settings
from app.schemas.slm_explanation_schema import (
    SLMExplanationRequest,
    SLMExplanationResponse,
)


class SLMExplanationClient:
    def __init__(self) -> None:
        self.base_url = settings.slm_service_url.rstrip("/")
        self.timeout = settings.slm_explanation_timeout_seconds

    async def generate_explanation(
        self,
        request: SLMExplanationRequest,
    ) -> SLMExplanationResponse:
        url = f"{self.base_url}/explanations/generate"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=request.model_dump(),
            )

        response.raise_for_status()

        return SLMExplanationResponse(**response.json())


slm_explanation_client = SLMExplanationClient()