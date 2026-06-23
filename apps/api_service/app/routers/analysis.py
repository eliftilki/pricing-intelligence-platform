from uuid import UUID

from fastapi import APIRouter

from app.schemas.analysis_schema import (
    RunAnalysisRequest,
    RunAnalysisResponse,
    RunProductAnalysisRequest,
)
from app.schemas.data_collection_schema import (
    DataCollectionRunRequest,
    DataCollectionSearchAndRunRequest,
)
from app.services.agent_client import agent_client
from app.services.data_ingestion_client import data_ingestion_client

router = APIRouter(prefix="/analysis", tags=["Analysis"])


async def build_analysis_response(product_id: UUID, ingestion_result: dict) -> RunAnalysisResponse:
    session_id = UUID(str(ingestion_result["job_id"]))

    intelligence = await agent_client.run_intelligence(
        session_id=session_id,
        product_id=product_id,
    )
    recommendation = intelligence.get("recommendation") or {}

    return RunAnalysisResponse(
        session_id=session_id,
        product_id=product_id,
        ingestion_status=ingestion_result["status"],
        scrape_counts=ingestion_result.get("scrape_counts", {}),
        total_competitors=intelligence.get("total_competitors", 0),
        price_range=intelligence.get("price_range", {}),
        recommendation={
            "suggested_price": recommendation.get("suggested_price"),
            "strategy": recommendation.get("strategy", "INSUFFICIENT_DATA"),
            "confidence": recommendation.get("confidence", 0),
            "rationale": recommendation.get(
                "rationale",
                "Analiz icin yeterli rakip verisi bulunamadi.",
            ),
        },
        competitors=intelligence.get("competitors", []),
    )


@router.post("/run", response_model=RunAnalysisResponse)
async def run_analysis(payload: RunAnalysisRequest):
    if payload.company_id and payload.query:
        ingestion_result = await data_ingestion_client.search_and_run(
            DataCollectionSearchAndRunRequest(
                product_id=payload.product_id,
                company_id=payload.company_id,
                query=payload.query,
                marketplaces=payload.marketplaces,
            )
        )
    else:
        ingestion_result = await data_ingestion_client.run_collection(
            DataCollectionRunRequest(
                product_id=payload.product_id,
                marketplaces=payload.marketplaces,
            )
        )

    return await build_analysis_response(payload.product_id, ingestion_result)


@router.post("/search-and-run", response_model=RunAnalysisResponse)
async def search_scrape_and_run_analysis(payload: RunProductAnalysisRequest):
    ingestion_result = await data_ingestion_client.search_and_run(
        DataCollectionSearchAndRunRequest(
            product_id=payload.product_id,
            company_id=payload.company_id,
            query=payload.query,
            marketplaces=payload.marketplaces,
        )
    )

    return await build_analysis_response(payload.product_id, ingestion_result)
