from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.graph.state import CompetitorGraphState
from app.nodes.competitor_intelligence_node import competitor_intelligence_node


def build_competitor_graph(db: Session):
    graph = StateGraph(CompetitorGraphState)

    def run_competitor_intelligence(state: CompetitorGraphState):
        return competitor_intelligence_node(state, db)

    graph.add_node("competitor_intelligence", run_competitor_intelligence)
    graph.add_edge(START, "competitor_intelligence")
    graph.add_edge("competitor_intelligence", END)

    return graph.compile()
