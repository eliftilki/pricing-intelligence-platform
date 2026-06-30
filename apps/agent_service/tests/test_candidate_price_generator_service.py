import unittest
from uuid import uuid4

from app.schemas.candidate_price_schema import (
    CandidateCompetitor,
    CandidatePriceContext,
    CandidateStrategy,
)
from app.services.candidate_price_generator_service import (
    CandidatePriceGeneratorService,
)
from app.services.candidate_strategies.dynamic_step_policy import (
    choose_step,
    generate_extended_market_range,
)


def build_context(
    competitors: list[tuple[str, float, str]],
) -> CandidatePriceContext:
    return CandidatePriceContext(
        product_id=uuid4(),
        seller_product_id=uuid4(),
        competitors=[
            CandidateCompetitor(
                marketplace=marketplace,
                seller_name=f"seller-{index}",
                price=price,
                tier=tier,
            )
            for index, (marketplace, price, tier) in enumerate(competitors)
        ],
    )


class CandidatePriceGeneratorServiceTests(unittest.TestCase):
    def test_dynamic_step_is_selected_from_full_market_width(self):
        self.assertEqual(choose_step(1000, 1500), 50)
        self.assertEqual(choose_step(1000, 2500), 100)
        self.assertEqual(choose_step(1000, 4000), 250)
        self.assertEqual(choose_step(1000, 7500), 500)
        self.assertEqual(choose_step(1000, 31000), 2500)

    def test_range_extends_five_steps_below_and_above_market(self):
        prices = generate_extended_market_range(4000, 6000, step=500)

        self.assertEqual(prices[0], 1500.0)
        self.assertEqual(prices[-1], 8500.0)
        self.assertTrue(all(right - left == 500 for left, right in zip(prices, prices[1:])))

    def test_range_never_contains_zero_or_negative_prices(self):
        prices = generate_extended_market_range(100, 300, step=50)

        self.assertEqual(prices[0], 50.0)
        self.assertTrue(all(price > 0 for price in prices))

    def test_all_marketplaces_share_one_tier_1_and_tier_2_range(self):
        context = build_context(
            [
                ("AMAZON", 4000.0, "TIER_1"),
                ("HEPSIBURADA", 5500.0, "TIER_2"),
                ("TRENDYOL", 6000.0, "TIER_2"),
            ]
        )

        result = CandidatePriceGeneratorService().generate(context)

        self.assertEqual(result.selected_strategy, CandidateStrategy.ALL_MARKETPLACE_RANGE)
        self.assertEqual(result.min_competitor_price, 4000.0)
        self.assertEqual(result.max_competitor_price, 6000.0)
        self.assertEqual(result.dynamic_step, 250)
        self.assertEqual(
            result.marketplaces_included,
            ["AMAZON", "HEPSIBURADA", "TRENDYOL"],
        )
        self.assertEqual(result.candidate_prices[0], 2750.0)
        self.assertEqual(result.candidate_prices[-1], 7250.0)
        self.assertIn(
            "TIER_1_AND_TIER_2_COMPETITORS_INCLUDED",
            result.constraints_applied,
        )

    def test_noise_competitor_is_excluded_from_min_max_range(self):
        context = build_context(
            [
                ("AMAZON", 219.31, "NOISE"),
                ("HEPSIBURADA", 5199.0, "TIER_1"),
                ("TRENDYOL", 6999.0, "TIER_2"),
            ]
        )

        result = CandidatePriceGeneratorService().generate(context)

        self.assertEqual(result.min_competitor_price, 5199.0)
        self.assertEqual(result.max_competitor_price, 6999.0)
        self.assertNotIn("AMAZON", result.marketplaces_included)
        self.assertIn("NOISE_COMPETITORS_EXCLUDED", result.constraints_applied)

    def test_tier_2_competitor_remains_in_range_even_when_price_is_low(self):
        context = build_context(
            [
                ("AMAZON", 219.31, "TIER_2"),
                ("HEPSIBURADA", 5199.0, "TIER_1"),
            ]
        )

        result = CandidatePriceGeneratorService().generate(context)

        self.assertEqual(result.min_competitor_price, 219.31)
        self.assertIn("AMAZON", result.marketplaces_included)


if __name__ == "__main__":
    unittest.main()
