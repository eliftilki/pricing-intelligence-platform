from fastapi import APIRouter

from app.schemas.data_collection_schema import (
    DataCollectionRunRequest,
    DataCollectionRunResponse,
)
from app.services.data_ingestion_client import data_ingestion_client


router = APIRouter(prefix="/data-collection", tags=["Data Collection"])


@router.post("/run", response_model=DataCollectionRunResponse)
async def run_data_collection(payload: DataCollectionRunRequest):
    return await data_ingestion_client.run_collection(payload)