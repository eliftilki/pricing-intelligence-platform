from fastapi import APIRouter
from app.schemas.analysis_schema import RunAnalysisRequest, RunAnalysisResponse
from app.services.agent_client import agent_client

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.post("/run", response_model=RunAnalysisResponse)
async def run_analysis(payload: RunAnalysisRequest):
    return await agent_client.run_analysis(payload)
