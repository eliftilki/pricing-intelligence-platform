from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.repositories.company_repository import CompanyRepository
from app.schemas.company_schema import CompanyCreate, CompanyOut

router = APIRouter(prefix="/companies", tags=["Companies"])

@router.post("", response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    return CompanyRepository(db).create(payload)

@router.get("", response_model=list[CompanyOut])
def list_companies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return CompanyRepository(db).list(limit, offset)

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    return CompanyRepository(db).get(company_id)
