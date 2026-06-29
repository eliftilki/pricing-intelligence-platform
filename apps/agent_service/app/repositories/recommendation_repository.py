from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.price_recommendation import PriceRecommendation


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        recommendation: dict[str, Any],
        ids: dict[str, Optional[UUID]],
        explanation: Optional[str],
    ) -> PriceRecommendation:
        record = PriceRecommendation(
            company_id=ids.get("company_id"),
            product_id=ids.get("product_id"),
            seller_product_id=ids.get("seller_product_id"),
            current_price=recommendation.get("current_price"),
            recommended_price=recommendation["recommended_price"],
            action=recommendation["action"],
            expected_sales_quantity=recommendation.get("expected_sales"),
            expected_profit=recommendation.get("expected_profit"),
            profit_uplift=recommendation.get("profit_uplift"),
            confidence_score=recommendation.get("confidence_score"),
            risk_level=recommendation.get("risk_level"),
            reason_codes=recommendation.get("reason_codes"),
            explanation=explanation,
        )

        self.db.add(record)
        self.db.commit()
        return record

    def rollback(self) -> None:
        self.db.rollback()
