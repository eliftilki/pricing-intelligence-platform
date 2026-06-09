from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.pricing_repository import PricingRepository
from app.repositories.product_repository import ProductRepository


class PricingService:
    def __init__(self, db: Session):
        self.repo = PricingRepository(db)
        self.product_repo = ProductRepository(db)

    def list_recommendations(self, seller_product_id: UUID, limit: int = 20, offset: int = 0):
        return self.repo.list_recommendations(seller_product_id, limit, offset)

    def approve(self, recommendation_id: UUID, note: str | None, user_id=None):
        rec = self.repo.get_recommendation(recommendation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        self.repo.set_status(rec, "APPROVED")
        return self.repo.create_decision(rec, "APPROVED", note, user_id)

    def reject(self, recommendation_id: UUID, note: str | None, user_id=None):
        rec = self.repo.get_recommendation(recommendation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        self.repo.set_status(rec, "REJECTED")
        return self.repo.create_decision(rec, "REJECTED", note, user_id)

    def apply(self, recommendation_id: UUID, note: str | None, user_id=None):
        rec = self.repo.get_recommendation(recommendation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        sp = self.product_repo.get_seller_product(rec.seller_product_id)
        if not sp:
            raise HTTPException(status_code=404, detail="Seller product not found")
        self.product_repo.update_price(sp, rec.recommended_price, "SYSTEM_RECOMMENDATION", user_id, rec.id)
        self.repo.set_status(rec, "APPLIED")
        return self.repo.create_decision(rec, "APPLIED", note, user_id)
