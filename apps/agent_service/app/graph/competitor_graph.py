from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.graph.state import CompetitorGraphState
from app.nodes.competitor_intelligence_node import competitor_intelligence_node
from app.nodes.event_agent_node import event_agent_node
from app.nodes.feature_engineering_node import feature_engineering_node


def build_competitor_graph(db: Session):
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

    graph.add_node("competitor_intelligence", run_competitor_intelligence)
    graph.add_node("event_agent", run_event_agent)
    graph.add_node("feature_engineering", run_feature_engineering)

    graph.add_edge(START, "competitor_intelligence")
    graph.add_edge(START, "event_agent")
    graph.add_edge("competitor_intelligence", "feature_engineering")
    graph.add_edge("event_agent", "feature_engineering")
    graph.add_edge("feature_engineering", END)

    return graph.compile()
