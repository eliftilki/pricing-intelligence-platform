from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


AppEnv = Literal["development", "staging", "production", "test"]


class Settings(BaseSettings):
    database_url: str
    app_env: AppEnv = "development"
    app_debug: bool = True
    cors_origins: str = "*"
    collector_timeout_seconds: float = Field(default=60, gt=0)
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
