from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
    IgnoredCompetitor,
)


class TierBasedStrategy:
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

        if not relevant_competitors:
            prices = [context.current_price]
        else:
            tier1_competitors = [
                c for c in relevant_competitors
                if c.tier == "TIER_1"
            ]

            base_competitors = tier1_competitors or relevant_competitors

            competitor_prices = [c.price for c in base_competitors]
            min_price = min(competitor_prices)
            avg_price = sum(competitor_prices) / len(competitor_prices)

            prices = [
                min_price - 500,
                min_price - 250,
                min_price,
                min_price + 250,
                avg_price,
                context.current_price,
                context.current_price + 500,
            ]

        prices = self._normalize_prices(prices, context.price_step)

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.TIER_BASED_COMPETITOR_WINDOW,
            candidate_prices=prices,
            reason="Tier-based competitor window was selected because meaningful TIER_1/TIER_2 competitors exist.",
            constraints_applied=[
                "NOISE_COMPETITOR_EXCLUDED",
                "TIER_BASED_WINDOW",
                "PRICE_STEP_NORMALIZATION",
            ],
            ignored_competitors=ignored_competitors,
        )

    def _normalize_prices(
        self,
        prices: list[float],
        step: int,
    ) -> list[float]:
        normalized = []

        for price in prices:
            rounded_price = round(price / step) * step
            if rounded_price > 0:
                normalized.append(float(rounded_price))

        return sorted(set(normalized))