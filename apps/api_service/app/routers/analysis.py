from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.analysis_schema import RunAnalysisRequest, RunAnalysisResponse
from app.schemas.data_collection_schema import DataCollectionRunRequest
from app.services.agent_client import agent_client
from app.services.data_ingestion_client import data_ingestion_client

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=RunAnalysisResponse)
async def run_analysis(payload: RunAnalysisRequest):
    # Adım 1: Veri çekme
    ingestion_result = await data_ingestion_client.run_collection(
        DataCollectionRunRequest(
            product_id=payload.product_id,
            marketplaces=payload.marketplaces,
        )
    )

    session_id = UUID(str(ingestion_result["job_id"]))

    # Adım 2: Rakip analizi
    intelligence = await agent_client.run_intelligence(
        session_id=session_id,
        product_id=payload.product_id,
    )

    return RunAnalysisResponse(
        session_id=session_id,
        product_id=payload.product_id,
        ingestion_status=ingestion_result["status"],
        scrape_counts=ingestion_result.get("scrape_counts", {}),
        total_competitors=intelligence.get("total_competitors", 0),
        price_range=intelligence.get("price_range", {}),
        recommendation=intelligence.get("recommendation", {}),
        competitors=intelligence.get("competitors", []),
    )
