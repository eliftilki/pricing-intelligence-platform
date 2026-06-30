from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.optimization_schema import (
    CandidateOptimizationEvaluation,
    DemandPredictionItem,
    MarketplaceOptimizationInput,
    MarketplaceOptimizationResult,
    OptimizationConstraintCode,
    OptimizationRequest,
    OptimizationResponse,
    RejectionReason,
)

MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.000001")
NEAR_OPTIMAL_PROFIT_TOLERANCE_RATE = Decimal("0.03")


def q_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def q_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


class OptimizationService:
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        marketplace_results = [
            self._optimize_marketplace(
                cost_price=(
                    marketplace_context.cost_price or request.cost_price
                ),
                marketplace_context=marketplace_context,
                demand_predictions=request.demand_predictions,
            )
            for marketplace_context in request.marketplaces
        ]

        return OptimizationResponse(
            seller_product_id=request.seller_product_id,
            product_id=request.product_id,
            run_id=request.run_id,
            generated_at=datetime.now(timezone.utc),
            marketplace_results=marketplace_results,
            summary=self._build_summary(marketplace_results),
        )

    def _optimize_marketplace(
        self,
        cost_price: Decimal,
        marketplace_context: MarketplaceOptimizationInput,
        demand_predictions: list[DemandPredictionItem],
    ) -> MarketplaceOptimizationResult:
        constraints_applied = [
            OptimizationConstraintCode.MIN_MARGIN_APPLIED,
            OptimizationConstraintCode.MARKETPLACE_COMMISSION_APPLIED,
        ]

        if marketplace_context.current_price is not None:
            if marketplace_context.max_price_increase_rate is not None:
                constraints_applied.append(OptimizationConstraintCode.MAX_PRICE_INCREASE_APPLIED)
            if marketplace_context.max_price_decrease_rate is not None:
                constraints_applied.append(OptimizationConstraintCode.MAX_PRICE_DECREASE_APPLIED)

        evaluations = [
            self._evaluate_candidate(
                price=prediction.price,
                expected_sales=prediction.expected_sales,
                cost_price=cost_price,
                marketplace_context=marketplace_context,
                prediction_metadata=prediction.metadata,
                confidence=prediction.confidence,
            )
            for prediction in demand_predictions
        ]

        valid_candidates = [item for item in evaluations if item.is_valid]
        rejected_candidates = [item for item in evaluations if not item.is_valid]

        if not valid_candidates:
            return MarketplaceOptimizationResult(
                marketplace=marketplace_context.marketplace,
                seller_product_id=marketplace_context.seller_product_id,
                cost_price=cost_price,
                current_price=marketplace_context.current_price,
                commission_rate=marketplace_context.commission_rate,
                constraints_applied=constraints_applied,
                selected_reason="No valid candidate satisfied optimization constraints.",
                evaluated_candidates=evaluations,
                rejected_candidates=rejected_candidates,
                metadata={"valid_candidate_count": 0},
            )

        max_expected_profit = max(item.expected_profit for item in valid_candidates)
        near_optimal_profit_floor = max_expected_profit * (
            Decimal("1") - NEAR_OPTIMAL_PROFIT_TOLERANCE_RATE
        )
        near_optimal_candidates = [
            item
            for item in valid_candidates
            if item.expected_profit >= near_optimal_profit_floor
        ]
        constraints_applied.append(
            OptimizationConstraintCode.NEAR_OPTIMAL_PROFIT_REGION_APPLIED
        )

        if marketplace_context.market_average_price is not None:
            best = min(
                near_optimal_candidates,
                key=lambda item: (
                    abs(item.price - marketplace_context.market_average_price),
                    -item.expected_sales,
                    -item.expected_profit,
                ),
            )
            constraints_applied.append(
                OptimizationConstraintCode.MARKET_AVERAGE_PROXIMITY_APPLIED
            )
        else:
            best = max(
                near_optimal_candidates,
                key=lambda item: (
                    item.expected_profit,
                    item.unit_margin_rate,
                    item.expected_sales,
                ),
            )

        constraints_applied.append(OptimizationConstraintCode.BEST_EXPECTED_PROFIT_SELECTED)

        evaluated_price_bounds = (
            min(item.price for item in evaluations),
            max(item.price for item in evaluations),
        )
        warnings: list[str] = []
        if best.price in evaluated_price_bounds:
            constraints_applied.append(OptimizationConstraintCode.BOUNDARY_OPTIMUM)
            warnings.append(OptimizationConstraintCode.BOUNDARY_OPTIMUM.value)

        current_profit = self._calculate_current_price_expected_profit(
            current_price=marketplace_context.current_price,
            evaluations=evaluations,
        )
        uplift = None
        if current_profit is not None and current_profit != 0:
            uplift = q_rate((best.expected_profit - current_profit) / abs(current_profit))

        return MarketplaceOptimizationResult(
            marketplace=marketplace_context.marketplace,
            seller_product_id=marketplace_context.seller_product_id,
            cost_price=cost_price,
            recommended_price=best.price,
            current_price=marketplace_context.current_price,
            commission_rate=marketplace_context.commission_rate,
            expected_sales=best.expected_sales,
            unit_profit=best.unit_profit,
            unit_margin_rate=best.unit_margin_rate,
            expected_profit=best.expected_profit,
            profit_uplift_vs_current=uplift,
            constraints_applied=constraints_applied,
            selected_reason=(
                "Closest price to the market average among candidates within 3% of "
                "the highest expected profit."
                if marketplace_context.market_average_price is not None
                else "Highest expected profit among valid near-optimal candidates."
            ),
            evaluated_candidates=evaluations,
            rejected_candidates=rejected_candidates,
            metadata={
                "valid_candidate_count": len(valid_candidates),
                "rejected_candidate_count": len(rejected_candidates),
                "near_optimal_candidate_count": len(near_optimal_candidates),
                "near_optimal_profit_tolerance_rate": str(
                    NEAR_OPTIMAL_PROFIT_TOLERANCE_RATE
                ),
                "market_average_price": (
                    str(marketplace_context.market_average_price)
                    if marketplace_context.market_average_price is not None
                    else None
                ),
                "max_expected_profit": str(max_expected_profit),
                "warnings": warnings,
            },
        )

    def _evaluate_candidate(
        self,
        price: Decimal,
        expected_sales: Decimal,
        cost_price: Decimal,
        marketplace_context: MarketplaceOptimizationInput,
        prediction_metadata: dict | None = None,
        confidence: Decimal | None = None,
    ) -> CandidateOptimizationEvaluation:
        rejection_reasons: list[RejectionReason] = []

        if price <= 0:
            rejection_reasons.append(RejectionReason.NEGATIVE_OR_ZERO_PRICE)
        if expected_sales < 0:
            rejection_reasons.append(RejectionReason.NEGATIVE_EXPECTED_SALES)
        if marketplace_context.commission_rate is None:
            rejection_reasons.append(RejectionReason.MISSING_COMMISSION_RULE)

        commission_rate = marketplace_context.commission_rate or Decimal("0")
        commission_amount = q_money(price * commission_rate)
        unit_profit = q_money(
            price
            - cost_price
            - commission_amount
            - marketplace_context.shipping_cost
            - marketplace_context.packaging_cost
        )
        unit_margin_rate = q_rate(unit_profit / price) if price > 0 else Decimal("0")
        expected_profit = q_money(unit_profit * expected_sales)

        if unit_profit <= 0:
            rejection_reasons.append(RejectionReason.INVALID_UNIT_PROFIT)
        if unit_margin_rate < marketplace_context.min_margin_rate:
            rejection_reasons.append(RejectionReason.MIN_MARGIN_NOT_MET)

        if marketplace_context.current_price is not None:
            if marketplace_context.max_price_increase_rate is not None:
                max_allowed_price = marketplace_context.current_price * (
                    Decimal("1") + marketplace_context.max_price_increase_rate
                )
                if price > max_allowed_price:
                    rejection_reasons.append(RejectionReason.PRICE_INCREASE_TOO_HIGH)

            if marketplace_context.max_price_decrease_rate is not None:
                min_allowed_price = marketplace_context.current_price * (
                    Decimal("1") - marketplace_context.max_price_decrease_rate
                )
                if price < min_allowed_price:
                    rejection_reasons.append(RejectionReason.PRICE_DECREASE_TOO_HIGH)

        is_valid = len(rejection_reasons) == 0
        score = expected_profit if is_valid else Decimal("0")

        return CandidateOptimizationEvaluation(
            price=q_money(price),
            expected_sales=expected_sales,
            commission_amount=commission_amount,
            unit_profit=unit_profit,
            unit_margin_rate=unit_margin_rate,
            expected_profit=expected_profit,
            is_valid=is_valid,
            rejection_reasons=rejection_reasons,
            score=q_money(score),
            metadata={
                "confidence": str(confidence) if confidence is not None else None,
                "prediction_metadata": prediction_metadata or {},
            },
        )

    def _calculate_current_price_expected_profit(
        self,
        current_price: Decimal | None,
        evaluations: list[CandidateOptimizationEvaluation],
    ) -> Decimal | None:
        if current_price is None:
            return None

        for item in evaluations:
            if item.price == q_money(current_price):
                return item.expected_profit

        return None

    def _build_summary(
        self,
        marketplace_results: list[MarketplaceOptimizationResult],
    ) -> dict[str, object]:
        valid_results = [
            result
            for result in marketplace_results
            if result.recommended_price is not None
        ]

        if not valid_results:
            return {"status": "NO_VALID_RECOMMENDATION", "best_marketplace": None}

        best_marketplace = max(
            valid_results,
            key=lambda item: item.expected_profit or Decimal("0"),
        )

        return {
            "status": "OK",
            "best_marketplace": best_marketplace.marketplace.value,
            "best_recommended_price": str(best_marketplace.recommended_price),
            "best_expected_profit": str(best_marketplace.expected_profit),
        }
