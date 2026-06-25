from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.nodes.competitor_intelligence_node import competitor_intelligence_node
from app.schemas.competitor_schema import CompetitorIntelligenceRunRequest, CompetitorIntelligenceRunResponse


router = APIRouter(prefix="/competitor-intelligence", tags=["Competitor Intelligence"])


@router.post("/run", response_model=CompetitorIntelligenceRunResponse)
def run_competitor_intelligence(payload: CompetitorIntelligenceRunRequest, db: Session = Depends(get_db)):
    return competitor_intelligence_node(
        {
            "product_id": payload.product_id,
            "lookback_hours": payload.lookback_hours,
        },
        db,
    )
