from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.competitor_intelligence import router as competitor_intelligence_router


app = FastAPI(
    title="Agent Service",
    version="0.1.0",
    description="Pricing Intelligence Agent Service",
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
        "service": "agent_service",
    }


app.include_router(competitor_intelligence_router)