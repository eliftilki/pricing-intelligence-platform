import asyncio

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.graph.state import CompetitorGraphState
from app.nodes.candidate_price_generator_node import candidate_price_generator_node
from app.nodes.competitor_intelligence_node import competitor_intelligence_node
from app.nodes.optimization_node import optimization_node
from app.nodes.slm_explanation_node import slm_explanation_node


def build_pricing_pipeline_graph(db: Session):
    graph = StateGraph(CompetitorGraphState)

    def run_competitor_intelligence(state: CompetitorGraphState):
        return competitor_intelligence_node(state, db)

    def run_candidate_price_generator(state: CompetitorGraphState):
        return candidate_price_generator_node(state, db)

    def run_optimization(state: CompetitorGraphState):
        return optimization_node(state, db)

    def run_slm_explanation(state: CompetitorGraphState):
        return asyncio.run(slm_explanation_node(state))

    graph.add_node("competitor_intelligence", run_competitor_intelligence)
    graph.add_node("candidate_price_generator", run_candidate_price_generator)
    graph.add_node("optimization", run_optimization)
    graph.add_node("slm_explanation", run_slm_explanation)

    graph.add_edge(START, "competitor_intelligence")
    graph.add_conditional_edges(
        "competitor_intelligence",
        _route_after_competitor_intelligence,
        {
            "candidate_price_generator": "candidate_price_generator",
            "optimization": "optimization",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "candidate_price_generator",
        _route_after_candidate_price_generator,
        {
            "optimization": "optimization",
            "end": END,
        },
    )
    graph.add_edge("optimization", "slm_explanation")
    graph.add_edge("slm_explanation", END)

    return graph.compile()


def _route_after_competitor_intelligence(state: CompetitorGraphState) -> str:
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

    if state.get("run_optimization"):
        return "optimization"

    return "end"
