from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.optimization_repository import OptimizationRepository
from app.schemas.optimization_schema import (
    DemandPredictionItem,
    MarketplaceOptimizationInput,
    OptimizationRequest,
)
from app.services.optimization_service import OptimizationService


def optimization_node(state: dict, db: Session) -> dict:
    if not state.get("seller_product_id"):
        state["status"] = "FAILED"
        state["message"] = "seller_product_id is missing. Optimization cannot run."
        return state

    if not state.get("demand_predictions"):
        state["status"] = "FAILED"
        state["message"] = "demand_predictions are missing. Optimization cannot run."
        return state

    repository = OptimizationRepository(db)

    try:
        seller_product_id = UUID(str(state["seller_product_id"]))
        seller_context = repository.get_seller_product_context(seller_product_id)
        marketplaces = _build_marketplaces(state, repository, seller_product_id)
        cost_price = state.get("cost_price") or seller_context.get("cost_price")
    except (ValueError, KeyError) as exc:
        state["status"] = "FAILED"
        state["message"] = str(exc)
        return state

    if cost_price is None:
        state["status"] = "FAILED"
        state["message"] = "cost_price is missing. Optimization cannot run."
        return state

    request = OptimizationRequest(
        seller_product_id=seller_product_id,
        product_id=UUID(str(state["product_id"])) if state.get("product_id") else seller_context.get("product_id"),
        run_id=UUID(str(state["run_id"])) if state.get("run_id") else None,
        cost_price=Decimal(str(cost_price)),
        demand_predictions=[
            DemandPredictionItem(**item)
            for item in state.get("demand_predictions", [])
        ],
        marketplaces=marketplaces,
        persist=bool(state.get("persist_optimization", False)),
    )

    response = OptimizationService().optimize(request)

    if request.persist:
        repository.save_response(
            response=response,
            cost_price=request.cost_price,
            marketplaces=request.marketplaces,
        )

    state["optimization_result"] = response.model_dump(mode="json")
    state["marketplace_recommendations"] = state["optimization_result"]["marketplace_results"]
    state["status"] = "SUCCESS"

    return state


def _build_marketplaces(
    state: dict,
    repository: OptimizationRepository,
    seller_product_id: UUID,
) -> list[MarketplaceOptimizationInput]:
    marketplaces_raw = state.get("marketplaces") or state.get("marketplace_contexts")

    if marketplaces_raw:
        return [
            MarketplaceOptimizationInput(**item)
            for item in marketplaces_raw
        ]

    return [repository.build_marketplace_input_from_db(seller_product_id)]
