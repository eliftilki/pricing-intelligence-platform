from sqlalchemy.orm import Session

from app.repositories.candidate_price_repository import CandidatePriceRepository
from app.schemas.candidate_price_schema import (
    CandidatePriceGenerateRequest,
)
from app.services.candidate_price_generator_service import CandidatePriceGeneratorService


def candidate_price_generator_node(state: dict, db: Session) -> dict:
    product_id = state.get("product_id")

    if not product_id:
        state["status"] = "FAILED"
        state["failed_stage"] = "candidate_price_generator"
        state["message"] = "product_id is missing. Candidate price generation cannot run."
        return state

    request = CandidatePriceGenerateRequest(
        product_id=product_id,
        seller_product_id=state.get("seller_product_id"),
    )

    repository = CandidatePriceRepository(db)

    try:
        context = repository.build_context_from_product(request)
    except ValueError as exc:
        state["status"] = "FAILED"
        state["failed_stage"] = "candidate_price_generator"
        state["message"] = str(exc)
        return state

    service = CandidatePriceGeneratorService()

    result = service.generate(context=context)

    state["candidate_price_result"] = result.model_dump()
    state["candidate_prices"] = result.candidate_prices
    state["selected_candidate_strategy"] = result.selected_strategy.value
    state["seller_product_id"] = result.seller_product_id
    state["status"] = "SUCCESS"

    return state
