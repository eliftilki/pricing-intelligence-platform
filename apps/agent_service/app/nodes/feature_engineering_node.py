import logging

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
        state["message"] = "product_id is missing. Feature engineering cannot run."
        return state

    repository = FeatureEngineeringRepository(db)

    try:
        seller_product = repository.get_seller_product(
            product_id=product_id,
            seller_product_id=state.get("seller_product_id"),
        )
    except ValueError as exc:
        state["status"] = "FAILED"
        state["message"] = str(exc)
        return state

    marketplace = seller_product.marketplace
    current_price = (
        float(seller_product.our_price) if seller_product.our_price is not None else None
    )
    stock_quantity = seller_product.stock_quantity

    competitor_features = repository.get_competitor_features(
        product_id=product_id,
        marketplace=marketplace,
    )

    logger.info(
        "feature_engineering_node basliyor: product_id=%s marketplace=%s rakip_sayisi=%d",
        product_id,
        marketplace,
        len(competitor_features),
    )

    features = _service.build_features(
        product_id=str(product_id),
        marketplace=marketplace,
        current_price=current_price,
        stock_quantity=stock_quantity,
        competitor_features=competitor_features,
    )

    if features.is_monopoly:
        logger.warning(
            "Monopol durumu tespit edildi (product_id=%s, marketplace=%s): "
            "gecerli (TIER_1/TIER_2) rakip bulunamadi.",
            product_id,
            marketplace,
        )
    else:
        logger.info(
            "feature_engineering_node tamamlandi: gecerli_rakip=%d min=%s agirlikli_ort=%s",
            features.valid_competitor_count,
            features.min_competitor_price,
            features.weighted_avg_competitor_price,
        )

    # candidate_price_generator_node'un ayni seller_product uzerinden devam
    # etmesini garantilemek icin cozumlenen id state'e yaziliyor.
    state["seller_product_id"] = seller_product.id
    state["marketplace"] = marketplace
    state["current_price"] = current_price
    state["stock_quantity"] = stock_quantity
    state["pricing_features"] = pricing_features_to_dict(features)

    # event_agent_node zaten tam hesaplanmis sonucu state'e yazmisti (rakip
    # verisinin aksine burada ham/parcali bir veri yok, DB'ye tekrar gitmeye
    # gerek yok) - sadece nihai feature paketine tasiniyor.
    state.setdefault("market_event_features", {})

    return state
