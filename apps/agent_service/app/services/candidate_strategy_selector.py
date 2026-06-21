from app.schemas.candidate_price_schema import CandidatePriceContext, CandidateStrategy


class CandidateStrategySelector:
    CLUSTER_WINDOW = 250
    MIN_CLUSTER_SIZE = 3

    def select(self, context: CandidatePriceContext) -> CandidateStrategy:
        if not context.competitors:
            return CandidateStrategy.BASIC_COMPETITOR_RANGE

        relevant_competitors = [
            c for c in context.competitors
            if c.tier in {"TIER_1", "TIER_2"} and c.price > 0
        ]

        if not relevant_competitors:
            return CandidateStrategy.BASIC_COMPETITOR_RANGE

        prices = [c.price for c in relevant_competitors]

        if self._has_dense_cluster(prices):
            return CandidateStrategy.ADAPTIVE_DENSE_MARKET_WINDOW

        return CandidateStrategy.TIER_BASED_COMPETITOR_WINDOW

    def _has_dense_cluster(self, prices: list[float]) -> bool:
        if len(prices) < self.MIN_CLUSTER_SIZE:
            return False

        sorted_prices = sorted(prices)

        for i, start_price in enumerate(sorted_prices):
            cluster_size = sum(
                1
                for price in sorted_prices[i:]
                if price - start_price <= self.CLUSTER_WINDOW
            )

            if cluster_size >= self.MIN_CLUSTER_SIZE:
                return True

        return False