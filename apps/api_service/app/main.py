from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.data_collection import router as data_collection_router
from app.routers.intelligence import router as intelligence_router


app = FastAPI(
    title="Pricing Intelligence API",
    version="0.1.0",
    description="Marketplace sellers için AI destekli pricing intelligence backend API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "api_service",
    }

app.include_router(data_collection_router)
app.include_router(intelligence_router)


