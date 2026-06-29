from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product import Product
from app.nodes.competitor_intelligence_node import competitor_intelligence_node
from app.schemas.competitor_schema import CompetitorIntelligenceRunRequest, CompetitorIntelligenceRunResponse


router = APIRouter(prefix="/competitor-intelligence", tags=["Competitor Intelligence"])


@router.post("/run", response_model=CompetitorIntelligenceRunResponse)
def run_competitor_intelligence(payload: CompetitorIntelligenceRunRequest, db: Session = Depends(get_db)):
    """
    Sadece rakip taramasi + skorlama yapar (tek node, graph yok). Bilerek hafif
    tutuldu: frontend'in "analiz baslat" akisi su an sadece rakip listesini
    gosteriyor, fiyat onerisi/optimizasyon/SLM aciklamasi tuketmiyor. Tam
    pipeline (event_agent + feature_engineering + candidate_price +
    optimization + slm_explanation) icin /pricing-intelligence/run kullanin.
    """
    product_exists = (
        db.query(Product.id)
        .filter(Product.id == payload.product_id)
        .first()
        is not None
    )
    if not product_exists:
        raise HTTPException(
            status_code=404,
            detail=f"Product not found: {payload.product_id}",
        )

    return competitor_intelligence_node(
        {
            "product_id": payload.product_id,
            "lookback_hours": payload.lookback_hours,
        },
        db,
    )
