from decimal import Decimal
import math
from typing import Any

from app.models.competitor import CompetitorListing


class CompetitorScoringService:
    KNOWN_STRONG_SELLERS: set[str] = {
        "amazon",
        "mediamarkt",
        "teknosa",
        "hepsiburada",
        "vatan",
        "itopya",
    }

    def safe_float(self, value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def is_known_strong_seller(self, seller_name: str | None) -> bool:
        if not seller_name:
            return False
        normalized_name = seller_name.lower()
        return any(
            strong_seller in normalized_name
            for strong_seller in self.KNOWN_STRONG_SELLERS
        )

    def calculate_market_prices(
        self,
        listings: list[CompetitorListing],
    ) -> dict[str, float]:
        prices: list[float] = []
        for item in listings:
            if item.price is not None:
                p_float = self.safe_float(item.price)
                if p_float > 0:
                    prices.append(p_float)

        if not prices:
            return {"min_price": 0.0, "avg_price": 0.0, "max_price": 0.0}

        return {
            "min_price": min(prices),
            "avg_price": sum(prices) / len(prices),
            "max_price": max(prices),
        }

    def calculate_price_score(
        self,
        price: float,
        min_price: float,
        avg_price: float,
    ) -> tuple[float, list[str]]:
        if price <= 0 or min_price <= 0.01:
            return 0.0, ["PRICE_DATA_MISSING"]

        reasons: list[str] = []
        score = 0.0

        if price < min_price:
            score = 38.0
            reasons.append("UNDERCUTTING_MARKET_MIN (AGGRESSIVE)")
        else:
            gap_to_min = (price - min_price) / min_price
            if gap_to_min <= 0.02:
                score = 35.0
                reasons.append("PRICE_NEAR_MARKET_MIN")
            elif gap_to_min <= 0.05:
                score = 28.0
                reasons.append("PRICE_COMPETITIVE")
            elif gap_to_min <= 0.10:
                score = 18.0
                reasons.append("PRICE_MODERATELY_COMPETITIVE")
            else:
                score = 8.0
                reasons.append("FAR_FROM_MARKET_MIN_PRICE")

        if avg_price > 0.01 and price < avg_price:
            discount_ratio = (avg_price - price) / avg_price
            if discount_ratio >= 0.10:
                score += 8.0
                reasons.append("PRICE_SIGNIFICANTLY_BELOW_MARKET_AVG")
            else:
                score += 4.0
                reasons.append("PRICE_BELOW_MARKET_AVG")

        return min(score, 45.0), reasons

    def calculate_seller_trust_score(
        self,
        listing: CompetitorListing,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        seller_score = self.safe_float(listing.seller_score, default=0.0)
        review_count = listing.seller_review_count

        if self.is_known_strong_seller(listing.seller_name):
            score += 10
            reasons.append("KNOWN_STRONG_SELLER")

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
            reasons.append("SELLER_SCORE_UNKNOWN")

        if review_count is None:
            reasons.append("REVIEW_COUNT_UNKNOWN")
        else:
            review_score = min(math.log2(review_count + 1) * 1.35, 15.0)
            score += review_score

            if review_count >= 5000:
                reasons.append("VERY_HIGH_SELLER_REVIEW_COUNT")
            elif review_count >= 1250:
                reasons.append("HIGH_SELLER_REVIEW_COUNT")
            elif review_count >= 312:
                reasons.append("GOOD_SELLER_REVIEW_COUNT")
            elif review_count >= 78:
                reasons.append("MEDIUM_SELLER_REVIEW_COUNT")
            elif review_count >= 20:
                reasons.append("LIMITED_SELLER_REVIEW_COUNT")
            else:
                reasons.append("LOW_SELLER_REVIEW_COUNT")

        if listing.is_authorized:
            score += 5.0
            reasons.append("AUTHORIZED_SELLER")

        return min(score, 50.0), reasons

    def calculate_delivery_score(
        self,
        listing: CompetitorListing,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

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

        return max(0.0, min(score, 20.0)), reasons

    def calculate_stock_score(
        self,
        listing: CompetitorListing,
    ) -> tuple[float, list[str]]:
        if listing.is_in_stock is False:
            return -30.0, ["OUT_OF_STOCK"]

        if listing.stock is None:
            return 0.0, ["STOCK_UNKNOWN"]

        if listing.stock >= 50:
            return 10.0, ["HIGH_STOCK"]
        if listing.stock >= 10:
            return 6.0, ["NORMAL_STOCK"]
        if listing.stock > 0:
            return 2.0, ["LOW_STOCK"]

        return -30.0, ["OUT_OF_STOCK"]

    def calculate_competitor_strength_score(
        self,
        listing: CompetitorListing,
        min_price: float,
        avg_price: float,
    ) -> tuple[float, list[str]]:
        price = self.safe_float(listing.price)

        price_score, price_reasons = self.calculate_price_score(
            price=price, min_price=min_price, avg_price=avg_price
        )
        trust_score, trust_reasons = self.calculate_seller_trust_score(listing)
        delivery_score, delivery_reasons = self.calculate_delivery_score(listing)
        stock_score, stock_reasons = self.calculate_stock_score(listing)

        score = price_score + trust_score + delivery_score + stock_score
        score = max(0.0, min(score, 100.0))

        reasons = price_reasons + trust_reasons + delivery_reasons + stock_reasons
        return score, reasons

    def calculate_price_aggression_score(
        self,
        listing: CompetitorListing,
        min_price: float,
        avg_price: float,
        price_history_summary: dict[str, Any],
    ) -> tuple[float, list[str]]:
        price = self.safe_float(listing.price)
        if price <= 0 or avg_price <= 0.01:
            return 0.0, ["PRICE_AGGRESSION_DATA_MISSING"]

        reasons: list[str] = []
        discount_vs_avg = (avg_price - price) / avg_price

        if discount_vs_avg >= 0.15:
            score = 95.0
            reasons.append("DESTRUCTIVE_PRICE_DUMPING")
        elif discount_vs_avg >= 0.08:
            score = 75.0
            reasons.append("VERY_AGGRESSIVE_PRICE")
        elif discount_vs_avg >= 0.03:
            score = 50.0
            reasons.append("MODERATELY_AGGRESSIVE_PRICE")
        else:
            score = 20.0
            reasons.append("NORMAL_PRICE_BEHAVIOR")

        if min_price > 0 and price < min_price:
            score += 15.0
            reasons.append("ABSOLUTE_LOWEST_MARKET_PRICE")
        elif min_price > 0 and price <= min_price * 1.02:
            score += 8.0
            reasons.append("NEAR_LOWEST_MARKET_PRICE")

        historical_avg = self.safe_float(price_history_summary.get("avg_price"))
        if historical_avg > 0.01:
            price_drop_vs_history = (historical_avg - price) / historical_avg
            if price_drop_vs_history >= 0.12:
                score += 10.0
                reasons.append("SHARP_PRICE_DROP_VS_HISTORY")
            elif price_drop_vs_history >= 0.05:
                score += 5.0
                reasons.append("PRICE_DROP_VS_HISTORY")

        return max(0.0, min(score, 100.0)), reasons

    def calculate_buybox_threat_score(
        self,
        listing: CompetitorListing,
        strength_score: float,
        our_price: float | None = None,
        price_aggression_score: float | None = None,
    ) -> tuple[float, list[str]]:
        reasons: list[str] = []
        competitor_price = self.safe_float(listing.price)
        score = strength_score * 0.40

        if price_aggression_score is not None:
            score += price_aggression_score * 0.15
            if price_aggression_score >= 70:
                reasons.append("BUYBOX_PRICE_PRESSURE")

        if listing.rank == 1:
            score += 20.0
            reasons.append("RANK_1_BUYBOX_POSITION")
        elif listing.rank == 2:
            score += 12.0
            reasons.append("RANK_2_STRONG_VISIBILITY")
        elif listing.rank == 3:
            score += 6.0
            reasons.append("RANK_3_VISIBLE_COMPETITOR")

        if listing.fast_shipping:
            score += 8
            reasons.append("BUYBOX_FAST_SHIPPING_ADVANTAGE")
        if listing.free_shipping:
            score += 5
            reasons.append("BUYBOX_FREE_SHIPPING_ADVANTAGE")

        # "Threat To Us" Filtresi
        if our_price and our_price > 0 and competitor_price > 0:
            our_price_gap = (competitor_price - our_price) / our_price
            
            if our_price_gap >= 0.03:
                score *= 0.30
                reasons.append("COMPETITOR_PRICE_SIGNIFICANTLY_HIGHER_THAN_US_LOW_DIRECT_THREAT")
            elif our_price_gap > 0:
                score *= 0.70
                reasons.append("COMPETITOR_PRICE_SLIGHTLY_HIGHER")
            elif our_price_gap < -0.05:
                score += 15.0
                reasons.append("COMPETITOR_UNDER_CUTTING_US_HIGH_THREAT")

        return max(0.0, min(score, 100.0)), reasons

    # 🔥 SİSTEMİ BİRBİRİNE BAĞLAYAN ANA METOT
    def process_listing_scoring(
        self,
        listing: CompetitorListing,
        min_price: float,
        avg_price: float,
        price_history_summary: dict[str, Any],
        our_price: float | None = None,  # <- Üst katmandan buraya akmalı
    ) -> dict[str, Any]:
        """
        Repository veya Service katmanından çağrılacak ana giriş noktası.
        Tüm alt puanları hesaplar ve nihai TIER atamasını yapar.
        """
        strength_score, strength_reasons = self.calculate_competitor_strength_score(
            listing, min_price, avg_price
        )
        
        price_aggression_score, aggression_reasons = self.calculate_price_aggression_score(
            listing, min_price, avg_price, price_history_summary
        )
        
        # our_price buraya bağlanarak threat skorunu doğrudan etkiler
        buybox_threat_score, threat_reasons = self.calculate_buybox_threat_score(
            listing, strength_score, our_price=our_price, price_aggression_score=price_aggression_score
        )
        
        tier, tier_reasons = self.assign_tier(
            listing, strength_score, buybox_threat_score, price_aggression_score
        )
        
        return {
            "tier": tier,
            "final_score": max(0.0, min((strength_score * 0.40 + buybox_threat_score * 0.40 + price_aggression_score * 0.20), 100.0)),
            "all_reasons": strength_reasons + aggression_reasons + threat_reasons + tier_reasons
        }

    def assign_tier(
        self,
        listing: CompetitorListing,
        strength_score: float,
        buybox_threat_score: float,
        price_aggression_score: float,
    ) -> tuple[str, list[str]]:
        if listing.is_in_stock is False:
            return "NOISE", ["OUT_OF_STOCK_SELLER"]

        seller_score = self.safe_float(listing.seller_score)
        review_count = listing.seller_review_count

        if 0 < seller_score < 6 and review_count is not None and review_count < 50:
            return "NOISE", ["LOW_TRUST_SELLER"]

        # 🔥 DÜZELTME 1: İlettiğin buybox_threat_score >= 60 filtresi eklendi.
        # Böylece fiyatta bizden çok pahalı olan rakipler Rank 1 olsa bile bypass ile TIER_1 olamazlar.
        if (
            listing.rank == 1 
            and price_aggression_score >= 80 
            and strength_score >= 50
            and buybox_threat_score >= 60.0
        ):
            return "TIER_1", ["RANK_1_PRICE_LEADER"]

        if price_aggression_score >= 90 and listing.stock and listing.stock > 10:
            return "TIER_1", ["CRITICAL_PRICE_DUMPING_BYPASS"]

        # Standart Ağırlıklı Hesaplama
        final_score = (
            strength_score * 0.40
            + buybox_threat_score * 0.40
            + price_aggression_score * 0.20
        )
        final_score = max(0.0, min(final_score, 100.0))

        if final_score >= 65:
            return "TIER_1", ["HIGH_IMPACT_COMPETITOR"]

        if final_score >= 40:
            return "TIER_2", ["MEDIUM_IMPACT_COMPETITOR"]

        # Fallback Kuralı
        if listing.rank == 1 and strength_score >= 40:
            return "TIER_2", ["RANK_1_COMPETITOR_SOFT_BYPASS"]

        return "NOISE", ["LOW_IMPACT_COMPETITOR"]