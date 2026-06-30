import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.feature_engineering_repository import FeatureEngineeringRepository
from app.services.feature_engineering_service import (
    FeatureEngineeringService,
    pricing_features_to_dict,
)

logger = logging.getLogger(__name__)

_service = FeatureEngineeringService()


def feature_engineering_node(state: dict, db: Session) -> dict:
    """
    LangGraph dugumu (2. asama): competitor_intelligence_node'un DB'ye yazdigi
    competitor_tiers + competitor_listings verisini birlestirip "pricing_features"
    alanini state'e ekler. competitor_intelligence_node'dan SONRA,
    candidate_price_generator_node'dan ONCE calisir.

    NOT: Bu dugum komisyon_orani, kargo_ucreti, ambalaj_maliyeti, min_kar_marji,
    cost_price gibi IC MALIYET alanlarina KESINLIKLE dokunmaz. Onlar Optimization
    asamasina / candidate_price stratejilerine aittir.
    """
    product_id = state.get("product_id")

    if not product_id:
        state["status"] = "FAILED"
        state["failed_stage"] = "feature_engineering"
        state["message"] = "product_id is missing. Feature engineering cannot run."
        return state

    repository = FeatureEngineeringRepository(db)

    try:
        seller_product = repository.get_seller_product(
            product_id=product_id,
            seller_product_id=state.get("seller_product_id"),
        )
        feature_seller_products = _get_feature_seller_products(
            state=state,
            repository=repository,
            product_id=product_id,
            fallback=seller_product,
        )
    except ValueError as exc:
        state["status"] = "FAILED"
        state["failed_stage"] = "feature_engineering"
        state["message"] = str(exc)
        return state

    marketplaces = sorted(
        {str(item.marketplace).upper() for item in feature_seller_products}
    )
    current_prices = [
        float(item.our_price)
        for item in feature_seller_products
        if item.our_price is not None
    ]
    current_price = (
        sum(current_prices) / len(current_prices) if current_prices else None
    )
    stock_quantity = sum(
        int(item.stock_quantity or 0) for item in feature_seller_products
    )

    competitor_features = repository.get_competitor_features(
        product_id=product_id,
        marketplace=None,
    )

    market_event_features = state.get("market_event_features")
    if not market_event_features:
        # event_agent_node ayni graph calismasinda hic calismamis/hata
        # vermis olabilir - elimizdeki en taze DB kaydina (varsa) fallback
        # yapiyoruz, yoksa _extract_event_features notr varsayilanlara duser.
        cached_event_row = repository.get_fresh_market_event_features(product_id)
        if cached_event_row is not None:
            market_event_features = _market_event_row_to_dict(cached_event_row)
            logger.info(
                "market_event_features state'te yoktu, DB fallback kullanildi (product_id=%s, generated_at=%s)",
                product_id,
                cached_event_row.generated_at,
            )

    logger.info(
        "feature_engineering_node basliyor: product_id=%s marketplaces=%s rakip_sayisi=%d",
        product_id,
        marketplaces,
        len(competitor_features),
    )

    agent_run = repository.create_agent_run(
        product_id=product_id,
        input_payload={
            "seller_product_id": str(seller_product.id),
            "marketplaces": marketplaces,
            "current_price": current_price,
            "stock_quantity": stock_quantity,
            "competitor_count": len(competitor_features),
        },
    )

    features = _service.build_features(
        product_id=str(product_id),
        marketplace=None,
        current_price=current_price,
        stock_quantity=stock_quantity,
        competitor_features=competitor_features,
        market_event_features=market_event_features,
    )

    if features.is_monopoly:
        logger.warning(
            "Monopol durumu tespit edildi (product_id=%s, marketplaces=%s): "
            "gecerli (TIER_1/TIER_2) rakip bulunamadi.",
            product_id,
            marketplaces,
        )
    else:
        logger.info(
            "feature_engineering_node tamamlandi: gecerli_rakip=%d min=%s agirlikli_ort=%s",
            features.valid_competitor_count,
            features.min_competitor_price,
            features.weighted_avg_competitor_price,
        )

    pricing_features = pricing_features_to_dict(features)

    try:
        repository.finish_agent_run(agent_run, "SUCCESS", output_payload=pricing_features)
        repository.commit()
    except Exception as exc:
        repository.rollback()
        logger.error(
            "pricing_features agent_runs'a kaydedilemedi (product_id=%s): %s",
            product_id,
            exc,
        )
        try:
            repository.finish_agent_run(agent_run, "FAILED", error_message=str(exc))
            repository.commit()
        except Exception as exc2:
            repository.rollback()
            logger.error(
                "agent_run FAILED durumu da kaydedilemedi (product_id=%s, agent_run_id=%s): %s",
                product_id,
                agent_run.id,
                exc2,
            )

    # candidate_price_generator_node'un ayni seller_product uzerinden devam
    # etmesini garantilemek icin cozumlenen id state'e yaziliyor.
    state["seller_product_id"] = seller_product.id
    state["marketplace"] = None
    state["current_price"] = current_price
    state["stock_quantity"] = stock_quantity
    state["pricing_features"] = pricing_features
    state["product_name"] = seller_product.product.name if seller_product.product else None
    state["company_id"] = seller_product.company_id

    return state


def _get_feature_seller_products(
    *,
    state: dict,
    repository: FeatureEngineeringRepository,
    product_id,
    fallback,
) -> list:
    seller_product_ids = state.get("seller_product_ids") or {}
    if not seller_product_ids:
        return [fallback]

    unique_ids = list(dict.fromkeys(seller_product_ids.values()))
    return [
        repository.get_seller_product(
            product_id=product_id,
            seller_product_id=UUID(str(seller_product_id)),
        )
        for seller_product_id in unique_ids
    ]


def _market_event_row_to_dict(row) -> dict:
    return {
        "category": row.category,
        "trend_score": float(row.trend_score) if row.trend_score is not None else None,
        "interest_change_7d": float(row.interest_change_7d) if row.interest_change_7d is not None else None,
        "interest_change_30d": float(row.interest_change_30d) if row.interest_change_30d is not None else None,
        "event_detected": row.event_detected,
        "event_type": row.event_type,
        "days_until_event": row.days_until_event,
        "event_confidence": float(row.event_confidence) if row.event_confidence is not None else None,
        "category_trend_score": float(row.category_trend_score) if row.category_trend_score is not None else None,
        "category_demand_change": float(row.category_demand_change) if row.category_demand_change is not None else None,
        "market_demand_signal": row.market_demand_signal,
        "recommended_demand_multiplier": (
            float(row.recommended_demand_multiplier) if row.recommended_demand_multiplier is not None else None
        ),
        "reason_codes": row.reason_codes or [],
        "generated_at": row.generated_at.isoformat(),
    }
