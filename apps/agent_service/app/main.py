import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.core.config import settings
from app.routers.competitor_intelligence import router as competitor_intelligence_router
from app.routers.candidate_price import router as candidate_price_router
from app.routers.admin import router as admin_router
from app.routers.optimization import router as optimization_router
from app.routers.pricing_intelligence import router as pricing_intelligence_router

logger = logging.getLogger("agent_service")

app = FastAPI(
    title="Agent Service",
    version="0.1.0",
    description="feraSet Agent Service",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def warn_if_admin_key_missing_in_production():
    if settings.app_env == "production" and not settings.admin_api_key:
        logger.warning(
            "ADMIN_API_KEY tanimli degil: production ortaminda /admin endpoint'leri kapali olacak."
        )


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "agent_service"}


app.include_router(competitor_intelligence_router)
app.include_router(pricing_intelligence_router)
app.include_router(candidate_price_router)
app.include_router(admin_router)
app.include_router(optimization_router)
