from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


AppEnv = Literal["development", "staging", "production", "test"]


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    agent_service_url: str = "http://localhost:8001"
    data_ingestion_service_url: str = "http://localhost:8004"
    app_env: AppEnv = "development"
    app_debug: bool = True
    cors_origins: str = "*"
    api_request_timeout_seconds: float = Field(default=30, gt=0)
    agent_request_timeout_seconds: float = Field(default=240, gt=0)
    data_ingestion_request_timeout_seconds: float = Field(default=180, gt=0)
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_pre_ping: bool = True

    @property
    def cors_allow_origins(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
