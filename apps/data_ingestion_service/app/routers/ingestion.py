from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.competitor_repository import CompetitorRepository
from app.schemas.ingestion_schema import (
    IngestionRunRequest,
    IngestionRunResponse,
    ProductCreateRequest,
    ProductCreateResponse,
)
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/run", response_model=IngestionRunResponse)
async def run_ingestion(payload: IngestionRunRequest, db: Session = Depends(get_db)):
    service = IngestionService(db)
    return await service.run(payload)


@router.post("/products", response_model=ProductCreateResponse)
def create_product(payload: ProductCreateRequest, db: Session = Depends(get_db)):
    repo = CompetitorRepository(db)

    product = repo.create_product(
        name=payload.name,
        brand=payload.brand,
        category=payload.category,
    )

    seller_product_ids = {}
    for marketplace, url in payload.marketplace_urls.items():
        sp = repo.create_seller_product(
            company_id=payload.company_id,
            product_id=product.id,
            marketplace=marketplace.upper(),
            url=url,
        )
        seller_product_ids[marketplace.upper()] = sp.id

    db.commit()

    return ProductCreateResponse(
        product_id=product.id,
        seller_product_ids=seller_product_ids,
    )
