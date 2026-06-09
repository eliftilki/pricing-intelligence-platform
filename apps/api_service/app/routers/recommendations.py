from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.pricing_schema import PriceRecommendationOut, RecommendationDecisionRequest
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get("/seller-products/{seller_product_id}", response_model=list[PriceRecommendationOut])
def list_recommendations(
    seller_product_id: UUID,
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return PricingService(db).list_recommendations(seller_product_id, limit, offset)

@router.post("/{recommendation_id}/approve")
def approve(recommendation_id: UUID, payload: RecommendationDecisionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return PricingService(db).approve(recommendation_id, payload.decision_note, user_id=user["id"])

@router.post("/{recommendation_id}/reject")
def reject(recommendation_id: UUID, payload: RecommendationDecisionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return PricingService(db).reject(recommendation_id, payload.decision_note, user_id=user["id"])

@router.post("/{recommendation_id}/apply")
def apply(recommendation_id: UUID, payload: RecommendationDecisionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return PricingService(db).apply(recommendation_id, payload.decision_note, user_id=user["id"])
