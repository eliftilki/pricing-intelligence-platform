from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.optimization_repository import OptimizationRepository
from app.schemas.optimization_schema import (
    OptimizationFromDbRequest,
    OptimizationRequest,
    OptimizationResponse,
)
from app.services.optimization_service import OptimizationService


router = APIRouter(
    prefix="/optimization",
    tags=["Optimization"],
)


@router.post("/run", response_model=OptimizationResponse)
def run_optimization(
    request: OptimizationRequest,
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    response = OptimizationService().optimize(request)

    if request.persist:
        OptimizationRepository(db).save_response(
            response=response,
            cost_price=request.cost_price,
            marketplaces=request.marketplaces,
        )

    return response


@router.post("/run-from-db/{seller_product_id}", response_model=OptimizationResponse)
def run_optimization_from_db(
    seller_product_id: UUID,
    request: OptimizationFromDbRequest,
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    repository = OptimizationRepository(db)

    try:
        marketplace_context = repository.build_marketplace_input_from_db(seller_product_id)
        seller_context = repository.get_seller_product_context(seller_product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cost_price = request.cost_price or repository._to_decimal(seller_context.get("cost_price"))
    if cost_price is None or cost_price <= Decimal("0"):
        raise HTTPException(
            status_code=400,
            detail="Seller product cost_price is missing or invalid.",
        )

    db_request = OptimizationRequest(
        seller_product_id=seller_product_id,
        product_id=request.product_id or seller_context.get("product_id"),
        run_id=request.run_id,
        cost_price=cost_price,
        demand_predictions=request.demand_predictions,
        marketplaces=[marketplace_context],
        persist=request.persist,
    )

    response = OptimizationService().optimize(db_request)

    if request.persist:
        repository.save_response(
            response=response,
            cost_price=db_request.cost_price,
            marketplaces=db_request.marketplaces,
        )

    return response
