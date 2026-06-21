from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
    DenseRegion,
    IgnoredCompetitor,
)


class AdaptiveDenseStrategy:
    CLUSTER_WINDOW = 250
    MIN_CLUSTER_SIZE = 3

    def generate(
        self,
        context: CandidatePriceContext,
    ) -> CandidatePriceGenerateResponse:
        relevant_competitors = [
            c for c in context.competitors
            if c.tier in {"TIER_1", "TIER_2"} and c.price > 0
        ]

        ignored_competitors = [
            IgnoredCompetitor(
                seller_name=c.seller_name,
                price=c.price,
                reason="NOISE_COMPETITOR",
            )
            for c in context.competitors
            if c.tier == "NOISE"
        ]

        cluster = self._find_dense_cluster(
            [c.price for c in relevant_competitors]
        )

        prices: list[float] = []
        dense_regions: list[DenseRegion] = []

        if cluster:
            start_price, end_price = cluster

            dense_regions.append(
                DenseRegion(
                    start_price=start_price,
                    end_price=end_price,
                    reason="COMPETITOR_PRICE_CLUSTER",
                )
            )

            current = start_price
            while current <= end_price:
                prices.append(current)
                current += context.dense_price_step

            prices.extend(
                [
                    end_price + context.base_price_step,
                    end_price + context.base_price_step * 2,
                    context.current_price,
                ]
            )
        else:
            prices = [context.current_price]

        prices = self._normalize_prices(prices)

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.ADAPTIVE_DENSE_MARKET_WINDOW,
            candidate_prices=prices,
            reason="Adaptive dense market window was selected because competitor prices are clustered.",
            constraints_applied=[
                "NOISE_COMPETITOR_EXCLUDED",
                "DENSE_MARKET_CLUSTER_DETECTED",
                "PRICE_STEP_NORMALIZATION",
            ],
            ignored_competitors=ignored_competitors,
            dense_regions=dense_regions,
        )

    def _find_dense_cluster(
        self,
        prices: list[float],
    ) -> tuple[float, float] | None:
        if len(prices) < self.MIN_CLUSTER_SIZE:
            return None

        sorted_prices = sorted(prices)
        best_cluster: list[float] = []

        for i, start_price in enumerate(sorted_prices):
            cluster = [
                price
                for price in sorted_prices[i:]
                if price - start_price <= self.CLUSTER_WINDOW
            ]

            if len(cluster) > len(best_cluster):
                best_cluster = cluster

        if len(best_cluster) < self.MIN_CLUSTER_SIZE:
            return None

        return min(best_cluster), max(best_cluster)

    def _normalize_prices(self, prices: list[float]) -> list[float]:
        return sorted(set(round(price, 2) for price in prices if price > 0))