from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.routers.explanation import router as explanation_router
from app.services.hf_slm_service import slm_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    if settings.app_env != "test":
        slm_service.load_model()

    yield


app = FastAPI(
    title="SLM Explanation Service",
    description="Hugging Face based local SLM service for pricing explanation generation.",
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "slm_service",
        "model_name": settings.hf_model_name,
    }


app.include_router(explanation_router)