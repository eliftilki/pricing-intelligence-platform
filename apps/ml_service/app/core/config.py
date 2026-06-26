from pathlib import Path 
from typing import Literal 
from pydantic_settings import BaseSettings 

AppEnv = Literal["development", "staging", "production", "test"] 

ML_SERVICE_ROOT = Path(__file__).resolve().parents[2] 

class Settings(BaseSettings):
    app_env: AppEnv = "development" 
    app_debug: bool = True 
    cors_origins: str = "*" 

    model_name: str = "catboost" 
    models_dir: Path = ML_SERVICE_ROOT / "training" / "models" / "raw" / "catboost" 
    feature_metadata_path: Path = (
        ML_SERVICE_ROOT / "training" / "data" / "model_splits" / "feature_metadata.json"
    ) 

    class Config:
        env_file = ".env" 
        extra = "ignore" 

    @property
    def cors_allow_origins(self) -> list[str]: 
        if self.cors_origins.strip() == "*": 
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
