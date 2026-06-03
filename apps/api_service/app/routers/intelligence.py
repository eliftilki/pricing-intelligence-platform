from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.data_collection_schema import DataCollectionRunRequest
from app.schemas.intelligence_schema import (
    IntelligenceRunRequest,
    ProductSetupRequest,
    ProductSetupResponse,
)
from app.services.agent_client import agent_client
from app.services.data_ingestion_client import data_ingestion_client

router = APIRouter(prefix="/api/v1", tags=["Intelligence"])


@router.post("/products", response_model=ProductSetupResponse)
async def setup_product(payload: ProductSetupRequest):
    result = await data_ingestion_client.create_product(payload)
    return ProductSetupResponse(
        product_id=result["product_id"],
        seller_product_ids={k: UUID(v) for k, v in result["seller_product_ids"].items()},
    )


@router.post("/intelligence/run")
async def run_intelligence(payload: IntelligenceRunRequest):
    ingestion_payload = DataCollectionRunRequest(
        product_id=payload.product_id,
        seller_product_id=payload.product_id,
        marketplaces=payload.marketplaces,
    )
    ingestion_result = await data_ingestion_client.run_collection(ingestion_payload)

    if ingestion_result.get("status") == "FAILED":
        raise HTTPException(
            status_code=422,
            detail=ingestion_result.get("message", "Veri toplama basarisiz."),
        )

    session_id = ingestion_result.get("job_id")
    if not session_id:
        raise HTTPException(status_code=500, detail="Ingestion service session_id dondurmedi.")

    analysis = await agent_client.run_intelligence(
        session_id=UUID(session_id),
        product_id=payload.product_id,
    )
    analysis["ingestion_summary"] = {
        "status": ingestion_result.get("status"),
        "scrape_counts": ingestion_result.get("scrape_counts", {}),
        "message": ingestion_result.get("message"),
    }
    return analysis
