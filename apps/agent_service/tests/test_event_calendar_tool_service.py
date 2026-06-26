from datetime import date
from types import SimpleNamespace

from app.services.event_calendar_tool_service import EventCalendarToolService

svc = EventCalendarToolService()


def test_no_event_returns_not_detected():
    result = svc.detect_event(None, date(2026, 1, 1))

    assert result == {
        "event_detected": False,
        "event_type": None,
        "days_until_event": None,
        "base_event_impact": None,
    }


def test_future_event_has_positive_days_until_event():
    event = SimpleNamespace(event_type="BLACK_FRIDAY", start_date=date(2026, 11, 20), base_impact_score=0.95)
    result = svc.detect_event(event, today=date(2026, 11, 10))

    assert result["event_detected"] is True
    assert result["event_type"] == "BLACK_FRIDAY"
    assert result["days_until_event"] == 10
    assert result["base_event_impact"] == 0.95


def test_active_event_has_non_positive_days_until_event():
    event = SimpleNamespace(event_type="BLACK_FRIDAY", start_date=date(2026, 11, 20), base_impact_score=0.95)
    result = svc.detect_event(event, today=date(2026, 11, 25))

    assert result["event_detected"] is True
    assert result["days_until_event"] == -5
