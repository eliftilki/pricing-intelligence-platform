import unittest
from decimal import Decimal
from uuid import uuid4

from app.schemas.risk_control_schema import (
    MarketplaceRiskInput,
    RiskContextInput,
    RiskControlRequest,
    RiskLevel,
    RiskReasonCode,
)
from app.services.risk_control_service import RiskControlService


def build_risk_request(
    *,
    recommended_price: Decimal | None = Decimal("110"),
    current_price: Decimal | None = Decimal("100"),
    unit_profit: Decimal | None = Decimal("20"),
    unit_margin_rate: Decimal | None = Decimal("0.20"),
    cost_price: Decimal = Decimal("60"),
    min_margin_rate: Decimal = Decimal("0.15"),
    stock_quantity: int | None = 100,
    min_competitor_price: Decimal | None = Decimal("95"),
    optimization_summary_status: str | None = "OK",
    n_fold_models: int = 5,
) -> RiskControlRequest:
    return RiskControlRequest(
        context=RiskContextInput(
            seller_product_id=uuid4(),
            product_id=uuid4(),
            cost_price=cost_price,
            min_margin_rate=min_margin_rate,
            stock_quantity=stock_quantity,
            min_competitor_price=min_competitor_price,
            avg_competitor_price=Decimal("105"),
            market_pressure_score=40.0,
            demand_prediction_meta={"n_fold_models": n_fold_models, "model_name": "test-model"},
        ),
        marketplaces=[
            MarketplaceRiskInput(
                marketplace="TRENDYOL",
                recommended_price=recommended_price,
                current_price=current_price,
                unit_profit=unit_profit,
                unit_margin_rate=unit_margin_rate,
                expected_sales=Decimal("10"),
                commission_rate=Decimal("0.10"),
                selected_reason="BEST_EXPECTED_PROFIT",
            )
        ],
        optimization_summary_status=optimization_summary_status,
    )


class RiskControlServiceTests(unittest.TestCase):
    def test_all_checks_pass_returns_low_risk(self):
        response = RiskControlService().assess(build_risk_request())

        assessment = response.assessments[0]
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertTrue(assessment.allowed)
        self.assertEqual(assessment.reason_codes, [])
        self.assertTrue(response.overall_allowed)

    def test_no_valid_optimization_result_blocks_recommendation(self):
        response = RiskControlService().assess(
            build_risk_request(
                recommended_price=None,
                optimization_summary_status="NO_VALID_RECOMMENDATION",
            )
        )

        assessment = response.assessments[0]
        self.assertEqual(assessment.risk_level, RiskLevel.HIGH)
        self.assertFalse(assessment.allowed)
        self.assertIn(RiskReasonCode.NO_VALID_OPTIMIZATION_RESULT, assessment.blocking_reasons)

    def test_selling_below_cost_blocks_recommendation(self):
        response = RiskControlService().assess(
            build_risk_request(
                recommended_price=Decimal("50"),
                unit_profit=Decimal("-5"),
            )
        )

        assessment = response.assessments[0]
        self.assertFalse(assessment.allowed)
        self.assertIn(RiskReasonCode.SELLING_BELOW_COST, assessment.blocking_reasons)

    def test_min_margin_breach_blocks_recommendation(self):
        response = RiskControlService().assess(
            build_risk_request(
                unit_margin_rate=Decimal("0.10"),
                min_margin_rate=Decimal("0.15"),
            )
        )

        assessment = response.assessments[0]
        self.assertFalse(assessment.allowed)
        self.assertIn(RiskReasonCode.MIN_MARGIN_BREACHED, assessment.blocking_reasons)

    def test_aggressive_price_change_can_block(self):
        response = RiskControlService().assess(
            build_risk_request(
                current_price=Decimal("100"),
                recommended_price=Decimal("130"),
            )
        )

        assessment = response.assessments[0]
        self.assertFalse(assessment.allowed)
        self.assertIn(RiskReasonCode.PRICE_CHANGE_TOO_AGGRESSIVE, assessment.reason_codes)

    def test_low_stock_price_decrease_warns(self):
        response = RiskControlService().assess(
            build_risk_request(
                stock_quantity=10,
                current_price=Decimal("100"),
                recommended_price=Decimal("95"),
            )
        )

        assessment = response.assessments[0]
        self.assertEqual(assessment.risk_level, RiskLevel.MEDIUM)
        self.assertTrue(assessment.allowed)
        self.assertIn(RiskReasonCode.LOW_STOCK_PRICE_DECREASE, assessment.reason_codes)

    def test_undercut_below_competitor_min_warns(self):
        response = RiskControlService().assess(
            build_risk_request(
                recommended_price=Decimal("90"),
                min_competitor_price=Decimal("95"),
            )
        )

        assessment = response.assessments[0]
        self.assertIn(RiskReasonCode.NOISE_DRIVEN_UNDERCUT, assessment.reason_codes)

    def test_low_model_confidence_warns(self):
        response = RiskControlService().assess(
            build_risk_request(n_fold_models=1)
        )

        assessment = response.assessments[0]
        self.assertEqual(assessment.risk_level, RiskLevel.MEDIUM)
        self.assertIn(RiskReasonCode.LOW_MODEL_CONFIDENCE, assessment.reason_codes)


if __name__ == "__main__":
    unittest.main()