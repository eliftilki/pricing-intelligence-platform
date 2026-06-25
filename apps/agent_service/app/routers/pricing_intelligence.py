from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.graph.pricing_pipeline_graph import build_pricing_pipeline_graph
from app.schemas.pricing_intelligence_schema import (
    PricingIntelligenceRunRequest,
    PricingIntelligenceRunResponse,
)


router = APIRouter(prefix="/pricing-intelligence", tags=["Pricing Intelligence"])


@router.post("/run", response_model=PricingIntelligenceRunResponse)
def run_pricing_intelligence(
    payload: PricingIntelligenceRunRequest,
    db: Session = Depends(get_db),
):
    graph = build_pricing_pipeline_graph(db)

    return graph.invoke(
        {
            "product_id": payload.product_id,
            "seller_product_id": payload.seller_product_id,
            "lookback_hours": payload.lookback_hours,
            "run_candidate_prices": payload.run_candidate_prices,
            "run_optimization": payload.run_optimization,
            "persist_candidate_prices": payload.persist_candidate_prices,
            "persist_optimization": payload.persist_optimization,
            "price_step": payload.price_step,
            "base_price_step": payload.base_price_step,
            "dense_price_step": payload.dense_price_step,
            "demand_predictions": [
                item.model_dump(mode="json")
                for item in payload.demand_predictions
            ],
        }
    )
