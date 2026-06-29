from fastapi import APIRouter, HTTPException

from app.schemas.ingestion_schema import SearchRequest, SearchResponse
from app.services.search_service import run_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_products(payload: SearchRequest):
    try:
        result = await run_search(
            query=payload.query,
            marketplaces=payload.marketplaces,
            max_results=payload.max_results,
            connection_type=payload.connection_type,
            ram_gb=payload.ram_gb,
            storage_gb=payload.storage_gb,
            sim_type=payload.sim_type,
            keyboard_layout=payload.keyboard_layout,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
