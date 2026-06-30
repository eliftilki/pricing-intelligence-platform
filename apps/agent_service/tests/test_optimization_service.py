import unittest
from decimal import Decimal
from uuid import uuid4

from app.schemas.optimization_schema import (
    DemandPredictionItem,
    Marketplace,
    MarketplaceOptimizationInput,
    OptimizationRequest,
    OptimizationConstraintCode,
    RejectionReason,
)
from app.services.optimization_service import OptimizationService


def build_request(
    demand_predictions: list[DemandPredictionItem],
    marketplace_context: MarketplaceOptimizationInput | None = None,
) -> OptimizationRequest:
    return OptimizationRequest(
        seller_product_id=uuid4(),
        product_id=uuid4(),
        cost_price=Decimal("60"),
        demand_predictions=demand_predictions,
        marketplaces=[
            marketplace_context
            or MarketplaceOptimizationInput(
                marketplace=Marketplace.TRENDYOL,
                current_price=Decimal("100"),
                commission_rate=Decimal("0.10"),
                shipping_cost=Decimal("5"),
                packaging_cost=Decimal("2"),
                min_margin_rate=Decimal("0.20"),
            )
        ],
        persist=False,
    )


class OptimizationServiceTests(unittest.TestCase):
    def test_optimizes_each_marketplace_with_shared_demand_predictions(self):
        trendyol_id = uuid4()
        amazon_id = uuid4()
        request = OptimizationRequest(
            seller_product_id=trendyol_id,
            product_id=uuid4(),
            cost_price=Decimal("60"),
            demand_predictions=[
                DemandPredictionItem(price=Decimal("100"), expected_sales=Decimal("10")),
                DemandPredictionItem(price=Decimal("110"), expected_sales=Decimal("9")),
            ],
            marketplaces=[
                MarketplaceOptimizationInput(
                    marketplace=Marketplace.TRENDYOL,
                    seller_product_id=trendyol_id,
                    cost_price=Decimal("60"),
                    current_price=Decimal("100"),
                    commission_rate=Decimal("0.10"),
                    min_margin_rate=Decimal("0.10"),
                ),
                MarketplaceOptimizationInput(
                    marketplace=Marketplace.AMAZON,
                    seller_product_id=amazon_id,
                    cost_price=Decimal("75"),
                    current_price=Decimal("100"),
                    commission_rate=Decimal("0.20"),
                    min_margin_rate=Decimal("0.10"),
                ),
            ],
            persist=False,
        )

        response = OptimizationService().optimize(request)

        self.assertEqual(len(response.marketplace_results), 2)
        self.assertEqual(response.marketplace_results[0].seller_product_id, trendyol_id)
        self.assertEqual(response.marketplace_results[1].seller_product_id, amazon_id)
        self.assertEqual(response.marketplace_results[0].cost_price, Decimal("60"))
        self.assertEqual(response.marketplace_results[1].cost_price, Decimal("75"))
        self.assertNotEqual(
            response.marketplace_results[0].expected_profit,
            response.marketplace_results[1].expected_profit,
        )

    def test_selects_highest_expected_profit_candidate(self):
        request = build_request(
            [
                DemandPredictionItem(price=Decimal("100"), expected_sales=Decimal("10")),
                DemandPredictionItem(price=Decimal("110"), expected_sales=Decimal("9")),
                DemandPredictionItem(price=Decimal("120"), expected_sales=Decimal("7")),
            ]
        )

        response = OptimizationService().optimize(request)
        result = response.marketplace_results[0]

        self.assertEqual(response.summary["status"], "OK")
        self.assertEqual(result.recommended_price, Decimal("110.00"))
        self.assertEqual(result.expected_profit, Decimal("288.00"))
        self.assertEqual(result.profit_uplift_vs_current, Decimal("0.252174"))

    def test_missing_commission_rule_produces_no_recommendation(self):
        request = build_request(
            [DemandPredictionItem(price=Decimal("100"), expected_sales=Decimal("10"))],
            MarketplaceOptimizationInput(
                marketplace=Marketplace.TRENDYOL,
                current_price=Decimal("100"),
                commission_rate=None,
                min_margin_rate=Decimal("0.10"),
            ),
        )

        response = OptimizationService().optimize(request)
        result = response.marketplace_results[0]

        self.assertEqual(response.summary["status"], "NO_VALID_RECOMMENDATION")
        self.assertIsNone(result.recommended_price)
        self.assertIn(
            RejectionReason.MISSING_COMMISSION_RULE,
            result.rejected_candidates[0].rejection_reasons,
        )

    def test_rejects_candidates_above_max_price_increase(self):
        request = build_request(
            [
                DemandPredictionItem(price=Decimal("100"), expected_sales=Decimal("5")),
                DemandPredictionItem(price=Decimal("140"), expected_sales=Decimal("10")),
            ]
        )

        response = OptimizationService().optimize(request)
        result = response.marketplace_results[0]

        self.assertEqual(result.recommended_price, Decimal("100.00"))
        self.assertEqual(result.rejected_candidates[0].price, Decimal("140.00"))
        self.assertIn(
            RejectionReason.PRICE_INCREASE_TOO_HIGH,
            result.rejected_candidates[0].rejection_reasons,
        )

    def test_marketplace_input_accepts_lowercase_values(self):
        marketplace_context = MarketplaceOptimizationInput(
            marketplace="trendyol",
            current_price=Decimal("100"),
            commission_rate=Decimal("0.10"),
        )

        self.assertEqual(marketplace_context.marketplace, Marketplace.TRENDYOL)

    def test_selects_market_aligned_candidate_within_three_percent_profit_region(self):
        request = OptimizationRequest(
            seller_product_id=uuid4(),
            product_id=uuid4(),
            cost_price=Decimal("4400"),
            demand_predictions=[
                DemandPredictionItem(price=Decimal("5500"), expected_sales=Decimal("6.667991486")),
                DemandPredictionItem(price=Decimal("5650"), expected_sales=Decimal("6.333369277")),
                DemandPredictionItem(price=Decimal("6050"), expected_sales=Decimal("4.592737385")),
                DemandPredictionItem(price=Decimal("6100"), expected_sales=Decimal("4.501357852")),
            ],
            marketplaces=[
                MarketplaceOptimizationInput(
                    marketplace=Marketplace.TRENDYOL,
                    current_price=Decimal("5500"),
                    commission_rate=Decimal("0.045"),
                    min_margin_rate=Decimal("0.15"),
                    market_average_price=Decimal("5707.67"),
                )
            ],
            persist=False,
        )

        result = OptimizationService().optimize(request).marketplace_results[0]

        self.assertEqual(result.recommended_price, Decimal("5650.00"))
        self.assertEqual(result.metadata["near_optimal_candidate_count"], 3)
        self.assertIn(
            OptimizationConstraintCode.MARKET_AVERAGE_PROXIMITY_APPLIED,
            result.constraints_applied,
        )
        self.assertNotIn(
            OptimizationConstraintCode.BOUNDARY_OPTIMUM,
            result.constraints_applied,
        )

    def test_warns_when_selected_candidate_is_at_price_range_boundary(self):
        request = build_request(
            [
                DemandPredictionItem(price=Decimal("100"), expected_sales=Decimal("10")),
                DemandPredictionItem(price=Decimal("110"), expected_sales=Decimal("12")),
            ]
        )

        result = OptimizationService().optimize(request).marketplace_results[0]

        self.assertEqual(result.recommended_price, Decimal("110.00"))
        self.assertIn(
            OptimizationConstraintCode.BOUNDARY_OPTIMUM,
            result.constraints_applied,
        )
        self.assertIn("BOUNDARY_OPTIMUM", result.metadata["warnings"])


if __name__ == "__main__":
    unittest.main()
