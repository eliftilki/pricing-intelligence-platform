import httpx
from app.core.config import settings
from app.schemas.analysis_schema import RunAnalysisRequest


class AgentClient:
    async def run_analysis(self, payload: RunAnalysisRequest):
        async with httpx.AsyncClient(timeout=settings.agent_request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.agent_service_url}/analysis/run",
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            return response.json()


agent_client = AgentClient()
