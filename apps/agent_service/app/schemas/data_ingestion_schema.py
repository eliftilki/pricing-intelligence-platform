from uuid import UUID

from pydantic import BaseModel, Field


class DataIngestionRunRequest(BaseModel):
    product_id: UUID
    marketplaces: list[str] = Field(min_length=1)


class DataIngestionSearchAndRunRequest(DataIngestionRunRequest):
    company_id: UUID
    query: str = Field(min_length=2)


class DataIngestionRunResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
    scrape_counts: dict[str, int] = Field(default_factory=dict)
