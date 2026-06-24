from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.competitor_repository import CompetitorRepository
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


def _serialize_competitor_result(result: dict) -> dict:
    return {
        "competitor_listing_id": (
            str(result["competitor_listing_id"])
            if result.get("competitor_listing_id")
            else None
        ),
        "competitor_seller_id": (
            str(result["competitor_seller_id"])
            if result.get("competitor_seller_id")
            else None
        ),
        "marketplace": result.get("marketplace"),
        "seller_name": result.get("seller_name"),
        "tier": result.get("tier"),
        "competitor_strength_score": result.get("competitor_strength_score"),
        "buybox_threat_score": result.get("buybox_threat_score"),
        "price_aggression_score": result.get("price_aggression_score"),
        "reason_codes": result.get("reason_codes", []),
    }


def _build_price_range(listings: list) -> dict:
    prices = sorted(
        float(listing.price)
        for listing in listings
        if listing.price is not None and float(listing.price) > 0
    )

    if not prices:
        return {}

    midpoint = len(prices) // 2
    median = (
        prices[midpoint]
        if len(prices) % 2
        else (prices[midpoint - 1] + prices[midpoint]) / 2
    )

    return {
        "min": prices[0],
        "max": prices[-1],
        "median": median,
        "mean": sum(prices) / len(prices),
    }


async def build_analysis_response(
    product_id: UUID,
    ingestion_result: dict,
    db: Session,
) -> RunAnalysisResponse:
    session_id = UUID(str(ingestion_result["job_id"]))

    intelligence = await agent_client.run_intelligence(
        session_id=session_id,
        product_id=product_id,
    )
    competitor_results = intelligence.get("results", [])
    listings = CompetitorRepository(db).list_latest_listings(product_id, limit=500)
    total_competitors = int(
        intelligence.get("total_competitors")
        or intelligence.get("analyzed_count")
        or sum(ingestion_result.get("scrape_counts", {}).values())
        or len(competitor_results)
    )

    return RunAnalysisResponse(
        session_id=session_id,
        product_id=product_id,
        ingestion_status=ingestion_result["status"],
        ingestion_message=ingestion_result.get("message"),
        scrape_counts=ingestion_result.get("scrape_counts", {}),
        total_competitors=total_competitors,
        price_range=intelligence.get("price_range") or _build_price_range(listings),
        recommendation={
            "suggested_price": None,
            "strategy": "COMPETITOR_INTELLIGENCE" if total_competitors else "INSUFFICIENT_DATA",
            "confidence": 1 if total_competitors else 0,
            "rationale": intelligence.get(
                "message",
                "Analiz icin yeterli rakip verisi bulunamadi.",
            ),
        },
        competitors=[_serialize_competitor_result(result) for result in competitor_results],
    )


@router.post("/run", response_model=RunAnalysisResponse)
async def run_analysis(payload: RunAnalysisRequest, db: Session = Depends(get_db)):
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

    return await build_analysis_response(payload.product_id, ingestion_result, db)


@router.post("/search-and-run", response_model=RunAnalysisResponse)
async def search_scrape_and_run_analysis(
    payload: RunProductAnalysisRequest,
    db: Session = Depends(get_db),
):
    ingestion_result = await data_ingestion_client.search_and_run(
        DataCollectionSearchAndRunRequest(
            product_id=payload.product_id,
            company_id=payload.company_id,
            query=payload.query,
            marketplaces=payload.marketplaces,
        )
    )

    return await build_analysis_response(payload.product_id, ingestion_result, db)
