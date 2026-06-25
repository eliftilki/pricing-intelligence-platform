from fastapi import APIRouter, HTTPException

from app.schemas.explanation_schema import (
    ExplanationRequest,
    ExplanationResponse,
)
from app.services.prompt_builder import PromptBuilder
from app.services.hf_slm_service import slm_service


router = APIRouter(
    prefix="/explanations",
    tags=["SLM Explanations"],
)


@router.post("/generate", response_model=ExplanationResponse)
def generate_explanation(request: ExplanationRequest) -> ExplanationResponse:
    try:
        messages = PromptBuilder.build(request)
        explanation = slm_service.generate(messages)

        return ExplanationResponse(
            explanation=explanation,
            model_name=slm_service.model_name,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"SLM explanation generation failed: {str(exc)}",
        )