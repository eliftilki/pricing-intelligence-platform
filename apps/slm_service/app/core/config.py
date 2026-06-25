from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    hf_token: str | None = None
    hf_model_name: str = "Qwen/Qwen2.5-3B-Instruct"

    app_env: str = "development"
    app_debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8003

    max_new_tokens: int = 350
    temperature: float = 0.3
    top_p: float = 0.9

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()