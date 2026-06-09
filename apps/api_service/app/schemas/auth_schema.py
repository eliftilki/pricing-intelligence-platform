from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    user_id: UUID
    company_id: UUID
