from typing import Optional


class MarketIntelligenceScoringService:
    """
    3 tool ciktisini (trend, event, category) birlestirip Market Intelligence
    Agent'in nihai sinyallerini (event_confidence, recommended_demand_multiplier,
    market_demand_signal, reason_codes) ureten pure servis. DB/ag cagrisi yapmaz.

    ONEMLI: Asagidaki esikler/agirliklar (0.3, 0.15, 0.10, 0.20 vb.) ilk
    versiyon icin elle secilmis heuristic degerlerdir, gercek veriyle
    kalibre edilmemistir. ML modeli olgunlastiginda bu sabit agirliklar yerine
    modelin kendisi ham feature'lari (trend_score, category_demand_change,
    event_confidence) ayri ayri gorup kendi icinde agirliklandirmasi beklenir
    - recommended_demand_multiplier sadece bir baseline/convenience feature'dir.
    """

    INTEREST_CHANGE_THRESHOLD = 0.3
    CATEGORY_DEMAND_THRESHOLD = 0.3
    EVENT_PROXIMITY_DAYS = 7

    TREND_WEIGHT = 0.15
    CATEGORY_WEIGHT = 0.10
    EVENT_WEIGHT = 0.20

    HIGH_SIGNAL_THRESHOLD = 1.15
    MEDIUM_SIGNAL_THRESHOLD = 1.05

    def compute(
        self,
        trend: dict,
        event: dict,
        category: dict,
        event_category_match: bool,
    ) -> dict:
        reason_codes: list[str] = []

        interest_change_7d = trend.get("interest_change_7d")
        category_demand_change = category.get("category_demand_change")

        if interest_change_7d is not None and interest_change_7d > self.INTEREST_CHANGE_THRESHOLD:
            reason_codes.append("PRODUCT_INTEREST_UP_7D")

        if category_demand_change is not None and category_demand_change > self.CATEGORY_DEMAND_THRESHOLD:
            reason_codes.append("CATEGORY_DEMAND_UP")

        if event.get("event_detected"):
            days_until_event = event.get("days_until_event")
            if days_until_event is not None and days_until_event <= self.EVENT_PROXIMITY_DAYS:
                reason_codes.append("EVENT_WITHIN_7_DAYS")
            if event_category_match:
                reason_codes.append("EVENT_CATEGORY_MATCH")

        event_confidence = self._event_confidence(event)
        recommended_demand_multiplier = self._demand_multiplier(
            interest_change_7d=interest_change_7d,
            category_demand_change=category_demand_change,
            event_confidence=event_confidence,
        )

        return {
            "event_confidence": event_confidence,
            "recommended_demand_multiplier": recommended_demand_multiplier,
            "market_demand_signal": self._bucket(recommended_demand_multiplier),
            "reason_codes": reason_codes,
        }

    def _event_confidence(self, event: dict) -> float:
        if not event.get("event_detected"):
            return 0.0

        base_impact = event.get("base_event_impact") or 0.0
        days_until_event = event.get("days_until_event")

        return round(base_impact * self._proximity_weight(days_until_event), 4)

    def _proximity_weight(self, days_until_event: Optional[int]) -> float:
        """
        Kampanyaya ne kadar yakinsa o kadar guvenilir. days_until_event <= 0
        ise kampanya zaten aktif (en yuksek agirlik). Bu esikler heuristic,
        gercek satis verisiyle kalibre edilmedi.
        """
        if days_until_event is None:
            return 0.0
        if days_until_event <= 0:
            return 1.0
        if days_until_event <= 7:
            return 0.8
        if days_until_event <= 14:
            return 0.5
        if days_until_event <= 30:
            return 0.2
        return 0.0

    def _demand_multiplier(
        self,
        interest_change_7d: Optional[float],
        category_demand_change: Optional[float],
        event_confidence: float,
    ) -> float:
        multiplier = 1.0
        multiplier += self.TREND_WEIGHT * (interest_change_7d or 0.0)
        multiplier += self.CATEGORY_WEIGHT * (category_demand_change or 0.0)
        multiplier += self.EVENT_WEIGHT * event_confidence
        return round(multiplier, 4)

    def _bucket(self, multiplier: float) -> str:
        if multiplier >= self.HIGH_SIGNAL_THRESHOLD:
            return "HIGH"
        if multiplier >= self.MEDIUM_SIGNAL_THRESHOLD:
            return "MEDIUM"
        return "LOW"
