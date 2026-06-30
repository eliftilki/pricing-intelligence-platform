from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.optimization import PricingOptimizationResult
from app.models.product import Product, SellerProduct
from app.schemas.optimization_schema import (
    Marketplace,
    MarketplaceOptimizationInput,
    OptimizationRecordCreate,
    OptimizationResponse,
)


class OptimizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_seller_product_context(self, seller_product_id: UUID) -> dict:
        row = (
            self.db.query(SellerProduct, Product)
            .join(Product, Product.id == SellerProduct.product_id)
            .filter(SellerProduct.id == seller_product_id)
            .first()
        )

        if not row:
            raise ValueError(f"Seller product not found: {seller_product_id}")

        seller_product, product = row

        return {
            "seller_product_id": seller_product.id,
            "company_id": seller_product.company_id,
            "product_id": seller_product.product_id,
            "category_id": product.category_id,
            "marketplace": seller_product.marketplace,
            "current_price": seller_product.our_price,
            "cost_price": seller_product.cost_price,
            "shipping_cost": seller_product.shipping_cost or Decimal("0"),
            "packaging_cost": seller_product.packaging_cost or Decimal("0"),
            "min_margin_rate": seller_product.min_margin_rate or Decimal("0.10"),
            "category": product.category,
        }

    def build_marketplace_input_from_db(
        self,
        seller_product_id: UUID,
        commission_rate: Decimal,
    ) -> MarketplaceOptimizationInput:
        context = self.get_seller_product_context(seller_product_id)
        return self.build_marketplace_input_from_context(context, commission_rate)

    def build_marketplace_input_from_context(
        self,
        context: dict,
        commission_rate: Decimal,
    ) -> MarketplaceOptimizationInput:
        marketplace = Marketplace(str(context["marketplace"]).upper())

        return MarketplaceOptimizationInput(
            marketplace=marketplace,
            seller_product_id=context.get("seller_product_id"),
            cost_price=self._to_decimal(context.get("cost_price")),
            category_id=context.get("category_id"),
            current_price=self._to_decimal(context.get("current_price")),
            commission_rate=commission_rate,
            shipping_cost=self._to_decimal(context.get("shipping_cost")) or Decimal("0"),
            packaging_cost=self._to_decimal(context.get("packaging_cost")) or Decimal("0"),
            min_margin_rate=self._to_decimal(context.get("min_margin_rate")) or Decimal("0.10"),
            market_average_price=self._to_decimal(context.get("market_average_price")),
            metadata={
                "source": "database",
                "category": context.get("category"),
                "category_id": str(context.get("category_id")) if context.get("category_id") else None,
            },
        )

    def save_response(
        self,
        response: OptimizationResponse,
        cost_price: Decimal,
        marketplaces: list[MarketplaceOptimizationInput],
    ) -> None:
        context_by_marketplace = {
            item.marketplace.value: item
            for item in marketplaces
        }

        for result in response.marketplace_results:
            marketplace_context = context_by_marketplace[result.marketplace.value]
            record = OptimizationRecordCreate(
                seller_product_id=(
                    result.seller_product_id or response.seller_product_id
                ),
                product_id=response.product_id,
                category_id=marketplace_context.category_id,
                run_id=response.run_id,
                marketplace=result.marketplace,
                recommended_price=result.recommended_price,
                current_price=result.current_price,
                cost_price=marketplace_context.cost_price or cost_price,
                commission_rate=result.commission_rate,
                shipping_cost=marketplace_context.shipping_cost,
                packaging_cost=marketplace_context.packaging_cost,
                min_margin_rate=marketplace_context.min_margin_rate,
                expected_sales=result.expected_sales,
                unit_profit=result.unit_profit,
                unit_margin_rate=result.unit_margin_rate,
                expected_profit=result.expected_profit,
                profit_uplift_vs_current=result.profit_uplift_vs_current,
                selected_reason=result.selected_reason,
                constraints_applied=[item.value for item in result.constraints_applied],
                evaluated_candidates=[
                    item.model_dump(mode="json")
                    for item in result.evaluated_candidates
                ],
                rejected_candidates=[
                    item.model_dump(mode="json")
                    for item in result.rejected_candidates
                ],
                metadata=result.metadata,
            )
            self.save_record(record)

        self.db.commit()

    def save_record(self, record: OptimizationRecordCreate) -> PricingOptimizationResult:
        db_record = PricingOptimizationResult(
            seller_product_id=record.seller_product_id,
            product_id=record.product_id,
            category_id=record.category_id,
            run_id=record.run_id,
            marketplace=record.marketplace.value,
            recommended_price=record.recommended_price,
            current_price=record.current_price,
            cost_price=record.cost_price,
            commission_rate=record.commission_rate,
            shipping_cost=record.shipping_cost,
            packaging_cost=record.packaging_cost,
            min_margin_rate=record.min_margin_rate,
            expected_sales=record.expected_sales,
            unit_profit=record.unit_profit,
            unit_margin_rate=record.unit_margin_rate,
            expected_profit=record.expected_profit,
            profit_uplift_vs_current=record.profit_uplift_vs_current,
            selected_reason=record.selected_reason,
            constraints_applied=record.constraints_applied,
            evaluated_candidates=record.evaluated_candidates,
            rejected_candidates=record.rejected_candidates,
            metadata_json=record.metadata,
        )

        self.db.add(db_record)
        self.db.flush()
        return db_record

    def _to_decimal(self, value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))
