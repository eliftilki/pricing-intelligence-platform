from uuid import UUID

import httpx

from app.core.config import settings


class AgentClient:
    def __init__(self):
        self.base_url = settings.agent_service_url

    async def run_intelligence(self, session_id: UUID, product_id: UUID) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/competitor-intelligence/run",
                json={
                    "session_id": str(session_id),
                    "product_id": str(product_id),
                },
            )
            response.raise_for_status()
            return response.json()


agent_client = AgentClient()
