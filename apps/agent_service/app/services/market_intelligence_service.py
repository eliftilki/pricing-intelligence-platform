from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.market_event import MarketEventFeatures
from app.repositories.market_intelligence_repository import MarketIntelligenceRepository
from app.services.category_analyzer_tool_service import CategoryAnalyzerToolService
from app.services.event_calendar_tool_service import EventCalendarToolService
from app.services.market_intelligence_scoring_service import MarketIntelligenceScoringService
from app.services.trend_tool_service import GoogleTrendsToolService

CACHE_TTL_HOURS = 48


class MarketIntelligenceService:
    """
    Market Intelligence Agent orchestrator'i. competitor_intelligence_service
    ile ayni kalip: agent_run loglar, repository + 3 tool + scoring service'i
    sirayla cagirir, market_event_features tablosuna yazar, hata durumunda
    pipeline'i dusurmeden FAILED sonuc doner.
    """

    def __init__(self, db: Session):
        self.repository = MarketIntelligenceRepository(db)
        self.trend_tool = GoogleTrendsToolService()
        self.event_calendar_tool = EventCalendarToolService()
        self.category_analyzer_tool = CategoryAnalyzerToolService()
        self.scoring_service = MarketIntelligenceScoringService()

    def analyze_market_signals(self, product_id: UUID) -> dict:
        agent_run = self.repository.create_agent_run(
            product_id=product_id,
            input_payload={"product_id": str(product_id)},
        )

        try:
            product = self.repository.get_product(product_id)
            if product is None:
                raise ValueError("Product not found.")

            cached = self.repository.get_fresh_market_event_features(product_id, CACHE_TTL_HOURS)
            if cached is not None:
                result = self._row_to_result(cached, from_cache=True)
                self.repository.finish_agent_run(agent_run, "SUCCESS", output_payload=self._serialize_result(result))
                self.repository.commit()
                return result

            features = self._compute_fresh_features(product)

            row = self.repository.create_market_event_features(
                product_id=product_id,
                category=product.category,
                **features,
                generated_at=datetime.now(timezone.utc),
            )

            result = self._row_to_result(row, from_cache=False)
            self.repository.finish_agent_run(agent_run, "SUCCESS", output_payload=self._serialize_result(result))
            self.repository.commit()
            return result

        except Exception as exc:
            self.repository.rollback()
            return {
                "product_id": product_id,
                "status": "FAILED",
                "message": str(exc),
                "from_cache": False,
                **self._neutral_signals(),
            }

    def _compute_fresh_features(self, product) -> dict:
        category = product.category

        trend_result = self.trend_tool.get_interest(product.name)

        active_event = self.repository.get_active_event(category)
        event_result = self.event_calendar_tool.detect_event(active_event, datetime.now(timezone.utc).date())
        # get_active_event kategori eslesmesini zaten DB seviyesinde yapiyor
        # (category=None ise hep None doner) - donen event varsa kategoriyle
        # eslesmistir demektir.
        event_category_match = active_event is not None

        peer_products = self.repository.get_category_peer_products(category, exclude_product_id=product.id)
        peer_trend_results = [self._get_peer_trend(peer) for peer in peer_products]
        category_result = self.category_analyzer_tool.analyze(peer_trend_results)

        signals = self.scoring_service.compute(
            trend=trend_result,
            event=event_result,
            category=category_result,
            event_category_match=event_category_match,
        )

        return {
            "trend_score": trend_result["trend_score"],
            "interest_change_7d": trend_result["interest_change_7d"],
            "interest_change_30d": trend_result["interest_change_30d"],
            "event_detected": event_result["event_detected"],
            "event_type": event_result["event_type"],
            "days_until_event": event_result["days_until_event"],
            "base_event_impact": event_result["base_event_impact"],
            "category_trend_score": category_result["category_trend_score"],
            "category_demand_change": category_result["category_demand_change"],
            "event_confidence": signals["event_confidence"],
            "recommended_demand_multiplier": signals["recommended_demand_multiplier"],
            "market_demand_signal": signals["market_demand_signal"],
            "reason_codes": signals["reason_codes"],
        }

    def _get_peer_trend(self, peer) -> dict:
        """
        Peer urun yakin zamanda (ana urun olarak) zaten analiz edilmisse,
        onun icin uretilmis trend verisini tekrar Google'a gitmeden, mevcut
        market_event_features satirindan okur. Boylece ayni kategorideki
        urunler birbirini sorgularken Google'a giden istek sayisi azalir
        (rate-limit riski + gecikme dususu). Sadece OKUMA yapar, bu peer
        icin yeni bir satir yazmaz - cache tablosunun "tam analiz" anlamini
        bozmamak icin.
        """
        cached = self.repository.get_fresh_market_event_features(peer.id, CACHE_TTL_HOURS)
        if cached is not None and cached.trend_score is not None:
            return {
                "trend_score": self._to_float(cached.trend_score),
                "interest_change_7d": self._to_float(cached.interest_change_7d),
                "interest_change_30d": self._to_float(cached.interest_change_30d),
            }
        return self.trend_tool.get_interest(peer.name)

    def _row_to_result(self, row: MarketEventFeatures, from_cache: bool) -> dict:
        return {
            "product_id": row.product_id,
            "status": "SUCCESS",
            "from_cache": from_cache,
            "category": row.category,
            "trend_score": self._to_float(row.trend_score),
            "interest_change_7d": self._to_float(row.interest_change_7d),
            "interest_change_30d": self._to_float(row.interest_change_30d),
            "event_detected": row.event_detected,
            "event_type": row.event_type,
            "days_until_event": row.days_until_event,
            "event_confidence": self._to_float(row.event_confidence),
            "category_trend_score": self._to_float(row.category_trend_score),
            "category_demand_change": self._to_float(row.category_demand_change),
            "market_demand_signal": row.market_demand_signal,
            "recommended_demand_multiplier": self._to_float(row.recommended_demand_multiplier),
            "reason_codes": row.reason_codes or [],
            "generated_at": row.generated_at.isoformat(),
        }

    def _neutral_signals(self) -> dict:
        return {
            "trend_score": None,
            "interest_change_7d": None,
            "interest_change_30d": None,
            "event_detected": False,
            "event_type": None,
            "days_until_event": None,
            "event_confidence": 0.0,
            "category_trend_score": None,
            "category_demand_change": None,
            "market_demand_signal": "LOW",
            "recommended_demand_multiplier": 1.0,
            "reason_codes": [],
        }

    def _serialize_result(self, result: dict) -> dict:
        serialized = dict(result)
        serialized["product_id"] = str(serialized["product_id"])
        return serialized

    @staticmethod
    def _to_float(value):
        return float(value) if value is not None else None
