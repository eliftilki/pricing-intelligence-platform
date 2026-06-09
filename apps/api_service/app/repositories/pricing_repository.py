from uuid import UUID
from sqlalchemy.orm import Session
from app.models.pricing import PriceRecommendation, PricingDecision
from app.models.product import SellerProduct
from app.repositories.base_repository import BaseRepository


class PricingRepository(BaseRepository):
    def __init__(self, db: Session):
        self.db = db

    def list_recommendations(self, seller_product_id: UUID, limit: int = 20, offset: int = 0):
        query = (
            self.db.query(PriceRecommendation)
            .filter(PriceRecommendation.seller_product_id == seller_product_id)
            .order_by(PriceRecommendation.created_at.desc())
        )
        return self.paginate(query, limit, offset).all()

    def get_recommendation(self, recommendation_id: UUID):
        return self.db.query(PriceRecommendation).filter(PriceRecommendation.id == recommendation_id).first()

    def set_status(self, recommendation: PriceRecommendation, status: str):
        recommendation.status = status
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def create_decision(self, recommendation: PriceRecommendation, status: str, note: str | None, user_id=None):
        decision = PricingDecision(
            company_id=recommendation.company_id,
            product_id=recommendation.product_id,
            seller_product_id=recommendation.seller_product_id,
            recommendation_id=recommendation.id,
            old_price=recommendation.current_price,
            new_price=recommendation.recommended_price,
            decision_status=status,
            decided_by=user_id,
            decision_note=note,
        )
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision
