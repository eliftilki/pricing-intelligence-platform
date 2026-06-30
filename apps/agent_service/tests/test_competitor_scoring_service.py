import unittest

from app.models.competitor import CompetitorListing
from app.services.competitor_scoring_service import CompetitorScoringService


def listing(price: float, **overrides) -> CompetitorListing:
    values = {
        "price": price,
        "seller_name": "seller",
        "is_in_stock": True,
        "rank": 1,
    }
    values.update(overrides)
    return CompetitorListing(**values)


class CompetitorScoringServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = CompetitorScoringService()

    def test_market_statistics_exclude_extreme_price_outlier(self):
        listings = [
            listing(219.31, seller_name="Amazon"),
            listing(4479.0),
            listing(5269.0),
            listing(5574.0),
            listing(5699.0),
        ]

        result = self.service.calculate_market_prices(listings)

        self.assertEqual(result["median_price"], 5269.0)
        self.assertEqual(result["min_price"], 4479.0)
        self.assertNotEqual(result["min_price"], 219.31)

    def test_extreme_price_outlier_is_assigned_to_noise(self):
        tier, reasons = self.service.assign_tier(
            listing=listing(219.31, seller_name="Amazon"),
            strength_score=53.0,
            buybox_threat_score=56.2,
            price_aggression_score=100.0,
            price_is_outlier=True,
        )

        self.assertEqual(tier, "NOISE")
        self.assertEqual(reasons, ["PRICE_OUTLIER_MEDIAN_MAD"])

    def test_small_samples_do_not_trigger_outlier_filter(self):
        self.assertFalse(
            self.service.is_price_outlier(
                price=219.31,
                median_price=5269.0,
                mad_price=430.0,
                price_count=3,
            )
        )


if __name__ == "__main__":
    unittest.main()
