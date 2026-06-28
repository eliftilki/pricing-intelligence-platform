from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.prediction import router as prediction_router
from app.services.model_loader import load_model_bundle
from app.services.prediction_service import PredictionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = load_model_bundle(
        models_dir=settings.models_dir,
        metadata_path=settings.feature_metadata_path,
        model_name=settings.model_name,
    )
    app.state.settings = settings
    app.state.prediction_service = PredictionService(bundle)
    yield


app = FastAPI(
    title="ML Service",
    version="0.1.0",
    description="Demand prediction service for pricing intelligence platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ml_service"}


app.include_router(prediction_router)
