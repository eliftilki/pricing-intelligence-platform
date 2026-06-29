from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.optimization_repository import OptimizationRepository
from app.schemas.risk_control_schema import (
    MarketplaceRiskInput,
    RiskContextInput,
    RiskControlRequest,
)
from app.services.risk_control_service import RiskControlService


def risk_control_node(state: dict, db: Session) -> dict:
    if state.get("status") == "FAILED":
        return state

    marketplace_recommendations = state.get("marketplace_recommendations")
    if not marketplace_recommendations:
        state["status"] = "FAILED"
        state["message"] = "marketplace_recommendations are missing. Risk control cannot run."
        return state

    if not state.get("seller_product_id"):
        state["status"] = "FAILED"
        state["message"] = "seller_product_id is missing. Risk control cannot run."
        return state

    try:
        seller_product_id = UUID(str(state["seller_product_id"]))
        repository = OptimizationRepository(db)
        seller_context = repository.get_seller_product_context(seller_product_id)

        cost_price = state.get("cost_price") or seller_context.get("cost_price")
        if cost_price is None:
            state["status"] = "FAILED"
            state["message"] = "cost_price is missing. Risk control cannot run."
            return state

        pricing_features = state.get("pricing_features") or {}
        optimization_result = state.get("optimization_result") or {}
        summary = optimization_result.get("summary") or {}

        context = RiskContextInput(
            seller_product_id=seller_product_id,
            product_id=_optional_uuid(state.get("product_id")) or seller_context.get("product_id"),
            cost_price=Decimal(str(cost_price)),
            min_margin_rate=Decimal(
                str(state.get("min_margin_rate") or seller_context.get("min_margin_rate") or "0.15")
            ),
            stock_quantity=_optional_int(state.get("stock_quantity"))
            or _optional_int(pricing_features.get("stock_quantity")),
            min_competitor_price=_optional_decimal(pricing_features.get("min_competitor_price")),
            avg_competitor_price=_optional_decimal(pricing_features.get("avg_competitor_price")),
            market_pressure_score=_optional_float(pricing_features.get("market_pressure_score")),
            demand_prediction_meta=state.get("demand_prediction_meta") or {},
        )

        request = RiskControlRequest(
            context=context,
            marketplaces=[
                MarketplaceRiskInput(
                    marketplace=str(item.get("marketplace", "UNKNOWN")),
                    recommended_price=_optional_decimal(item.get("recommended_price")),
                    current_price=_optional_decimal(item.get("current_price")),
                    unit_profit=_optional_decimal(item.get("unit_profit")),
                    unit_margin_rate=_optional_decimal(item.get("unit_margin_rate")),
                    expected_sales=_optional_decimal(item.get("expected_sales")),
                    commission_rate=_optional_decimal(item.get("commission_rate")),
                    selected_reason=item.get("selected_reason"),
                )
                for item in marketplace_recommendations
            ],
            optimization_summary_status=summary.get("status"),
        )

        response = RiskControlService().assess(request)
        state["risk_control_result"] = response.model_dump(mode="json")
        state["status"] = "SUCCESS"
        return state

    except (ValueError, TypeError) as exc:
        state["status"] = "FAILED"
        state["message"] = str(exc)
        return state


def _optional_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)