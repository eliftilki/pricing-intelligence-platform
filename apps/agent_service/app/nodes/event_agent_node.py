from sqlalchemy.orm import Session

from app.graph.state import CompetitorGraphState
from app.services.market_intelligence_service import MarketIntelligenceService


def event_agent_node(state: CompetitorGraphState, db: Session) -> CompetitorGraphState:
    """
    LangGraph dugumu (Market Intelligence Agent): competitor_intelligence_node
    ile paralel calisir (ikisi de START'tan tetiklenir, ikisi de bagimsiz).
    Kendi db Session'ini kullanir - competitor_intelligence_node ile ayni
    Session paylasilmaz (parallel superstep'te thread-safety icin).
    """
    service = MarketIntelligenceService(db)

    result = service.analyze_market_signals(product_id=state["product_id"])

    # NOT: state'in tamami spread edilmiyor - competitor_intelligence_node ile
    # ayni superstep'te paralel calisiyor; ikisi de **state dondururse ortak
    # key'lere (product_id vb.) iki kere "yazilmis" sayilip LangGraph
    # InvalidUpdateError firlatir. Sadece bu node'un urettigi delta donulur.
    return {"market_event_features": result}
