from decimal import Decimal
from typing import Any

from app.models.competitor import CompetitorListing


class CompetitorScoringService:
    def safe_float(self, value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def calculate_market_prices(self, listings: list[CompetitorListing]) -> dict:
        prices = [
            self.safe_float(item.price)
            for item in listings
            if item.price is not None and self.safe_float(item.price) > 0
        ]
        if not prices:
            return {"min_price": 0.0, "avg_price": 0.0, "max_price": 0.0}
        return {"min_price": min(prices), "avg_price": sum(prices) / len(prices), "max_price": max(prices)}

    def calculate_price_score(self, price: float, min_price: float, avg_price: float) -> tuple[float, list[str]]:
        reasons = []
        if price <= 0 or min_price <= 0:
            return 0, ["PRICE_DATA_MISSING"]

        gap_to_min = (price - min_price) / min_price
        if gap_to_min <= 0.02:
            score = 35
            reasons.append("PRICE_NEAR_MARKET_MIN")
        elif gap_to_min <= 0.05:
            score = 28
            reasons.append("PRICE_COMPETITIVE")
        elif gap_to_min <= 0.10:
            score = 18
            reasons.append("PRICE_MODERATELY_COMPETITIVE")
        else:
            score = 8
            reasons.append("PRICE_NOT_COMPETITIVE")

        if avg_price > 0 and price < avg_price:
            score += 5
            reasons.append("PRICE_BELOW_MARKET_AVG")
        return min(score, 40), reasons

    def calculate_seller_trust_score(self, listing: CompetitorListing) -> tuple[float, list[str]]:
        score = 0
        reasons = []
        seller_score = self.safe_float(listing.seller_score)
        review_count = listing.seller_review_count or 0

        if seller_score >= 9:
            score += 20
            reasons.append("VERY_HIGH_SELLER_SCORE")
        elif seller_score >= 8:
            score += 16
            reasons.append("HIGH_SELLER_SCORE")
        elif seller_score >= 7:
            score += 10
            reasons.append("AVERAGE_SELLER_SCORE")
        elif seller_score > 0:
            score += 4
            reasons.append("LOW_SELLER_SCORE")
        else:
            score += 6
            reasons.append("SELLER_SCORE_UNKNOWN")

        if review_count >= 1000:
            score += 15
            reasons.append("HIGH_SELLER_REVIEW_COUNT")
        elif review_count >= 300:
            score += 10
            reasons.append("GOOD_SELLER_REVIEW_COUNT")
        elif review_count >= 50:
            score += 5
            reasons.append("LIMITED_SELLER_REVIEW_COUNT")
        else:
            score += 2
            reasons.append("LOW_SELLER_REVIEW_COUNT")

        if listing.is_authorized:
            score += 10
            reasons.append("AUTHORIZED_SELLER")
        return min(score, 45), reasons

    def calculate_delivery_score(self, listing: CompetitorListing) -> tuple[float, list[str]]:
        score = 0
        reasons = []
        if listing.free_shipping:
            score += 5
            reasons.append("FREE_SHIPPING")
        if listing.fast_shipping:
            score += 7
            reasons.append("FAST_SHIPPING")
        if listing.shipment_days is not None:
            if listing.shipment_days <= 1:
                score += 8
                reasons.append("ONE_DAY_DELIVERY")
            elif listing.shipment_days <= 2:
                score += 5
                reasons.append("FAST_DELIVERY")
            elif listing.shipment_days >= 5:
                score -= 3
                reasons.append("SLOW_DELIVERY")
        return max(0, min(score, 20)), reasons

    def calculate_stock_score(self, listing: CompetitorListing) -> tuple[float, list[str]]:
        if listing.is_in_stock is False:
            return -30, ["OUT_OF_STOCK"]
        if listing.stock is None:
            return 5, ["STOCK_UNKNOWN"]
        if listing.stock >= 50:
            return 10, ["HIGH_STOCK"]
        if listing.stock >= 10:
            return 6, ["NORMAL_STOCK"]
        if listing.stock > 0:
            return 2, ["LOW_STOCK"]
        return -30, ["OUT_OF_STOCK"]

    def calculate_competitor_strength_score(self, listing: CompetitorListing, min_price: float, avg_price: float) -> tuple[float, list[str]]:
        price_score, price_reasons = self.calculate_price_score(self.safe_float(listing.price), min_price, avg_price)
        trust_score, trust_reasons = self.calculate_seller_trust_score(listing)
        delivery_score, delivery_reasons = self.calculate_delivery_score(listing)
        stock_score, stock_reasons = self.calculate_stock_score(listing)
        score = max(0, min(price_score + trust_score + delivery_score + stock_score, 100))
        return score, price_reasons + trust_reasons + delivery_reasons + stock_reasons

    def calculate_price_aggression_score(self, listing: CompetitorListing, min_price: float, avg_price: float, price_history_summary: dict) -> tuple[float, list[str]]:
        reasons = []
        price = self.safe_float(listing.price)
        if price <= 0 or avg_price <= 0:
            return 0, ["PRICE_AGGRESSION_DATA_MISSING"]

        discount_vs_avg = (avg_price - price) / avg_price
        if discount_vs_avg >= 0.10:
            score = 90
            reasons.append("VERY_AGGRESSIVE_PRICE")
        elif discount_vs_avg >= 0.05:
            score = 70
            reasons.append("AGGRESSIVE_PRICE")
        elif discount_vs_avg >= 0.02:
            score = 50
            reasons.append("MODERATELY_AGGRESSIVE_PRICE")
        else:
            score = 25
            reasons.append("NORMAL_PRICE_BEHAVIOR")

        if min_price > 0 and price <= min_price * 1.02:
            score += 10
            reasons.append("NEAR_LOWEST_MARKET_PRICE")

        historical_avg = self.safe_float(price_history_summary.get("avg_price"))
        if historical_avg > 0:
            price_drop_vs_history = (historical_avg - price) / historical_avg
            if price_drop_vs_history >= 0.08:
                score += 10
                reasons.append("PRICE_DROP_VS_HISTORY")

        return max(0, min(score, 100)), reasons

    def calculate_buybox_threat_score(self, listing: CompetitorListing, strength_score: float) -> tuple[float, list[str]]:
        reasons = []
        score = strength_score * 0.45
        if listing.rank == 1:
            score += 35
            reasons.append("RANK_1_BUYBOX_LIKE_POSITION")
        elif listing.rank == 2:
            score += 20
            reasons.append("RANK_2_STRONG_VISIBILITY")
        elif listing.rank == 3:
            score += 12
            reasons.append("RANK_3_VISIBLE_COMPETITOR")
        if listing.fast_shipping:
            score += 8
            reasons.append("BUYBOX_FAST_SHIPPING_ADVANTAGE")
        if listing.free_shipping:
            score += 5
            reasons.append("BUYBOX_FREE_SHIPPING_ADVANTAGE")
        return max(0, min(score, 100)), reasons

    def assign_tier(self, listing: CompetitorListing, strength_score: float, buybox_threat_score: float, price_aggression_score: float) -> tuple[str, list[str]]:
        if listing.is_in_stock is False:
            return "NOISE", ["OUT_OF_STOCK_SELLER"]
        seller_score = self.safe_float(listing.seller_score)
        review_count = listing.seller_review_count or 0
        if seller_score > 0 and seller_score < 6 and review_count < 50:
            return "NOISE", ["LOW_TRUST_SELLER"]
        if strength_score >= 75 or buybox_threat_score >= 75:
            return "TIER_1", ["HIGH_IMPACT_COMPETITOR"]
        if strength_score >= 45 or price_aggression_score >= 60:
            return "TIER_2", ["MEDIUM_IMPACT_COMPETITOR"]
        return "NOISE", ["LOW_IMPACT_COMPETITOR"]
