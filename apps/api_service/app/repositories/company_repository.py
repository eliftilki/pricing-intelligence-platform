from sqlalchemy.orm import Session
from uuid import UUID
from app.models.company import Company, UserProfile
from app.repositories.base_repository import BaseRepository
from app.schemas.company_schema import CompanyCreate


class CompanyRepository(BaseRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: CompanyCreate) -> Company:
        obj = Company(**payload.model_dump())
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get(self, company_id: UUID):
        return self.db.query(Company).filter(Company.id == company_id).first()

    def list(self, limit: int = 100, offset: int = 0):
        query = self.db.query(Company).order_by(Company.created_at.desc())
        return self.paginate(query, limit, offset).all()

    def create_user_profile(self, user_id: UUID, company_id: UUID, full_name: str, role: str = "owner"):
        profile = UserProfile(id=user_id, company_id=company_id, full_name=full_name, role=role)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
