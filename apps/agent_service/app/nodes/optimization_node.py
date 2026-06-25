from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.commission_repository import CommissionRepository
from app.repositories.optimization_repository import OptimizationRepository
from app.schemas.optimization_schema import (
    DemandPredictionItem,
    MarketplaceOptimizationInput,
    OptimizationRequest,
)
from app.services.commission_service import (
    CommissionRateNotFoundError,
    CommissionService,
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
    commission_service = CommissionService(CommissionRepository(db))

    try:
        seller_product_id = UUID(str(state["seller_product_id"]))
        seller_context = repository.get_seller_product_context(seller_product_id)
        marketplaces = _build_marketplaces(
            state=state,
            repository=repository,
            commission_service=commission_service,
            seller_context=seller_context,
        )
        cost_price = state.get("cost_price") or seller_context.get("cost_price")
    except CommissionRateNotFoundError as exc:
        state["status"] = "FAILED"
        state["message"] = str(exc)
        state["error_code"] = exc.code
        return state
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
    commission_service: CommissionService,
    seller_context: dict,
) -> list[MarketplaceOptimizationInput]:
    marketplaces_raw = state.get("marketplaces") or state.get("marketplace_contexts")

    if marketplaces_raw:
        return [
            MarketplaceOptimizationInput(**item)
            for item in marketplaces_raw
        ]

    commission_rate = commission_service.get_commission_rate(
        company_id=seller_context["company_id"],
        marketplace=seller_context["marketplace"],
        category_id=seller_context.get("category_id"),
    )

    return [
        repository.build_marketplace_input_from_context(
            context=seller_context,
            commission_rate=commission_rate,
        )
    ]
