from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    app_env: str = "development"
    app_debug: bool = True
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    slm_service_url: str = "http://localhost:8003"
    slm_explanation_timeout_seconds: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
