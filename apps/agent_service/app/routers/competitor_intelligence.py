import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.competitor_intelligence_schema import (
    CompetitorIntelligenceRunRequest,
    CompetitorIntelligenceRunResponse,
)
from app.services.competitor_intelligence_service import CompetitorIntelligenceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/competitor-intelligence",
    tags=["Competitor Intelligence"],
)


@router.post("/run", response_model=CompetitorIntelligenceRunResponse)
async def run_competitor_intelligence(
    payload: CompetitorIntelligenceRunRequest,
    db: Session = Depends(get_db),
):
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(CompetitorIntelligenceService(db).run, payload),
            timeout=60.0,
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Competitor intelligence timeout for session_id={payload.session_id}")
        return CompetitorIntelligenceRunResponse(
            session_id=payload.session_id,
            product_id=payload.product_id,
            total_competitors=0,
            price_range={"min": None, "max": None, "median": None, "mean": None},
            buybox_prices={},
            recommendation={
                "suggested_price": None,
                "strategy": "UNKNOWN",
                "confidence": 0.0,
                "rationale": "Competitor intelligence timeout after 60 seconds",
            },
            competitors=[],
        )