import logging

from sqlalchemy.orm import Session

from app.repositories.feature_engineering_repository import FeatureEngineeringRepository
from app.services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)


def recommendation_node(state: dict, db: Session) -> dict:
    """
    LangGraph dugumu (6. asama): optimization_node ciktisini tekil bir
    "recommendation" objesine cevirir. slm_explanation_node bu alani okur.
    optimization basarisiz olduysa (status=FAILED) hicbir sey yapmadan
    state'i aynen dondurur - graph zaten bu durumda buraya gelmeden END'e gider.
    """
    product_id = state.get("product_id")

    repository = FeatureEngineeringRepository(db)

    competitor_features = repository.get_competitor_features(
        product_id=product_id,
        marketplace=state.get("marketplace"),
    )

    recommendation = recommendation_service.build_recommendation(
        optimization_result=state.get("optimization_result") or {},
        pricing_features=state.get("pricing_features") or {},
        product_name=state.get("product_name"),
        risk_assessment=state.get("risk_assessment"),
        competitor_features=competitor_features,
    )

    if recommendation is None:
        logger.warning(
            "recommendation_node: gecerli aday bulunamadi, recommendation None (product_id=%s)",
            product_id,
        )
    else:
        logger.info(
            "recommendation_node tamamlandi: product_id=%s marketplace=%s recommended_price=%s",
            product_id,
            recommendation.get("marketplace"),
            recommendation.get("recommended_price"),
        )

    state["recommendation"] = recommendation

    return state
