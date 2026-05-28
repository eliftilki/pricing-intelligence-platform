from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware




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


