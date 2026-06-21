import unittest
from uuid import uuid4

from app.schemas.candidate_price_schema import (
    CandidateCompetitor,
    CandidatePriceContext,
)
from app.services.candidate_strategies.adaptive_dense_strategy import (
    AdaptiveDenseStrategy,
)
from app.services.candidate_strategies.basic_range_strategy import (
    BasicRangeStrategy,
)
from app.services.candidate_strategies.tier_based_strategy import (
    TierBasedStrategy,
)
from app.services.candidate_strategies.current_price_policy import (
    normalize_prices_to_step,
)
from app.services.candidate_strategies.dynamic_step_policy import (
    choose_dense_step,
    choose_step,
)


def build_context(current_price: float) -> CandidatePriceContext:
    competitor_prices = [1490.0, 1520.0, 1560.0, 1590.0]
    return CandidatePriceContext(
        product_id=uuid4(),
        seller_product_id=uuid4(),
        current_price=current_price,
        min_competitor_price=min(competitor_prices),
        avg_competitor_price=sum(competitor_prices) / len(competitor_prices),
        max_competitor_price=max(competitor_prices),
        competitors=[
            CandidateCompetitor(
                seller_name=f"seller-{index}",
                price=price,
                tier="TIER_1" if index < 2 else "TIER_2",
            )
            for index, price in enumerate(competitor_prices)
        ],
        price_step=250,
        base_price_step=250,
        dense_price_step=50,
    )


class CandidateCurrentPricePolicyTests(unittest.TestCase):
    def test_general_step_is_selected_from_market_width(self):
        self.assertEqual(choose_step(1000, 1500), 50)
        self.assertEqual(choose_step(1490, 2947), 100)
        self.assertEqual(choose_step(1000, 3500), 250)
        self.assertEqual(choose_step(1000, 5001), 500)

    def test_dense_step_is_selected_from_cluster_width(self):
        self.assertEqual(choose_dense_step(1490, 1657), 50)
        self.assertEqual(choose_dense_step(1000, 1600), 100)
        self.assertEqual(choose_dense_step(1000, 2000), 250)

    def test_candidate_prices_are_normalized_to_strategy_step(self):
        self.assertEqual(
            normalize_prices_to_step(
                [1490.55, 1540.55, 1590.55, 1907.96],
                50,
            ),
            [1500.0, 1550.0, 1600.0, 1900.0],
        )

    def test_adaptive_excludes_current_price_far_from_cluster(self):
        result = AdaptiveDenseStrategy().generate(build_context(3499.0))

        self.assertNotIn(3499.0, result.candidate_prices)
        self.assertIn("CURRENT_PRICE_OUTLIER_EXCLUDED", result.constraints_applied)

    def test_adaptive_noise_prices_do_not_expand_general_range(self):
        context = build_context(1550.0)
        context.competitors.append(
            CandidateCompetitor(
                seller_name="noise-seller",
                price=9999.0,
                tier="NOISE",
            )
        )

        result = AdaptiveDenseStrategy().generate(context)

        self.assertLess(max(result.candidate_prices), 9999.0)
        self.assertIn("NOISE_COMPETITOR_EXCLUDED", result.constraints_applied)

    def test_adaptive_does_not_report_cluster_when_none_exists(self):
        context = build_context(1550.0)
        context.competitors = context.competitors[:2]

        result = AdaptiveDenseStrategy().generate(context)

        self.assertNotIn(
            "DENSE_MARKET_CLUSTER_DETECTED",
            result.constraints_applied,
        )
        self.assertIn("CURRENT_PRICE_USED_AS_FALLBACK", result.constraints_applied)

    def test_tier_based_excludes_current_price_far_from_tier_market(self):
        result = TierBasedStrategy().generate(build_context(3499.0))

        self.assertNotIn(3500.0, result.candidate_prices)
        self.assertIn("CURRENT_PRICE_OUTLIER_EXCLUDED", result.constraints_applied)

    def test_basic_range_is_not_expanded_by_far_current_price(self):
        result = BasicRangeStrategy().generate(build_context(3499.0))

        self.assertLess(max(result.candidate_prices), 3499.0)
        self.assertIn("CURRENT_PRICE_OUTLIER_EXCLUDED", result.constraints_applied)

    def test_all_strategies_include_near_current_price_context(self):
        context = build_context(1550.0)

        for strategy in (
            AdaptiveDenseStrategy(),
            TierBasedStrategy(),
            BasicRangeStrategy(),
        ):
            with self.subTest(strategy=type(strategy).__name__):
                result = strategy.generate(context)
                self.assertIn(
                    "CURRENT_PRICE_NEAR_MARKET_INCLUDED",
                    result.constraints_applied,
                )

    def test_basic_uses_current_price_when_market_data_is_unavailable(self):
        context = build_context(3499.0)
        context.min_competitor_price = None
        context.max_competitor_price = None

        result = BasicRangeStrategy().generate(context)

        self.assertEqual(result.candidate_prices, [3500.0])
        self.assertIn("CURRENT_PRICE_USED_AS_FALLBACK", result.constraints_applied)


if __name__ == "__main__":
    unittest.main()
