from sqlalchemy.orm import Session

from app.graph.state import CompetitorGraphState
from app.services.competitor_intelligence_service import CompetitorIntelligenceService


def competitor_intelligence_node(state: CompetitorGraphState, db: Session) -> CompetitorGraphState:
    service = CompetitorIntelligenceService(db)

    result = service.analyze_product_competitors(
        product_id=state["product_id"],
        lookback_hours=state.get("lookback_hours", 24),
    )

    if result.get("status") == "FAILED":
        result["failed_stage"] = "competitor_intelligence"

    # NOT: state'in tamami spread edilmiyor - event_agent_node ile ayni
    # superstep'te paralel calisiyor, ikisi de **state dondururse ortak
    # key'lere (product_id vb.) iki kere "yazilmis" sayilip LangGraph
    # InvalidUpdateError firlatir. Sadece bu node'un urettigi delta donulur.
    return result
