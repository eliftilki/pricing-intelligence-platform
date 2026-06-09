from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.supabase_client import supabase, supabase_admin
from app.repositories.company_repository import CompanyRepository
from app.schemas.auth_schema import RegisterRequest, LoginRequest
from app.schemas.company_schema import CompanyCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)

    def register(self, payload: RegisterRequest):
        company = self.company_repo.create(CompanyCreate(name=payload.company_name))
        try:
            result = supabase_admin.auth.admin.create_user({
                "email": payload.email,
                "password": payload.password,
                "email_confirm": True,
            })
            user = result.user
            self.company_repo.create_user_profile(user.id, company.id, payload.full_name)
            login = supabase.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
            return {
                "access_token": login.session.access_token,
                "refresh_token": login.session.refresh_token,
                "user_id": user.id,
                "company_id": company.id,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    def login(self, payload: LoginRequest):
        try:
            login = supabase.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
            user_id = login.user.id
            from app.models.company import UserProfile
            profile = self.db.query(UserProfile).filter(UserProfile.id == user_id).first()
            if not profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            return {
                "access_token": login.session.access_token,
                "refresh_token": login.session.refresh_token,
                "user_id": user_id,
                "company_id": profile.company_id,
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=401, detail=str(exc))
