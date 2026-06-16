from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.companies import router as companies_router
from app.routers.products import router as products_router
from app.routers.data_collection import router as data_collection_router
from app.routers.competitors import router as competitors_router
from app.routers.analysis import router as analysis_router
from app.routers.recommendations import router as recommendations_router

app = FastAPI(title="Pricing Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "api_service"}

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(products_router)
app.include_router(data_collection_router)
app.include_router(competitors_router)
app.include_router(analysis_router)
app.include_router(recommendations_router)
