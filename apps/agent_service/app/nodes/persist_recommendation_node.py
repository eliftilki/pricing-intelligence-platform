import logging

from sqlalchemy.orm import Session

from app.repositories.recommendation_repository import RecommendationRepository

logger = logging.getLogger(__name__)


def persist_recommendation_node(state: dict, db: Session) -> dict:
    """
    LangGraph dugumu (pipeline'in son adimi): recommendation_node'un urettigi
    state["recommendation"]'i, slm_explanation_node'un urettigi aciklamayla
    birlikte price_recommendations tablosuna yazar. slm_explanation'dan SONRA
    calisir - explanation alani ancak o asamada hazir olur.

    DB yazimi basarisiz olursa pipeline'i cokertmez (API cevabi recommendation
    alaninda dogru veri donmeye devam eder); sadece kalici kayit olusmaz.
    """
    recommendation = state.get("recommendation")

    if recommendation is None:
        return state

    repository = RecommendationRepository(db)

    try:
        repository.create(
            recommendation=recommendation,
            ids={
                "company_id": state.get("company_id"),
                "product_id": state.get("product_id"),
                "seller_product_id": state.get("seller_product_id"),
            },
            explanation=(state.get("slm_explanation") or {}).get("explanation"),
        )
    except Exception as exc:
        repository.rollback()
        logger.error(
            "persist_recommendation_node: price_recommendations kaydi olusturulamadi (product_id=%s): %s",
            state.get("product_id"),
            exc,
        )

    return state
