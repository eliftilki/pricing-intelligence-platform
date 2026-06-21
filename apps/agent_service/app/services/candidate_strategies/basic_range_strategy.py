import math

from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
)


class BasicRangeStrategy:
    def generate(
        self,
        context: CandidatePriceContext,
    ) -> CandidatePriceGenerateResponse:
        min_competitor = context.min_competitor_price or context.current_price
        max_competitor = context.max_competitor_price or context.current_price

        lower_bound = min(min_competitor * 0.98, context.current_price)
        upper_bound = max(max_competitor * 1.02, context.current_price)

        prices = self._generate_range(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            step=context.price_step,
        )

        prices.append(context.current_price)
        prices = self._normalize_prices(prices)

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.BASIC_COMPETITOR_RANGE,
            candidate_prices=prices,
            reason="Basic competitor range was selected because tier-based or dense-market signals were not available.",
            constraints_applied=[
                "BASIC_COMPETITOR_RANGE",
                "PRICE_STEP_NORMALIZATION",
            ],
        )

    def _generate_range(
        self,
        lower_bound: float,
        upper_bound: float,
        step: int,
    ) -> list[float]:
        start = math.floor(lower_bound / step) * step
        end = math.ceil(upper_bound / step) * step

        prices = []
        current = start

        while current <= end:
            prices.append(float(current))
            current += step

        return prices

    def _normalize_prices(self, prices: list[float]) -> list[float]:
        return sorted(set(round(price, 2) for price in prices if price > 0))