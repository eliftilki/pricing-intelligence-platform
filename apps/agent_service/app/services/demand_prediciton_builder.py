from __future__ import annotations

"""
Graph state parcalarini ML servisinin bekledigi feature satirlarina cevirir.
HTTP ve DB yok; node state'i DemandPredictionBuildContext'e paketleyip service'e verir.
"""

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.schemas.demand_prediction_schema import (
    DemandFeatureRow,
    DemandPredictionRequest,
)

# Rakip tier filtrelemesi — FeatureEngineeringService ile ayni kural.
_EXCLUDED_TIER_STRINGS = {"NOISE", "TIER_3", "TIER3"}

# Egitim verisindeki event_type_id kodlari (final_training_dataset.csv ile uyumlu).
# event_detected=0 iken her zaman 0.0 kullanilir.
# Yeni event tipi eklendiginde bu sozluk ve egitim ETL'i birlikte guncellenmeli.
EVENT_TYPE_TO_ID: dict[str, float] = {
    "NEW_YEAR": 1.0,
    "VALENTINES_DAY": 1.0,
    "BACK_TO_SCHOOL": 1.0,
    "RAMADAN": 1.0,
    "EID_AL_ADHA": 1.0,
    "MOTHERS_DAY": 1.0,
    "FATHERS_DAY": 1.0,
    "SINGLES_DAY": 2.0,
    "BLACK_FRIDAY": 3.0,
    "YEAR_END": 4.0,
}


@dataclass(frozen=True)
class DemandPredictionBuildContext:
    """
    demand_prediction_node state'ten urettigi giris paketi.
    Builder ham state dict gormez; sadece bu context ile calisir.
    """

    candidate_prices: list[float]
    pricing_features: dict[str, Any]
    market_event_features: dict[str, Any] | None = None
    # Frontend / satıcıdan gelen son 7 gunluk ortalama satis (API -> state -> node).
    sales_7d_avg: float | None = None
    stock_quantity: int | None = None
    product_id: str | None = None
    category: str | None = None
    # Opsiyonel: feature_engineering_node'un DB'den okudugu ham rakip listesi.
    # tier1_competitor_count ve competitor_aggression_score buradan turetilir.
    competitor_features: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class _SharedFeatureSnapshot:
    """Aday fiyat dongusu oncesi bir kez hesaplanan ortak degerler."""

    # Ayni urun-gun icin tum aday fiyatlarda ortak; sadece candidate_price degisir.
    product_id: int
    category: str
    month: int
    is_weekend: int
    is_salary_week: int
    min_competitor_price: float
    avg_competitor_price: float
    market_avg_price: float
    market_price_trend_7d: float
    market_volatility_7d: float
    competitor_count: int
    tier1_competitor_count: int
    market_pressure_score: float
    competitor_aggression_score: float
    trend_score: float
    interest_change_7d: float
    interest_change_30d: float
    event_detected: float
    event_type_id: float
    days_until_event: float
    event_confidence: float
    category_demand_change: float
    recommended_demand_multiplier: float
    sales_7d_avg: float
    stock_quantity: int
    stock_bucket: str


class DemandPredictionBuilder:
    """
    Pipeline state parcalarini ML servisinin bekledigi DemandFeatureRow
    formatina cevirir.

    Sorumluluk: mapping / turetme.
    Yapmaz: HTTP, DB, graph orchestration.
    """

    def build_feature_rows(
        self,
        context: DemandPredictionBuildContext,
    ) -> list[DemandFeatureRow]:
        if not context.candidate_prices:
            raise ValueError("candidate_prices is empty.")

        if not context.pricing_features:
            raise ValueError("pricing_features is missing.")

        shared = self._build_shared_snapshot(context)

        # Her aday fiyat icin ayri ML satiri (egitim verisi de boyle).
        return [
            self._build_row_for_candidate_price(
                candidate_price=float(price),
                shared=shared,
            )
            for price in context.candidate_prices
        ]

    def build_request(
        self,
        context: DemandPredictionBuildContext,
    ) -> DemandPredictionRequest:
        return DemandPredictionRequest(items=self.build_feature_rows(context))

    def _build_shared_snapshot(
        self,
        context: DemandPredictionBuildContext,
    ) -> _SharedFeatureSnapshot:
        pricing = context.pricing_features
        market = context.market_event_features or {}

        reference_date = _resolve_reference_date(pricing)

        min_price = _to_float(pricing.get("min_competitor_price"), 0.0)
        avg_price = _to_float(pricing.get("avg_competitor_price"), min_price)
        market_avg_price = _to_float(
            pricing.get("weighted_avg_competitor_price"),
            avg_price,
        )

        stock_quantity = _resolve_stock_quantity(context, pricing)
        category = _resolve_category(context, market)
        tier1_count, aggression_score = _resolve_competitor_derived_metrics(
            context,
            pricing,
        )

        return _SharedFeatureSnapshot(
            product_id=_resolve_product_id(context.product_id, pricing),
            category=category,
            # Kaynak: pricing_features.generated_at (yoksa UTC simdi).
            month=reference_date.month,
            # Kaynak: pricing_features.is_weekend (feature_engineering zaman ozelligi).
            is_weekend=1 if pricing.get("is_weekend") else 0,
            # Kaynak: referans tarihin ay icindeki gunu (egitim verisi: gun 1-7 -> 1).
            is_salary_week=_resolve_is_salary_week(reference_date),
            min_competitor_price=min_price,
            avg_competitor_price=avg_price,
            market_avg_price=market_avg_price,
            # Kaynak: pricing_features (ileride FE genisletmesi) veya 0.0.
            market_price_trend_7d=_resolve_market_price_trend_7d(pricing),
            market_volatility_7d=_resolve_market_volatility_7d(pricing),
            competitor_count=int(pricing.get("valid_competitor_count") or 0),
            tier1_competitor_count=tier1_count,
            market_pressure_score=_to_float(pricing.get("market_pressure_score"), 0.0),
            competitor_aggression_score=aggression_score,
            # Kaynak: market_event_features (event_agent_node).
            trend_score=_to_float(market.get("trend_score"), 0.0),
            interest_change_7d=_to_float(market.get("interest_change_7d"), 0.0),
            interest_change_30d=_to_float(market.get("interest_change_30d"), 0.0),
            event_detected=1.0 if market.get("event_detected") else 0.0,
            # Kaynak: market_event_features.event_type -> EVENT_TYPE_TO_ID eslemesi.
            event_type_id=_resolve_event_type_id(market),
            days_until_event=_resolve_days_until_event(market),
            event_confidence=_resolve_event_confidence(pricing, market),
            category_demand_change=_to_float(market.get("category_demand_change"), 0.0),
            recommended_demand_multiplier=_resolve_recommended_demand_multiplier(
                pricing,
                market,
            ),
            # Kaynak: context.sales_7d_avg (frontend / satıcı girdisi).
            sales_7d_avg=_resolve_sales_7d_avg(context),
            stock_quantity=stock_quantity,
            # Kaynak: stok miktari -> LOW / MEDIUM / HIGH (egitim verisi ile ayni esikler).
            stock_bucket=_stock_bucket(stock_quantity),
        )

    def _build_row_for_candidate_price(
        self,
        *,
        candidate_price: float,
        shared: _SharedFeatureSnapshot,
    ) -> DemandFeatureRow:
        return DemandFeatureRow(
            product_id=shared.product_id,
            category=shared.category,
            month=shared.month,
            is_weekend=shared.is_weekend,
            is_salary_week=shared.is_salary_week,
            candidate_price=candidate_price,
            min_competitor_price=shared.min_competitor_price,
            avg_competitor_price=shared.avg_competitor_price,
            market_avg_price=shared.market_avg_price,
            market_price_trend_7d=shared.market_price_trend_7d,
            market_volatility_7d=shared.market_volatility_7d,
            competitor_count=shared.competitor_count,
            tier1_competitor_count=shared.tier1_competitor_count,
            # Kaynak: aday fiyat - rakip ozet fiyatlari (candidate_price'a bagli).
            price_gap_to_min=round(candidate_price - shared.min_competitor_price, 2),
            price_gap_to_avg=round(candidate_price - shared.avg_competitor_price, 2),
            price_gap_to_market_avg=round(
                candidate_price - shared.market_avg_price,
                2,
            ),
            price_rank=_estimate_price_rank(
                candidate_price,
                shared.min_competitor_price,
                shared.avg_competitor_price,
            ),
            market_pressure_score=shared.market_pressure_score,
            competitor_aggression_score=shared.competitor_aggression_score,
            trend_score=shared.trend_score,
            interest_change_7d=shared.interest_change_7d,
            interest_change_30d=shared.interest_change_30d,
            event_detected=shared.event_detected,
            event_type_id=shared.event_type_id,
            days_until_event=shared.days_until_event,
            event_confidence=shared.event_confidence,
            category_demand_change=shared.category_demand_change,
            recommended_demand_multiplier=shared.recommended_demand_multiplier,
            sales_7d_avg=shared.sales_7d_avg,
            stock_quantity=shared.stock_quantity,
            stock_bucket=shared.stock_bucket,
        )


# GECICI: Frontend baglaninca kaldirilacak varsayilan (model test icin).
_TEMP_SALES_7D_AVG_DEFAULT = 5.33


def _resolve_sales_7d_avg(context: DemandPredictionBuildContext) -> float:
    if context.sales_7d_avg is not None:
        return float(context.sales_7d_avg)
    # GECICI: API/frontend henuz yoksa sabit deger; production'da kaldirilmali.
    return _TEMP_SALES_7D_AVG_DEFAULT


def _resolve_reference_date(pricing_features: dict[str, Any]) -> datetime:
    generated_at = pricing_features.get("generated_at")
    if isinstance(generated_at, str) and generated_at:
        try:
            return datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _resolve_is_salary_week(reference_date: datetime) -> int:
    # Egitim verisinde maas haftasi: ayin 1-7. gunleri -> 1, aksi halde 0.
    return 1 if 1 <= reference_date.day <= 7 else 0


def _resolve_event_type_id(market_event_features: dict[str, Any]) -> float:
    if not market_event_features.get("event_detected"):
        return 0.0

    raw_id = market_event_features.get("event_type_id")
    if raw_id is not None:
        return float(raw_id)

    event_type = market_event_features.get("event_type")
    if not event_type:
        return 0.0

    return EVENT_TYPE_TO_ID.get(str(event_type).upper(), 0.0)


def _resolve_market_price_trend_7d(pricing_features: dict[str, Any]) -> float:
    # Oncelik: feature_engineering ciktisina eklenecek alan (fiyat gecmisi gerektirir).
    if pricing_features.get("market_price_trend_7d") is not None:
        return _to_float(pricing_features.get("market_price_trend_7d"), 0.0)
    return 0.0


def _resolve_market_volatility_7d(pricing_features: dict[str, Any]) -> float:
    if pricing_features.get("market_volatility_7d") is not None:
        return _to_float(pricing_features.get("market_volatility_7d"), 0.0)
    return 0.0


def _resolve_competitor_derived_metrics(
    context: DemandPredictionBuildContext,
    pricing_features: dict[str, Any],
) -> tuple[int, float]:
    # Oncelik 1: pricing_features'a yazilmis hazir degerler (ileride FE genisletmesi).
    tier1_from_pricing = pricing_features.get("tier1_competitor_count")
    aggression_from_pricing = pricing_features.get("competitor_aggression_score")
    if tier1_from_pricing is not None and aggression_from_pricing is not None:
        return int(tier1_from_pricing), _to_float(aggression_from_pricing, 0.0)

    # Oncelik 2: ham rakip listesinden turet (node context.competitor_features ile besler).
    competitors = _filter_relevant_competitors(
        context.competitor_features or [],
        pricing_features.get("marketplace"),
    )
    priced = [c for c in competitors if _extract_price(c) is not None]
    if not priced:
        return 0, 0.0

    tier1_count = sum(1 for c in priced if str(c.get("tier", "")).upper() == "TIER_1")
    aggression_scores = [
        float(c.get("price_aggression_score") or 0.0) for c in priced
    ]
    aggression = round(statistics.mean(aggression_scores), 2) if aggression_scores else 0.0
    return tier1_count, aggression


def _filter_relevant_competitors(
    competitors: list[dict[str, Any]],
    marketplace: str | None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for competitor in competitors:
        if _is_excluded_tier(competitor.get("tier")):
            continue
        if competitor.get("is_in_stock") is False:
            continue
        competitor_marketplace = competitor.get("marketplace")
        if (
            marketplace
            and competitor_marketplace
            and str(competitor_marketplace).upper() != str(marketplace).upper()
        ):
            continue
        filtered.append(competitor)
    return filtered


def _is_excluded_tier(tier: Any) -> bool:
    if tier is None:
        return True
    return str(tier).upper() in _EXCLUDED_TIER_STRINGS


def _extract_price(competitor: dict[str, Any]) -> float | None:
    price = competitor.get("price")
    if price is None:
        return None
    try:
        return float(price)
    except (TypeError, ValueError):
        return None


def _resolve_product_id(
    product_id: str | None,
    pricing_features: dict[str, Any],
) -> int:
    raw = product_id or pricing_features.get("product_id")
    if raw is None:
        return 1

    try:
        return int(str(raw))
    except ValueError:
        return abs(hash(str(raw))) % 1_000_000


def _resolve_category(
    context: DemandPredictionBuildContext,
    market_event_features: dict[str, Any],
) -> str:
    if context.category:
        return context.category
    if market_event_features.get("category"):
        return str(market_event_features["category"])
    return "UNKNOWN"


def _resolve_stock_quantity(
    context: DemandPredictionBuildContext,
    pricing_features: dict[str, Any],
) -> int:
    if context.stock_quantity is not None:
        return int(context.stock_quantity)
    if pricing_features.get("stock_quantity") is not None:
        return int(pricing_features["stock_quantity"])
    return 0


def _resolve_days_until_event(market_event_features: dict[str, Any]) -> float:
    value = market_event_features.get("days_until_event")
    if value is None:
        return 999.0
    return float(value)


def _resolve_event_confidence(
    pricing_features: dict[str, Any],
    market_event_features: dict[str, Any],
) -> float:
    if market_event_features.get("event_confidence") is not None:
        return _to_float(market_event_features.get("event_confidence"), 0.0)
    return _to_float(pricing_features.get("event_confidence"), 0.0)


def _resolve_recommended_demand_multiplier(
    pricing_features: dict[str, Any],
    market_event_features: dict[str, Any],
) -> float:
    if market_event_features.get("recommended_demand_multiplier") is not None:
        return _to_float(market_event_features.get("recommended_demand_multiplier"), 1.0)
    return _to_float(pricing_features.get("recommended_demand_multiplier"), 1.0)


def _estimate_price_rank(
    candidate_price: float,
    min_competitor_price: float,
    avg_competitor_price: float,
) -> int:
    # Basitlestirilmis siralama; tam rank icin tum rakip fiyat listesi gerekir.
    if candidate_price <= min_competitor_price:
        return 1
    if candidate_price <= avg_competitor_price:
        return 5
    return 10


def _stock_bucket(stock_quantity: int) -> str:
    if stock_quantity >= 80:
        return "HIGH"
    if stock_quantity >= 40:
        return "MEDIUM"
    return "LOW"


def _to_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default