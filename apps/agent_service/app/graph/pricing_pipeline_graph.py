import asyncio

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.graph.state import CompetitorGraphState
from app.nodes.candidate_price_generator_node import candidate_price_generator_node
from app.nodes.competitor_intelligence_node import competitor_intelligence_node
from app.nodes.event_agent_node import event_agent_node
from app.nodes.feature_engineering_node import feature_engineering_node
from app.nodes.demand_prediction_node import demand_prediction_node
from app.nodes.optimization_node import optimization_node
from app.nodes.slm_explanation_node import slm_explanation_node


def build_pricing_pipeline_graph(db: Session):
    graph = StateGraph(CompetitorGraphState)

    def run_competitor_intelligence(state: CompetitorGraphState):
        return competitor_intelligence_node(state, db)

    def run_event_agent(state: CompetitorGraphState):
        # competitor_intelligence ile paralel calistigi icin (ayni superstep)
        # ayri bir Session kullanir - SQLAlchemy Session thread-safe degildir.
        event_db = SessionLocal()
        try:
            return event_agent_node(state, event_db)
        finally:
            event_db.close()

    def run_feature_engineering(state: CompetitorGraphState):
        return feature_engineering_node(state, db)

    def run_candidate_price_generator(state: CompetitorGraphState):
        return candidate_price_generator_node(state, db)

    # ML talep tahmini: aday fiyatlar icin expected_sales uretir (optimization oncesi).
    def run_demand_prediction(state: CompetitorGraphState):
        return demand_prediction_node(state, db)

    def run_optimization(state: CompetitorGraphState):
        return optimization_node(state, db)

    def run_slm_explanation(state: CompetitorGraphState):
        return asyncio.run(slm_explanation_node(state))

    graph.add_node("competitor_intelligence", run_competitor_intelligence)
    graph.add_node("event_agent", run_event_agent)
    graph.add_node("feature_engineering", run_feature_engineering)
    graph.add_node("candidate_price_generator", run_candidate_price_generator)
    # candidate_price_generator -> demand_prediction -> optimization (run_optimization=true iken)
    graph.add_node("demand_prediction", run_demand_prediction)
    graph.add_node("optimization", run_optimization)
    graph.add_node("slm_explanation", run_slm_explanation)

    graph.add_edge(START, "competitor_intelligence")
    graph.add_edge(START, "event_agent")
    graph.add_edge("competitor_intelligence", "feature_engineering")
    graph.add_edge("event_agent", "feature_engineering")

    graph.add_conditional_edges(
        "feature_engineering",
        _route_after_feature_engineering,
        {
            "candidate_price_generator": "candidate_price_generator",
            "optimization": "optimization",
            "end": END,
        },
    )
    # Aday fiyat yolu: once ML tahmini, sonra kar optimizasyonu.
    graph.add_conditional_edges(
        "candidate_price_generator",
        _route_after_candidate_price_generator,
        {
            "demand_prediction": "demand_prediction",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "demand_prediction",
        _route_after_demand_prediction,
        {
            "optimization": "optimization",
            "end": END,
        },
    )
    graph.add_edge("optimization", "slm_explanation")
    graph.add_edge("slm_explanation", END)

    return graph.compile()


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


def _route_after_demand_prediction(state: CompetitorGraphState) -> str:
    # ML veya builder hata verdiyse pipeline'i burada durdur.
    if state.get("status") == "FAILED":
        return "end"

    return "optimization"
