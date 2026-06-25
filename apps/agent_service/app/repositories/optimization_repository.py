from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
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

    def get_marketplace_commission_rate(
        self,
        marketplace: Marketplace,
        category: str | None,
    ) -> Decimal | None:
        if not category:
            return None

        query = text(
            """
            SELECT commission_rate
            FROM public.marketplace_commission_rules
            WHERE marketplace = :marketplace
              AND category = :category
              AND is_active = true
            LIMIT 1
            """
        )

        try:
            row = self.db.execute(
                query,
                {"marketplace": marketplace.value, "category": category},
            ).mappings().first()
        except SQLAlchemyError:
            self.db.rollback()
            return None

        return Decimal(str(row["commission_rate"])) if row else None

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
            "product_id": seller_product.product_id,
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
    ) -> MarketplaceOptimizationInput:
        context = self.get_seller_product_context(seller_product_id)
        marketplace = Marketplace(str(context["marketplace"]).upper())
        commission_rate = self.get_marketplace_commission_rate(
            marketplace=marketplace,
            category=context.get("category"),
        )

        return MarketplaceOptimizationInput(
            marketplace=marketplace,
            current_price=self._to_decimal(context.get("current_price")),
            commission_rate=commission_rate,
            shipping_cost=self._to_decimal(context.get("shipping_cost")) or Decimal("0"),
            packaging_cost=self._to_decimal(context.get("packaging_cost")) or Decimal("0"),
            min_margin_rate=self._to_decimal(context.get("min_margin_rate")) or Decimal("0.10"),
            metadata={"source": "database", "category": context.get("category")},
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
                seller_product_id=response.seller_product_id,
                product_id=response.product_id,
                run_id=response.run_id,
                marketplace=result.marketplace,
                recommended_price=result.recommended_price,
                current_price=result.current_price,
                cost_price=cost_price,
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
