from datetime import date

from app.models.market_event import EventCalendar


class EventCalendarToolService:
    """
    Tool 2 - Event Calendar Tool. Pure: DB'ye dokunmaz, sadece
    MarketIntelligenceRepository.get_active_event'in dondurdugu satiri
    (varsa) gunluk bir ciktiya cevirir.
    """

    def detect_event(self, event: EventCalendar | None, today: date) -> dict:
        if event is None:
            return {
                "event_detected": False,
                "event_type": None,
                "days_until_event": None,
                "base_event_impact": None,
            }

        days_until_event = (event.start_date - today).days

        return {
            "event_detected": True,
            "event_type": event.event_type,
            "days_until_event": days_until_event,
            "base_event_impact": float(event.base_impact_score),
        }
