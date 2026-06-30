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
        state["failed_stage"] = "optimization"
        state["message"] = "seller_product_id is missing. Optimization cannot run."
        return state

    if not state.get("demand_predictions"):
        state["status"] = "FAILED"
        state["failed_stage"] = "optimization"
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
        state["failed_stage"] = "optimization"
        state["message"] = str(exc)
        state["error_code"] = exc.code
        return state
    except (ValueError, KeyError) as exc:
        state["status"] = "FAILED"
        state["failed_stage"] = "optimization"
        state["message"] = str(exc)
        return state

    if cost_price is None:
        state["status"] = "FAILED"
        state["failed_stage"] = "optimization"
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
    state["marketplace_results"] = state["marketplace_recommendations"]
    state["status"] = "SUCCESS"

    return state


def _build_marketplaces(
    state: dict,
    repository: OptimizationRepository,
    commission_service: CommissionService,
    seller_context: dict,
) -> list[MarketplaceOptimizationInput]:
    marketplaces_raw = state.get("marketplaces") or state.get("marketplace_contexts")
    seller_product_ids = state.get("seller_product_ids") or {}
    market_average_price = (
        state.get("candidate_price_result") or {}
    ).get("avg_competitor_price")

    if marketplaces_raw:
        return [
            MarketplaceOptimizationInput(
                **{
                    **item,
                    "market_average_price": (
                        item.get("market_average_price") or market_average_price
                    ),
                }
            )
            for item in marketplaces_raw
        ]

    if seller_product_ids:
        marketplace_inputs: list[MarketplaceOptimizationInput] = []
        for expected_marketplace, seller_product_id in seller_product_ids.items():
            context = repository.get_seller_product_context(
                UUID(str(seller_product_id))
            )
            actual_marketplace = str(context["marketplace"]).upper()
            if actual_marketplace != str(expected_marketplace).upper():
                raise ValueError(
                    f"Seller product {seller_product_id} belongs to "
                    f"{actual_marketplace}, not {expected_marketplace}."
                )

            commission_rate = commission_service.get_commission_rate(
                company_id=context["company_id"],
                marketplace=context["marketplace"],
                category_id=context.get("category_id"),
            )
            marketplace_inputs.append(
                repository.build_marketplace_input_from_context(
                    context={
                        **context,
                        "market_average_price": market_average_price,
                    },
                    commission_rate=commission_rate,
                )
            )

        return marketplace_inputs

    commission_rate = commission_service.get_commission_rate(
        company_id=seller_context["company_id"],
        marketplace=seller_context["marketplace"],
        category_id=seller_context.get("category_id"),
    )

    marketplace_context = {
        **seller_context,
        "market_average_price": market_average_price,
    }

    return [
        repository.build_marketplace_input_from_context(
            context=marketplace_context,
            commission_rate=commission_rate,
        )
    ]
