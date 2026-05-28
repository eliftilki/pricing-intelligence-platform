from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    agent_service_url: str = "http://localhost:8001"
    app_env: str = "development"
    app_debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()