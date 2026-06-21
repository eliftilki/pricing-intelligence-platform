from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.candidate_price_repository import CandidatePriceRepository
from app.schemas.candidate_price_schema import (
    CandidatePriceGenerateRequest,
    CandidatePriceGenerateResponse,
)
from app.services.candidate_price_generator_service import CandidatePriceGeneratorService


router = APIRouter(
    prefix="/candidate-prices",
    tags=["Candidate Price Generator"],
)


@router.post("/generate", response_model=CandidatePriceGenerateResponse)
def generate_candidate_prices(
    request: CandidatePriceGenerateRequest,
    db: Session = Depends(get_db),
):
    repository = CandidatePriceRepository(db)

    try:
        context = repository.build_context_from_product(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = CandidatePriceGeneratorService()

    result = service.generate(
        context=context,
        strategy=request.strategy,
    )

    if request.persist:
        repository.save_result(result)

    return result