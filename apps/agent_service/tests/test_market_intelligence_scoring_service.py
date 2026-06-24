from app.services.market_intelligence_scoring_service import MarketIntelligenceScoringService

svc = MarketIntelligenceScoringService()


def _trend(interest_change_7d=None):
    return {"trend_score": 50.0, "interest_change_7d": interest_change_7d, "interest_change_30d": None}


def _event(detected=False, days_until_event=None, base_impact=None):
    return {
        "event_detected": detected,
        "event_type": "BLACK_FRIDAY" if detected else None,
        "days_until_event": days_until_event,
        "base_event_impact": base_impact,
    }


def _category(category_demand_change=None):
    return {"category_trend_score": None, "category_demand_change": category_demand_change}


def test_no_signals_returns_neutral_baseline():
    result = svc.compute(_trend(), _event(), _category(), event_category_match=False)

    assert result["event_confidence"] == 0.0
    assert result["recommended_demand_multiplier"] == 1.0
    assert result["market_demand_signal"] == "LOW"
    assert result["reason_codes"] == []


def test_product_interest_spike_triggers_reason_code():
    result = svc.compute(_trend(interest_change_7d=0.5), _event(), _category(), event_category_match=False)

    assert "PRODUCT_INTEREST_UP_7D" in result["reason_codes"]
    assert result["recommended_demand_multiplier"] > 1.0


def test_category_demand_spike_triggers_reason_code():
    result = svc.compute(_trend(), _event(), _category(category_demand_change=0.4), event_category_match=False)

    assert "CATEGORY_DEMAND_UP" in result["reason_codes"]


def test_event_detected_but_no_category_match_has_zero_weight_reason_only():
    event = _event(detected=True, days_until_event=3, base_impact=0.95)
    result = svc.compute(_trend(), event, _category(), event_category_match=False)

    assert "EVENT_WITHIN_7_DAYS" in result["reason_codes"]
    assert "EVENT_CATEGORY_MATCH" not in result["reason_codes"]
    # event_confidence kategori eslesmesinden BAGIMSIZ hesaplanir (event.detected ve proximity'e gore)
    assert result["event_confidence"] > 0.0


def test_event_detected_with_category_match_adds_both_reason_codes():
    event = _event(detected=True, days_until_event=0, base_impact=0.95)
    result = svc.compute(_trend(), event, _category(), event_category_match=True)

    assert "EVENT_WITHIN_7_DAYS" in result["reason_codes"]
    assert "EVENT_CATEGORY_MATCH" in result["reason_codes"]
    assert result["event_confidence"] == 0.95  # days_until_event <= 0 -> proximity weight 1.0


def test_event_not_detected_gives_zero_confidence_regardless_of_match_flag():
    result = svc.compute(_trend(), _event(detected=False), _category(), event_category_match=True)

    assert result["event_confidence"] == 0.0
    assert "EVENT_WITHIN_7_DAYS" not in result["reason_codes"]
    assert "EVENT_CATEGORY_MATCH" not in result["reason_codes"]


def test_proximity_weight_decreases_with_distance():
    base_impact = 1.0
    close = svc._event_confidence(_event(detected=True, days_until_event=0, base_impact=base_impact))
    near = svc._event_confidence(_event(detected=True, days_until_event=7, base_impact=base_impact))
    mid = svc._event_confidence(_event(detected=True, days_until_event=14, base_impact=base_impact))
    far = svc._event_confidence(_event(detected=True, days_until_event=30, base_impact=base_impact))
    very_far = svc._event_confidence(_event(detected=True, days_until_event=60, base_impact=base_impact))

    assert close > near > mid > far > very_far
    assert very_far == 0.0


def test_market_demand_signal_buckets():
    assert svc._bucket(1.2) == "HIGH"
    assert svc._bucket(1.1) == "MEDIUM"
    assert svc._bucket(1.0) == "LOW"


def test_missing_values_do_not_crash_and_use_neutral_defaults():
    result = svc.compute(
        trend={"trend_score": None, "interest_change_7d": None, "interest_change_30d": None},
        event={"event_detected": False, "event_type": None, "days_until_event": None, "base_event_impact": None},
        category={"category_trend_score": None, "category_demand_change": None},
        event_category_match=False,
    )

    assert result["recommended_demand_multiplier"] == 1.0
    assert result["reason_codes"] == []
