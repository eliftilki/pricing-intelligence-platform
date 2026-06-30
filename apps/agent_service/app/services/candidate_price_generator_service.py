from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
)
from app.services.candidate_strategies.dynamic_step_policy import (
    choose_step,
    generate_extended_market_range,
)


class CandidatePriceGeneratorService:
    def generate(
        self,
        context: CandidatePriceContext,
    ) -> CandidatePriceGenerateResponse:
        relevant_competitors = [
            competitor
            for competitor in context.competitors
            if competitor.tier.upper() in {"TIER_1", "TIER_2"}
        ]
        if not relevant_competitors:
            raise ValueError(
                "No TIER_1 or TIER_2 competitors are available for candidate pricing."
            )

        competitor_prices = [competitor.price for competitor in relevant_competitors]
        min_price = min(competitor_prices)
        avg_price = sum(competitor_prices) / len(competitor_prices)
        max_price = max(competitor_prices)
        dynamic_step = choose_step(min_price, max_price)
        candidate_prices = generate_extended_market_range(
            min_price=min_price,
            max_price=max_price,
            step=dynamic_step,
            padding_steps=5,
        )
        marketplaces = sorted(
            {competitor.marketplace.upper() for competitor in relevant_competitors}
        )

        return CandidatePriceGenerateResponse(
            product_id=context.product_id,
            seller_product_id=context.seller_product_id,
            selected_strategy=CandidateStrategy.ALL_MARKETPLACE_RANGE,
            candidate_prices=candidate_prices,
            min_competitor_price=min_price,
            avg_competitor_price=avg_price,
            max_competitor_price=max_price,
            dynamic_step=dynamic_step,
            marketplaces_included=marketplaces,
            reason=(
                "TIER_1 and TIER_2 competitor prices from all marketplaces were combined "
                "into one dynamically stepped min/max range with five extra steps on "
                "each side."
            ),
            constraints_applied=[
                "ALL_MARKETPLACES_COMBINED",
                "TIER_1_AND_TIER_2_COMPETITORS_INCLUDED",
                "NOISE_COMPETITORS_EXCLUDED",
                f"DYNAMIC_STEP_{dynamic_step}",
                "RANGE_EXTENDED_5_STEPS_EACH_SIDE",
            ],
        )
