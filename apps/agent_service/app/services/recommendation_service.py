from __future__ import annotations

from typing import Any, Optional

# competitor_tiers.tier kolonu ile ayni kural (feature_engineering_service'teki
# tier filtrelemesiyle tutarli).
_TIER_1 = "TIER_1"


class RecommendationService:
    """
    optimization_node ciktisini (optimization_result) + pricing_features +
    rakip listesini birlestirip tekil bir "recommendation" objesi uretir.
    DB'ye dokunmaz, yan etkisizdir (pure) - feature_engineering_service ile
    ayni desen.
    """

    def build_recommendation(
        self,
        *,
        optimization_result: dict[str, Any],
        pricing_features: dict[str, Any],
        product_name: Optional[str],
        risk_assessment: Optional[dict[str, Any]],
        competitor_features: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        best = self._select_best_marketplace_result(optimization_result)

        if best is None or best.get("recommended_price") is None:
            return None

        risk_assessment = risk_assessment or {}

        return {
            "product_name": product_name or "Unknown Product",
            "marketplace": best.get("marketplace"),
            "seller_product_id": best.get("seller_product_id"),
            "current_price": best.get("current_price"),
            "recommended_price": best.get("recommended_price"),
            "action": self._resolve_action(best.get("current_price"), best.get("recommended_price")),
            "expected_sales": best.get("expected_sales"),
            "unit_profit": best.get("unit_profit"),
            "expected_profit": best.get("expected_profit"),
            "profit_uplift": best.get("profit_uplift_vs_current"),
            "commission_rate": best.get("commission_rate"),
            "selected_reason": best.get("selected_reason"),
            "reason_codes": best.get("constraints_applied"),
            "competitor_min_price": pricing_features.get("min_competitor_price"),
            "competitor_avg_price": pricing_features.get("avg_competitor_price"),
            "tier1_min_price": self._tier1_min_price(competitor_features),
            # risk_control node'u henuz yok (Sude calisiyor) - eklendiginde
            # state["risk_assessment"] doldurulacak, bu alan otomatik dolacak.
            "risk_level": risk_assessment.get("risk_level"),
        }

    @staticmethod
    def _resolve_action(current_price: Optional[float], recommended_price: float) -> str:
        # price_recommendations.action kolonunda DB CHECK constraint var:
        # sadece PRICE_INCREASE/PRICE_DECREASE/KEEP_PRICE/PROMOTION/MANUAL_REVIEW
        # kabul ediliyor (pg_constraint: price_recommendations_action_check).
        # current_price yoksa (ilk analiz, henuz satis fiyati girilmemis) net
        # bir artis/azalis yonu belirlenemiyor - MANUAL_REVIEW'a dusuruyoruz.
        if current_price is None:
            return "MANUAL_REVIEW"
        if recommended_price > current_price:
            return "PRICE_INCREASE"
        if recommended_price < current_price:
            return "PRICE_DECREASE"
        return "KEEP_PRICE"

    @staticmethod
    def _select_best_marketplace_result(
        optimization_result: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        results = optimization_result.get("marketplace_results") or []
        if not results:
            return None

        best_marketplace = (optimization_result.get("summary") or {}).get("best_marketplace")
        if best_marketplace is not None:
            for result in results:
                if result.get("marketplace") == best_marketplace and result.get("recommended_price") is not None:
                    return result

        for result in results:
            if result.get("recommended_price") is not None:
                return result

        return None

    @staticmethod
    def _tier1_min_price(competitor_features: list[dict[str, Any]]) -> Optional[float]:
        tier1_prices = [
            c["price"]
            for c in competitor_features
            if str(c.get("tier", "")).upper() == _TIER_1 and c.get("price") is not None
        ]
        return min(tier1_prices) if tier1_prices else None


recommendation_service = RecommendationService()
