from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.repositories.competitor_repository import CompetitorRepository
from app.schemas.competitor_schema import CompetitorListingOut, CompetitorTierOut

router = APIRouter(prefix="/competitors", tags=["Competitors"])

@router.get("/products/{product_id}/listings", response_model=list[CompetitorListingOut])
def list_listings(
    product_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return CompetitorRepository(db).list_latest_listings(product_id, limit, offset)

@router.get("/products/{product_id}/tiers", response_model=list[CompetitorTierOut])
def list_tiers(
    product_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return CompetitorRepository(db).list_tiers(product_id, limit, offset)
