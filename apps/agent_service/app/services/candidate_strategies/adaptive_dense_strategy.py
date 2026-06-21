from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
    DenseRegion,
    IgnoredCompetitor,
)
from app.services.candidate_strategies.current_price_policy import (
    current_price_candidates,
    current_price_constraint,
    normalize_prices_to_step,
)
from app.services.candidate_strategies.dynamic_step_policy import (
    choose_dense_step,
    choose_step,
    generate_aligned_range,
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
        constraints_applied = [
            "NOISE_COMPETITOR_EXCLUDED",
            "PRICE_STEP_NORMALIZATION",
        ]

        if cluster:
            constraints_applied.append("DENSE_MARKET_CLUSTER_DETECTED")
            start_price, end_price = cluster
            cluster_center = (start_price + end_price) / 2
            relevant_competitor_prices = [
                competitor.price
                for competitor in relevant_competitors
                if competitor.price > 0
            ]
            general_min_price = (
                min(relevant_competitor_prices)
                if relevant_competitor_prices
                else start_price
            )
            general_max_price = (
                max(relevant_competitor_prices)
                if relevant_competitor_prices
                else end_price
            )
            general_step = choose_step(
                general_min_price,
                general_max_price,
            )
            dense_step = choose_dense_step(start_price, end_price)

            dense_regions.append(
                DenseRegion(
                    start_price=start_price,
                    end_price=end_price,
                    reason="COMPETITOR_PRICE_CLUSTER",
                )
            )

            prices.extend(
                generate_aligned_range(
                    general_min_price,
                    general_max_price,
                    general_step,
                )
            )
            prices.extend(
                generate_aligned_range(
                    start_price,
                    end_price,
                    dense_step,
                    include_ceiling=True,
                )
            )
            prices.extend(
                current_price_candidates(
                    current_price=context.current_price,
                    market_reference_price=cluster_center,
                    step=general_step,
                )
            )
            constraints_applied.extend(
                [
                    f"DYNAMIC_GENERAL_STEP_{general_step}",
                    f"DYNAMIC_DENSE_STEP_{dense_step}",
                ]
            )
            constraints_applied.append(
                current_price_constraint(
                    current_price=context.current_price,
                    market_reference_price=cluster_center,
                )
            )
        else:
            prices = [context.current_price]
            constraints_applied.append("CURRENT_PRICE_USED_AS_FALLBACK")

        normalization_step = (
            dense_step
            if cluster
            else context.dense_price_step
        )
        prices = normalize_prices_to_step(prices, normalization_step)

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.ADAPTIVE_DENSE_MARKET_WINDOW,
            candidate_prices=prices,
            reason="Adaptive dense market window was selected because competitor prices are clustered.",
            constraints_applied=constraints_applied,
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

