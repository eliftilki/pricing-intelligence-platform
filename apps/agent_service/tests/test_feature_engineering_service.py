from app.services.feature_engineering_service import FeatureEngineeringService

svc = FeatureEngineeringService()

COMPETITORS = [
    {
        "marketplace": "TRENDYOL",
        "tier": "TIER_1",
        "price": 100.0,
        "is_in_stock": True,
        "competitor_strength_score": 2.0,
        "buybox_threat_score": 80.0,
        "price_aggression_score": 60.0,
    },
    {
        "marketplace": "TRENDYOL",
        "tier": "TIER_2",
        "price": 120.0,
        "is_in_stock": True,
        "competitor_strength_score": 1.0,
        "buybox_threat_score": 40.0,
        "price_aggression_score": 20.0,
    },
]


def _build(market_event_features=None):
    return svc.build_features(
        product_id="p1",
        marketplace="TRENDYOL",
        current_price=110.0,
        stock_quantity=10,
        competitor_features=COMPETITORS,
        market_event_features=market_event_features,
    )


def test_event_signals_merge_into_pricing_features_when_present():
    features = _build(
        market_event_features={
            "recommended_demand_multiplier": 1.42,
            "event_confidence": 0.8,
            "market_demand_signal": "HIGH",
        }
    )

    assert features.recommended_demand_multiplier == 1.42
    assert features.event_confidence == 0.8
    assert features.market_demand_signal == "HIGH"


def test_event_signals_default_to_neutral_when_missing():
    features = _build(market_event_features=None)

    assert features.recommended_demand_multiplier == 1.0
    assert features.event_confidence == 0.0
    assert features.market_demand_signal == "LOW"


def test_event_signals_default_to_neutral_when_event_agent_failed():
    # event_agent_node basarisiz olursa _neutral_signals() ile bu sekle benzer
    # bir payload doner (multiplier=None degil, anahtarlar bos/None olabilir).
    features = _build(
        market_event_features={
            "recommended_demand_multiplier": None,
            "event_confidence": None,
            "market_demand_signal": None,
        }
    )

    assert features.recommended_demand_multiplier == 1.0
    assert features.event_confidence == 0.0
    assert features.market_demand_signal == "LOW"


def test_legitimate_zero_event_confidence_is_not_overridden_by_neutral_default():
    # event_confidence=0.0 gercek/gecerli bir deger (hic event yokken donen
    # normal sonuc) - "or" tabanli eski mantik bunu da notr varsayilanla
    # ayni gorup uzerine yazardi, ama burada zaten ayni deger oldugundan
    # bu test yalnizca is-None kontrolunun 0.0'i KORUDUGUNU dogrular.
    features = _build(
        market_event_features={
            "recommended_demand_multiplier": 0.5,
            "event_confidence": 0.0,
            "market_demand_signal": "LOW",
        }
    )

    assert features.recommended_demand_multiplier == 0.5
    assert features.event_confidence == 0.0


def test_event_signals_present_in_monopoly_fallback_too():
    features = svc.build_features(
        product_id="p1",
        marketplace="TRENDYOL",
        current_price=110.0,
        stock_quantity=10,
        competitor_features=[],
        market_event_features={
            "recommended_demand_multiplier": 1.3,
            "event_confidence": 0.5,
            "market_demand_signal": "MEDIUM",
        },
    )

    assert features.is_monopoly is True
    assert features.recommended_demand_multiplier == 1.3
    assert features.event_confidence == 0.5
    assert features.market_demand_signal == "MEDIUM"
