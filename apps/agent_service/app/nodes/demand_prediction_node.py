from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.feature_engineering_repository import FeatureEngineeringRepository
from app.services.demand_prediciton_builder import DemandPredictionBuildContext
from app.services.demand_prediction_service import (
    DemandPredictionServiceError,
    demand_prediction_service,
)


def demand_prediction_node(state: dict, db: Session) -> dict:
    """
    Ince adaptör: state okur, service cagirir, demand_predictions yazar.
    Is mantigi builder + service'te; burada HTTP veya feature mapping yok.
    """
    if not state.get("candidate_prices"):
        state["status"] = "FAILED"
        state["failed_stage"] = "demand_prediction"
        state["message"] = "candidate_prices are missing. Demand prediction cannot run."
        return state

    if not state.get("pricing_features"):
        state["status"] = "FAILED"
        state["failed_stage"] = "demand_prediction"
        state["message"] = "pricing_features are missing. Demand prediction cannot run."
        return state

    product_id = state.get("product_id")
    if not product_id:
        state["status"] = "FAILED"
        state["failed_stage"] = "demand_prediction"
        state["message"] = "product_id is missing. Demand prediction cannot run."
        return state

    pricing_features = state["pricing_features"]
    market_event_features = state.get("market_event_features") or {}

    repository = FeatureEngineeringRepository(db)
    # pricing_features'ta tier kirilimi yok; tier1/aggression icin ham rakip listesi tekrar okunur.
    competitor_features = repository.get_competitor_features(
        product_id=product_id,
        marketplace=state.get("marketplace") or pricing_features.get("marketplace"),
    )

    context = DemandPredictionBuildContext(
        candidate_prices=state["candidate_prices"],
        pricing_features=pricing_features,
        market_event_features=market_event_features,
        # API/state uzerinden gelmeli; yoksa builder hata verir.
        sales_7d_avg=state.get("sales_7d_avg"),
        stock_quantity=state.get("stock_quantity"),
        product_id=str(product_id),
        category=market_event_features.get("category"),
        competitor_features=competitor_features,
    )

    try:
        result = demand_prediction_service.predict(context)
    except ValueError as exc:
        state["status"] = "FAILED"
        state["failed_stage"] = "demand_prediction"
        state["message"] = str(exc)
        return state
    except DemandPredictionServiceError as exc:
        state["status"] = "FAILED"
        state["failed_stage"] = "demand_prediction"
        state["message"] = str(exc)
        return state

    state.update(result.to_state())
    # demand_predictions -> optimization_node; meta -> izleme/debug
    state["status"] = "SUCCESS"
    return state
