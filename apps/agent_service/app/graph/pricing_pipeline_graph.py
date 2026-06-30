import asyncio
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

# GECICI: SLM analizi icin pipeline trace araci. PIPELINE_TRACE=1 olmadan
# hicbir etkisi yok, normal calismayi degistirmez. Analiz bitince kaldirilacak.
_TRACE_ENABLED = bool(os.environ.get("PIPELINE_TRACE"))
_TRACE_PATH = Path(os.environ.get("PIPELINE_TRACE_PATH", "pipeline_trace.json"))
_trace_log: list[dict] = []


def _json_default(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _safe_snapshot(data: dict) -> dict:
    return json.loads(json.dumps(data, default=_json_default))


def _trace(node_name: str, fn):
    if not _TRACE_ENABLED:
        return fn

    def wrapped(state):
        input_snapshot = _safe_snapshot(dict(state))
        result = fn(state)
        output_dict = result if isinstance(result, dict) else {}
        output_snapshot = _safe_snapshot(output_dict)
        _trace_log.append(
            {
                "node": node_name,
                "input": input_snapshot,
                "output": output_snapshot,
            }
        )
        _TRACE_PATH.write_text(
            json.dumps(_trace_log, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    return wrapped
from app.graph.state import CompetitorGraphState
from app.nodes.candidate_price_generator_node import candidate_price_generator_node
from app.nodes.competitor_intelligence_node import competitor_intelligence_node
from app.nodes.data_ingestion_node import data_ingestion_node
from app.nodes.event_agent_node import event_agent_node
from app.nodes.feature_engineering_node import feature_engineering_node
from app.nodes.demand_prediction_node import demand_prediction_node
from app.nodes.optimization_node import optimization_node
from app.nodes.risk_control_node import risk_control_node
from app.nodes.pipeline_finalizer_node import pipeline_finalizer_node
from app.nodes.persist_recommendation_node import persist_recommendation_node
from app.nodes.recommendation_node import recommendation_node
from app.nodes.slm_explanation_node import slm_explanation_node


COMPETITOR_INTELLIGENCE_UPDATE_KEYS = (
    "status",
    "error_code",
    "failed_stage",
    "analyzed_count",
    "inserted_count",
    "message",
    "results",
)


def build_pricing_pipeline_graph(db: Session):
    graph = StateGraph(CompetitorGraphState)

    def run_competitor_intelligence(state: CompetitorGraphState):
        result = competitor_intelligence_node(state, db)
        return _pick_graph_update(result, COMPETITOR_INTELLIGENCE_UPDATE_KEYS)

    def run_event_agent(state: CompetitorGraphState):
        # competitor_intelligence ile paralel calistigi icin (ayni superstep)
        # ayri bir Session kullanir - SQLAlchemy Session thread-safe degildir.
        event_db = SessionLocal()
        try:
            result = event_agent_node(state, event_db)
            return {"market_event_features": result.get("market_event_features")}
        finally:
            event_db.close()

    def run_data_ingestion(state: CompetitorGraphState):
        return asyncio.run(data_ingestion_node(state))

    def run_feature_engineering(state: CompetitorGraphState):
        return feature_engineering_node(state, db)

    def run_candidate_price_generator(state: CompetitorGraphState):
        return candidate_price_generator_node(state, db)

    # ML talep tahmini: aday fiyatlar icin expected_sales uretir (optimization oncesi).
    def run_demand_prediction(state: CompetitorGraphState):
        return demand_prediction_node(state, db)

    def run_optimization(state: CompetitorGraphState):
        return optimization_node(state, db)
    
    def run_risk_control(state: CompetitorGraphState):
        return risk_control_node(state, db)

    def run_recommendation(state: CompetitorGraphState):
        return recommendation_node(state, db)

    def run_slm_explanation(state: CompetitorGraphState):
        return asyncio.run(slm_explanation_node(state))

    def run_pipeline_finalizer(state: CompetitorGraphState):
        return pipeline_finalizer_node(state)

    def run_persist_recommendation(state: CompetitorGraphState):
        return persist_recommendation_node(state, db)

    graph.add_node("data_ingestion", _trace("data_ingestion", run_data_ingestion))
    graph.add_node("competitor_intelligence", _trace("competitor_intelligence", run_competitor_intelligence))
    graph.add_node("event_agent", _trace("event_agent", run_event_agent))
    graph.add_node("feature_engineering", _trace("feature_engineering", run_feature_engineering))
    graph.add_node("candidate_price_generator", _trace("candidate_price_generator", run_candidate_price_generator))
    # candidate_price_generator -> demand_prediction -> optimization (run_optimization=true iken)
    graph.add_node("demand_prediction", _trace("demand_prediction", run_demand_prediction))
    graph.add_node("optimization", _trace("optimization", run_optimization))
    graph.add_node("risk_control", _trace("risk_control", run_risk_control))
    graph.add_node("recommendation", _trace("recommendation", run_recommendation))
    graph.add_node("slm_explanation", _trace("slm_explanation", run_slm_explanation))
    graph.add_node("persist_recommendation", _trace("persist_recommendation", run_persist_recommendation))
    graph.add_node("pipeline_finalizer", _trace("pipeline_finalizer", run_pipeline_finalizer))

    graph.add_edge(START, "data_ingestion")
    graph.add_conditional_edges(
        "data_ingestion",
        _route_after_data_ingestion,
        {
            "competitor_intelligence": "competitor_intelligence",
            "event_agent": "event_agent",
            "end": "pipeline_finalizer",
        },
    )
    graph.add_edge("competitor_intelligence", "feature_engineering")
    graph.add_edge("event_agent", "feature_engineering")

    graph.add_conditional_edges(
        "feature_engineering",
        _route_after_feature_engineering,
        {
            "candidate_price_generator": "candidate_price_generator",
            "optimization": "optimization",
            "end": "pipeline_finalizer",
        },
    )
    # Aday fiyat yolu: once ML tahmini, sonra kar optimizasyonu.
    graph.add_conditional_edges(
        "candidate_price_generator",
        _route_after_candidate_price_generator,
        {
            "demand_prediction": "demand_prediction",
            "end": "pipeline_finalizer",
        },
    )
    graph.add_conditional_edges(
        "demand_prediction",
        _route_after_demand_prediction,
        {
            "optimization": "optimization",
            "end": "pipeline_finalizer",
        },
    )
    graph.add_conditional_edges(
        "optimization",
        _route_after_optimization,
        {
            "risk_control": "risk_control",
            "end": "pipeline_finalizer",
        },
    )
    graph.add_conditional_edges(
        "risk_control",
        _route_after_risk_control,
        {
            "recommendation": "recommendation",
            "end": "pipeline_finalizer",
        },
    )
    graph.add_edge("recommendation", "slm_explanation")
    graph.add_edge("slm_explanation", "persist_recommendation")
    graph.add_edge("persist_recommendation", "pipeline_finalizer")
    graph.add_edge("pipeline_finalizer", END)

    return graph.compile()


def _route_after_data_ingestion(state: CompetitorGraphState) -> list[str]:
    if state.get("status") == "FAILED":
        return ["end"]

    return ["competitor_intelligence", "event_agent"]


def _route_after_feature_engineering(state: CompetitorGraphState) -> str:
    if state.get("status") == "FAILED":
        return "end"

    if state.get("run_candidate_prices"):
        return "candidate_price_generator"

    if state.get("run_optimization"):
        return "optimization"

    return "end"


def _route_after_candidate_price_generator(state: CompetitorGraphState) -> str:
    if state.get("status") == "FAILED":
        return "end"

    # optimization_node demand_predictions bekler; ML dugumu bunu doldurur.
    if state.get("run_optimization"):
        return "demand_prediction"

    return "end"


def _pick_graph_update(result: dict, allowed_keys: tuple[str, ...]) -> dict:
    return {key: result[key] for key in allowed_keys if key in result}


def _route_after_demand_prediction(state: CompetitorGraphState) -> str:
    # ML veya builder hata verdiyse pipeline'i burada durdur.
    if state.get("status") == "FAILED":
        return "end"

    return "optimization"


def _route_after_optimization(state: CompetitorGraphState) -> str:
    if state.get("status") == "FAILED":
        return "end"

    return "risk_control"


def _route_after_risk_control(state: CompetitorGraphState) -> str:
    if state.get("status") == "FAILED":
        return "end"

    return "recommendation"
