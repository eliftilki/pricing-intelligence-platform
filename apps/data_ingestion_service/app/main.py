import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.ingestion import router as ingestion_router
from app.routers.search import router as search_router


app = FastAPI(
    title="Data Ingestion Service",
    version="0.1.0",
    description="feraSet marketplace competitor data collection service.",
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
    return {
        "status": "ok",
        "service": "data_ingestion_service",
    }


app.include_router(ingestion_router)
app.include_router(search_router)
