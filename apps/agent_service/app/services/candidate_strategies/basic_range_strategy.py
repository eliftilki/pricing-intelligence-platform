import math

from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
)
from app.services.candidate_strategies.current_price_policy import (
    current_price_candidates,
    current_price_constraint,
    normalize_prices_to_step,
)
from app.services.candidate_strategies.dynamic_step_policy import choose_step


class BasicRangeStrategy:
    def generate(
        self,
        context: CandidatePriceContext,
    ) -> CandidatePriceGenerateResponse:
        has_market_range = (
            context.min_competitor_price is not None
            and context.max_competitor_price is not None
            and context.min_competitor_price > 0
            and context.max_competitor_price > 0
        )
        constraints_applied = [
            "BASIC_COMPETITOR_RANGE",
            "PRICE_STEP_NORMALIZATION",
        ]

        if has_market_range:
            min_competitor = context.min_competitor_price
            max_competitor = context.max_competitor_price
            market_center = (min_competitor + max_competitor) / 2
            dynamic_step = choose_step(min_competitor, max_competitor)

            prices = self._generate_range(
                lower_bound=min_competitor * 0.98,
                upper_bound=max_competitor * 1.02,
                step=dynamic_step,
            )
            prices.extend(
                current_price_candidates(
                    current_price=context.current_price,
                    market_reference_price=market_center,
                    step=dynamic_step,
                )
            )
            constraints_applied.append(
                f"DYNAMIC_GENERAL_STEP_{dynamic_step}"
            )
            constraints_applied.append(
                current_price_constraint(
                    current_price=context.current_price,
                    market_reference_price=market_center,
                )
            )
        else:
            prices = [context.current_price]
            dynamic_step = context.price_step
            constraints_applied.append("CURRENT_PRICE_USED_AS_FALLBACK")

        prices = normalize_prices_to_step(prices, dynamic_step)

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.BASIC_COMPETITOR_RANGE,
            candidate_prices=prices,
            reason="Basic competitor range was selected because tier-based or dense-market signals were not available.",
            constraints_applied=constraints_applied,
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

