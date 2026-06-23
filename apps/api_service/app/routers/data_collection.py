from fastapi import APIRouter

from app.schemas.data_collection_schema import (
    DataCollectionProductCreateRequest,
    DataCollectionProductCreateResponse,
    DataCollectionRunRequest,
    DataCollectionRunResponse,
    DataCollectionSearchAndRunRequest,
)
from app.services.data_ingestion_client import data_ingestion_client


router = APIRouter(prefix="/data-collection", tags=["Data Collection"])


@router.post("/run", response_model=DataCollectionRunResponse)
async def run_data_collection(payload: DataCollectionRunRequest):
    return await data_ingestion_client.run_collection(payload)


@router.post("/search-and-run", response_model=DataCollectionRunResponse)
async def search_and_run_data_collection(payload: DataCollectionSearchAndRunRequest):
    return await data_ingestion_client.search_and_run(payload)


@router.post("/products", response_model=DataCollectionProductCreateResponse)
async def create_data_collection_product(payload: DataCollectionProductCreateRequest):
    return await data_ingestion_client.create_product(payload)
