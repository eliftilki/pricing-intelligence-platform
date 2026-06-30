from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.graph.pricing_pipeline_graph import build_pricing_pipeline_graph
from app.models.product import Product, SellerProduct
from app.repositories.pricing_intelligence_repository import (
    PricingIntelligenceRepository,
)
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
    Tam fiyatlandirma pipeline'i: data_ingestion -> competitor_intelligence +
    event_agent (paralel) -> feature_engineering -> candidate_price_generator ->
    demand_prediction -> optimization -> risk_control -> recommendation ->
    slm_explanation -> persist_recommendation -> pipeline_finalizer.
    Henuz frontend'e baglanmadi - "Fiyat Onerisi Olustur" gibi gercek bir
    aksiyon eklendiginde bu endpoint kullanilmali. Sadece rakip taramasi icin
    /competitor-intelligence/run'a bakin (o endpoint bilerek hafif tutuldu).
    """
    _validate_pricing_request(payload, db)

    graph = build_pricing_pipeline_graph(db)

    graph_result = graph.invoke(
        {
            "product_id": payload.product_id,
            "seller_product_id": payload.seller_product_id,
            "seller_product_ids": payload.seller_product_ids,
            "lookback_hours": payload.lookback_hours,
            "ingestion_marketplaces": payload.ingestion_marketplaces,
            "ingestion_query": payload.ingestion_query,
            "ingestion_company_id": payload.ingestion_company_id,
            "run_candidate_prices": payload.run_candidate_prices,
            "run_optimization": payload.run_optimization,
            "persist_optimization": payload.persist_optimization,
            "sales_7d_avg": payload.sales_7d_avg,
            "demand_predictions": [
                item.model_dump(mode="json")
                for item in payload.demand_predictions
            ],
            "errors": [],
            "warnings": [],
        }
    )
    response = PricingIntelligenceRunResponse.model_validate(graph_result)

    PricingIntelligenceRepository(db).save_run(
        product_id=payload.product_id,
        seller_product_id=payload.seller_product_id,
        company_id=payload.ingestion_company_id,
        input_payload=payload.model_dump(mode="json"),
        output_payload=response.model_dump(mode="json"),
        status=response.status,
    )

    return response


@router.get(
    "/latest/{product_id}",
    response_model=PricingIntelligenceRunResponse,
)
def get_latest_pricing_intelligence(
    product_id: UUID,
    seller_product_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    run = PricingIntelligenceRepository(db).get_latest_run(
        product_id=product_id,
        seller_product_id=seller_product_id,
    )
    if run is None or run.output_payload is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pricing intelligence result found for product: {product_id}",
        )

    return PricingIntelligenceRunResponse.model_validate(run.output_payload)


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

    seller_products_to_validate = dict(payload.seller_product_ids)
    if payload.seller_product_id is not None:
        seller_products_to_validate.setdefault("PRIMARY", payload.seller_product_id)

    for expected_marketplace, seller_product_id in seller_products_to_validate.items():
        seller_product = (
            db.query(
                SellerProduct.id,
                SellerProduct.product_id,
                SellerProduct.marketplace,
            )
            .filter(SellerProduct.id == seller_product_id)
            .first()
        )
        if seller_product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Seller product not found: {seller_product_id}",
            )

        if seller_product.product_id != payload.product_id:
            raise HTTPException(
                status_code=400,
                detail=f"Seller product does not belong to product_id: {seller_product_id}",
            )

        if (
            expected_marketplace != "PRIMARY"
            and str(seller_product.marketplace).upper() != expected_marketplace
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"seller_product_ids[{expected_marketplace}] belongs to "
                    f"{seller_product.marketplace}."
                ),
            )
