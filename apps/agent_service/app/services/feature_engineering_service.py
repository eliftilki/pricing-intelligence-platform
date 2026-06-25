from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

# competitor_tiers.tier kolonu string ("TIER_1", "TIER_2", "NOISE") tutar.
# Tier bilinmiyorsa (None) guvenli tarafta kalip rakibi analize dahil etmiyoruz.
_EXCLUDED_TIER_STRINGS = {"NOISE", "TIER_3", "TIER3"}


@dataclass
class PricingFeatures:
    """
    Demand Prediction (XGBoost/LightGBM) modeline ve candidate_price_generator
    dugumune dogrudan beslenecek saf sayisal/zaman bazli feature seti.

    ONEMLI: Bu nesne komisyon_orani, kargo_ucreti, ambalaj_maliyeti,
    min_kar_marji, cost_price gibi IC MALIYET bilgilerini ASLA icermez.
    Bu alanlar Optimization/candidate-price stratejileri asamasina aittir.
    """

    product_id: Optional[str]
    marketplace: Optional[str]
    current_price: Optional[float]
    stock_quantity: Optional[int]

    valid_competitor_count: int
    is_monopoly: bool

    min_competitor_price: Optional[float]
    max_competitor_price: Optional[float]
    avg_competitor_price: Optional[float]
    median_competitor_price: Optional[float]
    weighted_avg_competitor_price: Optional[float]

    price_gap_to_min_pct: Optional[float]
    price_rank: Optional[int]
    market_pressure_score: float

    day_of_week: int
    hour_of_day: int
    is_weekend: bool

    # event_agent_node'un (Market Intelligence Agent) urettigi sinyaller.
    # market_event_features state'i yoksa/bos ise notr varsayilanlar kullanilir.
    recommended_demand_multiplier: float
    event_confidence: float
    market_demand_signal: str

    generated_at: str


class FeatureEngineeringService:
    """
    competitor_tiers + competitor_listings join'inden gelen rakip verisini
    (FeatureEngineeringRepository.get_competitor_features ciktisi) deterministik
    sekilde sayisal feature'lara cevirir. DB'ye dokunmaz, yan etkisizdir (pure).
    """

    def build_features(
        self,
        *,
        product_id: Optional[str],
        marketplace: Optional[str],
        current_price: Optional[float],
        stock_quantity: Optional[int],
        competitor_features: list[dict[str, Any]],
        market_event_features: Optional[dict[str, Any]] = None,
        reference_time: Optional[datetime] = None,
    ) -> PricingFeatures:
        time_features = self._time_features(reference_time or datetime.now(timezone.utc))
        event_features = self._extract_event_features(market_event_features)

        relevant = self._filter_relevant_competitors(competitor_features, marketplace)
        priced = [c for c in relevant if self._extract_price(c) is not None]

        if not priced:
            return self._monopoly_fallback(
                product_id=product_id,
                marketplace=marketplace,
                current_price=current_price,
                stock_quantity=stock_quantity,
                time_features=time_features,
                event_features=event_features,
            )

        prices = [self._extract_price(c) for c in priced]
        weights = [self._extract_weight(c) for c in priced]

        min_price = min(prices)
        max_price = max(prices)
        avg_price = round(statistics.mean(prices), 2)
        median_price = round(statistics.median(prices), 2)
        weighted_avg_price = self._weighted_average(prices, weights)

        return PricingFeatures(
            product_id=product_id,
            marketplace=marketplace,
            current_price=current_price,
            stock_quantity=stock_quantity,
            valid_competitor_count=len(priced),
            is_monopoly=False,
            min_competitor_price=min_price,
            max_competitor_price=max_price,
            avg_competitor_price=avg_price,
            median_competitor_price=median_price,
            weighted_avg_competitor_price=weighted_avg_price,
            price_gap_to_min_pct=self._price_gap_to_min_pct(current_price, min_price),
            price_rank=self._price_rank(current_price, prices),
            market_pressure_score=self._market_pressure_score(priced),
            day_of_week=time_features["day_of_week"],
            hour_of_day=time_features["hour_of_day"],
            is_weekend=time_features["is_weekend"],
            recommended_demand_multiplier=event_features["recommended_demand_multiplier"],
            event_confidence=event_features["event_confidence"],
            market_demand_signal=event_features["market_demand_signal"],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # event_agent_node sinyalleri (Market Intelligence Agent)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_event_features(market_event_features: Optional[dict[str, Any]]) -> dict[str, Any]:
        """
        event_agent_node'un urettigi sinyalleri notr varsayilanlarla guvenli
        sekilde okur. market_event_features eksik/bos olabilir (event_agent
        hata verdiyse veya hic calismadiysa) - bu durumda "talep normal"
        anlamina gelen notr degerler kullanilir.
        """
        market_event_features = market_event_features or {}

        multiplier = market_event_features.get("recommended_demand_multiplier")
        confidence = market_event_features.get("event_confidence")
        signal = market_event_features.get("market_demand_signal")

        return {
            "recommended_demand_multiplier": 1.0 if multiplier is None else multiplier,
            "event_confidence": 0.0 if confidence is None else confidence,
            "market_demand_signal": "LOW" if signal is None else signal,
        }

    # ------------------------------------------------------------------
    # Filtreleme: pazar yeri eslesmesi + stok + NOISE/TIER_3 disarida birakma
    # ------------------------------------------------------------------

    def _filter_relevant_competitors(
        self,
        competitors: list[dict[str, Any]],
        marketplace: Optional[str],
    ) -> list[dict[str, Any]]:
        filtered = []
        for competitor in competitors or []:
            if self._is_excluded_tier(competitor.get("tier")):
                continue
            if competitor.get("is_in_stock") is False:
                continue
            competitor_marketplace = competitor.get("marketplace")
            if (
                marketplace
                and competitor_marketplace
                and competitor_marketplace.upper() != marketplace.upper()
            ):
                continue
            filtered.append(competitor)
        return filtered

    @staticmethod
    def _is_excluded_tier(tier: Any) -> bool:
        if tier is None:
            return True
        return str(tier).upper() in _EXCLUDED_TIER_STRINGS

    @staticmethod
    def _extract_price(competitor: dict[str, Any]) -> Optional[float]:
        price = competitor.get("price")
        if price is None:
            return None
        try:
            return float(price)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_weight(competitor: dict[str, Any]) -> float:
        # Agirlik olarak rakibin guc skoru kullanilir (competitor_strength_score).
        # Yoksa buybox_threat_score'a, o da yoksa esit agirliga (1.0) dusulur.
        weight = competitor.get("competitor_strength_score")
        if weight is None:
            weight = competitor.get("buybox_threat_score")
        if weight is None:
            weight = 1.0
        # Sifir/negatif agirlik bolme hatasini engellemek icin alt limit konur.
        return max(float(weight), 0.01)

    @staticmethod
    def _weighted_average(prices: list[float], weights: list[float]) -> float:
        total_weight = sum(weights)
        if total_weight <= 0:
            return round(statistics.mean(prices), 2)
        weighted_sum = sum(p * w for p, w in zip(prices, weights))
        return round(weighted_sum / total_weight, 2)

    # ------------------------------------------------------------------
    # Fiyat metrikleri
    # ------------------------------------------------------------------

    @staticmethod
    def _price_gap_to_min_pct(
        current_price: Optional[float], min_price: float
    ) -> Optional[float]:
        if current_price is None or not min_price:
            return None
        return round(((current_price - min_price) / min_price) * 100, 2)

    @staticmethod
    def _price_rank(
        current_price: Optional[float], competitor_prices: list[float]
    ) -> Optional[int]:
        """1 = pazardaki en ucuz konum. Esit fiyatlarda ilk siraya yerlestirilir."""
        if current_price is None:
            return None
        all_prices = sorted(competitor_prices + [current_price])
        return all_prices.index(current_price) + 1

    @staticmethod
    def _market_pressure_score(competitors: list[dict[str, Any]]) -> float:
        """
        0-100 arasi composite pazar baskisi skoru. Rakiplerin ortalama buybox
        tehdidi ve fiyat agresifligi ne kadar yuksekse baski o kadar buyuktur.
        """
        if not competitors:
            return 0.0
        threat_scores = [float(c.get("buybox_threat_score") or 0.0) for c in competitors]
        aggression_scores = [float(c.get("price_aggression_score") or 0.0) for c in competitors]
        score = (statistics.mean(threat_scores) * 0.6) + (statistics.mean(aggression_scores) * 0.4)
        return round(min(max(score, 0.0), 100.0), 2)

    # ------------------------------------------------------------------
    # Zaman ozellikleri
    # ------------------------------------------------------------------

    @staticmethod
    def _time_features(now: datetime) -> dict[str, Any]:
        return {
            "day_of_week": now.weekday(),  # 0=Pazartesi ... 6=Pazar
            "hour_of_day": now.hour,
            "is_weekend": now.weekday() >= 5,
        }

    # ------------------------------------------------------------------
    # Monopol / Fallback: gecerli rakip yoksa sistem cokmez
    # ------------------------------------------------------------------

    def _monopoly_fallback(
        self,
        *,
        product_id: Optional[str],
        marketplace: Optional[str],
        current_price: Optional[float],
        stock_quantity: Optional[int],
        time_features: dict[str, Any],
        event_features: dict[str, Any],
    ) -> PricingFeatures:
        return PricingFeatures(
            product_id=product_id,
            marketplace=marketplace,
            current_price=current_price,
            stock_quantity=stock_quantity,
            valid_competitor_count=0,
            is_monopoly=True,
            min_competitor_price=None,
            max_competitor_price=None,
            avg_competitor_price=None,
            median_competitor_price=None,
            weighted_avg_competitor_price=None,
            price_gap_to_min_pct=0.0,
            price_rank=1,
            market_pressure_score=0.0,
            day_of_week=time_features["day_of_week"],
            hour_of_day=time_features["hour_of_day"],
            is_weekend=time_features["is_weekend"],
            recommended_demand_multiplier=event_features["recommended_demand_multiplier"],
            event_confidence=event_features["event_confidence"],
            market_demand_signal=event_features["market_demand_signal"],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


def pricing_features_to_dict(features: PricingFeatures) -> dict[str, Any]:
    return asdict(features)
