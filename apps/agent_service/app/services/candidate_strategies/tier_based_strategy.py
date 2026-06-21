from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
    IgnoredCompetitor,
)
from app.services.candidate_strategies.current_price_policy import (
    current_price_candidates,
    current_price_constraint,
    normalize_prices_to_step,
)
from app.services.candidate_strategies.dynamic_step_policy import choose_step


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
        constraints_applied = [
            "NOISE_COMPETITOR_EXCLUDED",
            "TIER_BASED_WINDOW",
            "PRICE_STEP_NORMALIZATION",
        ]

        if not relevant_competitors:
            prices = [context.current_price]
            dynamic_step = context.price_step
            constraints_applied.append("CURRENT_PRICE_USED_AS_FALLBACK")
        else:
            tier1_competitors = [
                c for c in relevant_competitors
                if c.tier == "TIER_1"
            ]

            base_competitors = tier1_competitors or relevant_competitors

            competitor_prices = [c.price for c in base_competitors]
            min_price = min(competitor_prices)
            max_price = max(competitor_prices)
            avg_price = sum(competitor_prices) / len(competitor_prices)
            dynamic_step = choose_step(min_price, max_price)

            prices = [
                min_price - dynamic_step * 2,
                min_price - dynamic_step,
                min_price,
                min_price + dynamic_step,
                avg_price,
            ]
            prices.extend(
                current_price_candidates(
                    current_price=context.current_price,
                    market_reference_price=avg_price,
                    step=dynamic_step,
                )
            )
            constraints_applied.append(
                f"DYNAMIC_GENERAL_STEP_{dynamic_step}"
            )
            constraints_applied.append(
                current_price_constraint(
                    current_price=context.current_price,
                    market_reference_price=avg_price,
                )
            )

        prices = normalize_prices_to_step(prices, dynamic_step)

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.TIER_BASED_COMPETITOR_WINDOW,
            candidate_prices=prices,
            reason="Tier-based competitor window was selected because meaningful TIER_1/TIER_2 competitors exist.",
            constraints_applied=constraints_applied,
            ignored_competitors=ignored_competitors,
        )

