from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.ingestion import router as ingestion_router


app = FastAPI(
    title="Data Ingestion Service",
    version="0.1.0",
    description="Marketplace competitor data collection service.",
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
        "service": "data_ingestion_service",
    }


app.include_router(ingestion_router)