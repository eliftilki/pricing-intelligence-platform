from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.risk_control_schema import (
    MarketplaceRiskAssessment,
    MarketplaceRiskInput,
    RiskCheckResult,
    RiskCheckSeverity,
    RiskContextInput,
    RiskControlRequest,
    RiskControlResponse,
    RiskLevel,
    RiskReasonCode,
)

PRICE_CHANGE_WARNING_RATE = Decimal("0.15")
PRICE_CHANGE_BLOCKING_RATE = Decimal("0.25")
LOW_STOCK_THRESHOLD = 40
MIN_FOLD_MODELS_FOR_CONFIDENCE = 3

_RISK_LEVEL_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
}


class RiskControlService:
    def assess(self, request: RiskControlRequest) -> RiskControlResponse:
        assessments = [
            self._assess_marketplace(
                marketplace_input=marketplace_input,
                context=request.context,
                optimization_summary_status=request.optimization_summary_status,
            )
            for marketplace_input in request.marketplaces
        ]

        overall_risk_level = self._aggregate_risk_level(assessments)
        overall_allowed = all(assessment.allowed for assessment in assessments)
        best_marketplace = self._select_best_marketplace(assessments)

        return RiskControlResponse(
            seller_product_id=request.context.seller_product_id,
            product_id=request.context.product_id,
            evaluated_at=datetime.now(timezone.utc),
            assessments=assessments,
            overall_risk_level=overall_risk_level,
            overall_allowed=overall_allowed,
            best_marketplace=best_marketplace,
        )

    def _assess_marketplace(
        self,
        *,
        marketplace_input: MarketplaceRiskInput,
        context: RiskContextInput,
        optimization_summary_status: str | None,
    ) -> MarketplaceRiskAssessment:
        no_result_check = self._check_no_valid_optimization_result(
            marketplace_input=marketplace_input,
            optimization_summary_status=optimization_summary_status,
        )
        if not no_result_check.passed:
            return self._build_assessment(marketplace_input, [no_result_check])

        checks = [
            no_result_check,
            self._check_selling_below_cost(marketplace_input, context),
            self._check_min_margin(marketplace_input, context),
            self._check_price_change(marketplace_input),
            self._check_low_stock_price_decrease(marketplace_input, context),
            self._check_noise_driven_undercut(marketplace_input, context),
            self._check_model_confidence(context),
        ]
        return self._build_assessment(marketplace_input, checks)

    def _build_assessment(
        self,
        marketplace_input: MarketplaceRiskInput,
        checks: list[RiskCheckResult],
    ) -> MarketplaceRiskAssessment:
        failed_checks = [check for check in checks if not check.passed]
        reason_codes = list(dict.fromkeys(check.rule_code for check in failed_checks))
        blocking_reasons = [
            check.rule_code
            for check in failed_checks
            if check.severity == RiskCheckSeverity.BLOCKING
        ]
        allowed = len(blocking_reasons) == 0
        risk_level = self._compute_risk_level(checks)

        return MarketplaceRiskAssessment(
            marketplace=marketplace_input.marketplace,
            recommended_price=marketplace_input.recommended_price,
            current_price=marketplace_input.current_price,
            risk_level=risk_level,
            allowed=allowed,
            reason_codes=reason_codes,
            blocking_reasons=list(dict.fromkeys(blocking_reasons)),
            checks=checks,
        )

    def _check_no_valid_optimization_result(
        self,
        *,
        marketplace_input: MarketplaceRiskInput,
        optimization_summary_status: str | None,
    ) -> RiskCheckResult:
        has_recommendation = marketplace_input.recommended_price is not None
        summary_ok = optimization_summary_status != "NO_VALID_RECOMMENDATION"
        passed = has_recommendation and summary_ok

        return RiskCheckResult(
            rule_code=RiskReasonCode.NO_VALID_OPTIMIZATION_RESULT,
            passed=passed,
            severity=RiskCheckSeverity.BLOCKING,
            message="Optimization produced a valid recommendation."
            if passed
            else "Optimization did not produce a valid recommendation.",
            details={
                "recommended_price": str(marketplace_input.recommended_price)
                if marketplace_input.recommended_price is not None
                else None,
                "optimization_summary_status": optimization_summary_status,
            },
        )

    def _check_selling_below_cost(
        self,
        marketplace_input: MarketplaceRiskInput,
        context: RiskContextInput,
    ) -> RiskCheckResult:
        recommended_price = marketplace_input.recommended_price
        unit_profit = marketplace_input.unit_profit

        below_cost = (
            recommended_price is not None
            and recommended_price < context.cost_price
        )
        non_positive_profit = unit_profit is not None and unit_profit <= 0
        passed = not below_cost and not non_positive_profit

        return RiskCheckResult(
            rule_code=RiskReasonCode.SELLING_BELOW_COST,
            passed=passed,
            severity=RiskCheckSeverity.BLOCKING,
            message="Recommended price is not below cost."
            if passed
            else "Recommended price would sell below cost or with non-positive unit profit.",
            details={
                "recommended_price": str(recommended_price)
                if recommended_price is not None
                else None,
                "cost_price": str(context.cost_price),
                "unit_profit": str(unit_profit) if unit_profit is not None else None,
            },
        )

    def _check_min_margin(
        self,
        marketplace_input: MarketplaceRiskInput,
        context: RiskContextInput,
    ) -> RiskCheckResult:
        unit_margin_rate = marketplace_input.unit_margin_rate
        if unit_margin_rate is None:
            return RiskCheckResult(
                rule_code=RiskReasonCode.MIN_MARGIN_BREACHED,
                passed=True,
                severity=RiskCheckSeverity.BLOCKING,
                message="Unit margin rate is not available; check skipped.",
                details={},
            )

        passed = unit_margin_rate >= context.min_margin_rate
        return RiskCheckResult(
            rule_code=RiskReasonCode.MIN_MARGIN_BREACHED,
            passed=passed,
            severity=RiskCheckSeverity.BLOCKING,
            message="Minimum margin requirement is satisfied."
            if passed
            else "Recommended price does not satisfy the minimum margin requirement.",
            details={
                "unit_margin_rate": str(unit_margin_rate),
                "min_margin_rate": str(context.min_margin_rate),
            },
        )

    def _check_price_change(self, marketplace_input: MarketplaceRiskInput) -> RiskCheckResult:
        current_price = marketplace_input.current_price
        recommended_price = marketplace_input.recommended_price

        if current_price is None or recommended_price is None or current_price <= 0:
            return RiskCheckResult(
                rule_code=RiskReasonCode.PRICE_CHANGE_TOO_AGGRESSIVE,
                passed=True,
                severity=RiskCheckSeverity.WARNING,
                message="Price change check skipped because current or recommended price is missing.",
                details={},
            )

        change_rate = abs(recommended_price - current_price) / current_price
        blocking = change_rate >= PRICE_CHANGE_BLOCKING_RATE
        warning = change_rate >= PRICE_CHANGE_WARNING_RATE
        passed = not warning

        if blocking:
            severity = RiskCheckSeverity.BLOCKING
            message = "Price change exceeds the blocking threshold."
        elif warning:
            severity = RiskCheckSeverity.WARNING
            message = "Price change exceeds the warning threshold."
        else:
            severity = RiskCheckSeverity.INFO
            message = "Price change is within acceptable limits."

        return RiskCheckResult(
            rule_code=RiskReasonCode.PRICE_CHANGE_TOO_AGGRESSIVE,
            passed=passed,
            severity=severity,
            message=message,
            details={
                "current_price": str(current_price),
                "recommended_price": str(recommended_price),
                "change_rate": str(change_rate.quantize(Decimal("0.0001"))),
                "warning_threshold": str(PRICE_CHANGE_WARNING_RATE),
                "blocking_threshold": str(PRICE_CHANGE_BLOCKING_RATE),
            },
        )

    def _check_low_stock_price_decrease(
        self,
        marketplace_input: MarketplaceRiskInput,
        context: RiskContextInput,
    ) -> RiskCheckResult:
        stock_quantity = context.stock_quantity
        current_price = marketplace_input.current_price
        recommended_price = marketplace_input.recommended_price

        if (
            stock_quantity is None
            or current_price is None
            or recommended_price is None
            or stock_quantity >= LOW_STOCK_THRESHOLD
            or recommended_price >= current_price
        ):
            return RiskCheckResult(
                rule_code=RiskReasonCode.LOW_STOCK_PRICE_DECREASE,
                passed=True,
                severity=RiskCheckSeverity.WARNING,
                message="Low-stock price decrease check passed.",
                details={
                    "stock_quantity": stock_quantity,
                    "low_stock_threshold": LOW_STOCK_THRESHOLD,
                },
            )

        return RiskCheckResult(
            rule_code=RiskReasonCode.LOW_STOCK_PRICE_DECREASE,
            passed=False,
            severity=RiskCheckSeverity.WARNING,
            message="Price decrease was recommended while stock is low.",
            details={
                "stock_quantity": stock_quantity,
                "low_stock_threshold": LOW_STOCK_THRESHOLD,
                "current_price": str(current_price),
                "recommended_price": str(recommended_price),
            },
        )

    def _check_noise_driven_undercut(
        self,
        marketplace_input: MarketplaceRiskInput,
        context: RiskContextInput,
    ) -> RiskCheckResult:
        recommended_price = marketplace_input.recommended_price
        min_competitor_price = context.min_competitor_price

        if (
            recommended_price is None
            or min_competitor_price is None
            or recommended_price >= min_competitor_price
        ):
            return RiskCheckResult(
                rule_code=RiskReasonCode.NOISE_DRIVEN_UNDERCUT,
                passed=True,
                severity=RiskCheckSeverity.WARNING,
                message="Recommendation is not below the valid competitor minimum price.",
                details={
                    "min_competitor_price": str(min_competitor_price)
                    if min_competitor_price is not None
                    else None,
                },
            )

        return RiskCheckResult(
            rule_code=RiskReasonCode.NOISE_DRIVEN_UNDERCUT,
            passed=False,
            severity=RiskCheckSeverity.WARNING,
            message="Recommended price is below the valid competitor minimum price.",
            details={
                "recommended_price": str(recommended_price),
                "min_competitor_price": str(min_competitor_price),
            },
        )

    def _check_model_confidence(self, context: RiskContextInput) -> RiskCheckResult:
        n_fold_models = int(context.demand_prediction_meta.get("n_fold_models", 0) or 0)
        passed = n_fold_models == 0 or n_fold_models >= MIN_FOLD_MODELS_FOR_CONFIDENCE

        return RiskCheckResult(
            rule_code=RiskReasonCode.LOW_MODEL_CONFIDENCE,
            passed=passed,
            severity=RiskCheckSeverity.WARNING,
            message="Demand prediction model confidence is acceptable."
            if passed
            else "Demand prediction model confidence is low.",
            details={
                "n_fold_models": n_fold_models,
                "min_fold_models": MIN_FOLD_MODELS_FOR_CONFIDENCE,
                "model_name": context.demand_prediction_meta.get("model_name"),
            },
        )

    def _compute_risk_level(self, checks: list[RiskCheckResult]) -> RiskLevel:
        failed_checks = [check for check in checks if not check.passed]

        if any(
            check.severity == RiskCheckSeverity.BLOCKING
            for check in failed_checks
        ):
            return RiskLevel.HIGH

        if any(
            check.severity == RiskCheckSeverity.WARNING
            for check in failed_checks
        ):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _aggregate_risk_level(
        self,
        assessments: list[MarketplaceRiskAssessment],
    ) -> RiskLevel:
        if not assessments:
            return RiskLevel.HIGH

        return max(
            (assessment.risk_level for assessment in assessments),
            key=lambda level: _RISK_LEVEL_ORDER[level],
        )

    def _select_best_marketplace(
        self,
        assessments: list[MarketplaceRiskAssessment],
    ) -> str | None:
        allowed_assessments = [
            assessment for assessment in assessments if assessment.allowed
        ]
        if not allowed_assessments:
            return assessments[0].marketplace if assessments else None

        low_risk = [
            assessment
            for assessment in allowed_assessments
            if assessment.risk_level == RiskLevel.LOW
        ]
        if low_risk:
            return low_risk[0].marketplace

        return allowed_assessments[0].marketplace