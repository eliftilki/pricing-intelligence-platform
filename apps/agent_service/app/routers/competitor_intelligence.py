from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.competitor_intelligence_schema import (
    CompetitorIntelligenceRunRequest,
    CompetitorIntelligenceRunResponse,
)
from app.services.competitor_intelligence_service import CompetitorIntelligenceService


router = APIRouter(
    prefix="/competitor-intelligence",
    tags=["Competitor Intelligence"],
)


@router.post("/run", response_model=CompetitorIntelligenceRunResponse)
def run_competitor_intelligence(
    payload: CompetitorIntelligenceRunRequest,
    db: Session = Depends(get_db),
):
    return CompetitorIntelligenceService(db).run(payload)