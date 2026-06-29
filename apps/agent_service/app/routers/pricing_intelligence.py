from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.graph.pricing_pipeline_graph import build_pricing_pipeline_graph
from app.models.product import Product, SellerProduct
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
    """
    Tam fiyatlandirma pipeline'i: competitor_intelligence + event_agent
    (paralel) -> feature_engineering -> candidate_price_generator ->
    optimization -> slm_explanation. Henuz frontend'e baglanmadi - "Fiyat
    Onerisi Olustur" gibi gercek bir aksiyon eklendiginde bu endpoint
    kullanilmali. Sadece rakip taramasi icin /competitor-intelligence/run'a
    bakin (o endpoint bilerek hafif tutuldu).
    """
    _validate_pricing_request(payload, db)

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


def _validate_pricing_request(payload: PricingIntelligenceRunRequest, db: Session) -> None:
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

    if payload.seller_product_id is None:
        return

    seller_product = (
        db.query(SellerProduct.id, SellerProduct.product_id)
        .filter(SellerProduct.id == payload.seller_product_id)
        .first()
    )
    if seller_product is None:
        raise HTTPException(
            status_code=404,
            detail=f"Seller product not found: {payload.seller_product_id}",
        )

    if seller_product.product_id != payload.product_id:
        raise HTTPException(
            status_code=400,
            detail="seller_product_id does not belong to product_id.",
        )
