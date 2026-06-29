from app.schemas.slm_explanation_schema import SLMExplanationRequest
from app.services.slm_explanation_client import slm_explanation_client


async def slm_explanation_node(state: dict) -> dict:
    recommendation = state.get("recommendation")

    if not recommendation:
        state["slm_explanation"] = None
        state.setdefault("errors", []).append("RECOMMENDATION_NOT_FOUND_FOR_SLM")
        return state

    request = SLMExplanationRequest(
        product_name=recommendation.get("product_name", "Unknown Product"),
        marketplace=recommendation.get("marketplace", "UNKNOWN"),

        current_price=(
            float(recommendation["current_price"])
            if recommendation.get("current_price") is not None
            else None
        ),
        recommended_price=float(recommendation.get("recommended_price", 0)),
        action=recommendation.get("action"),

        expected_sales=recommendation.get("expected_sales"),
        unit_profit=recommendation.get("unit_profit"),
        expected_profit=recommendation.get("expected_profit"),
        profit_uplift=recommendation.get("profit_uplift"),

        commission_rate=recommendation.get("commission_rate"),
        risk_level=recommendation.get("risk_level"),
        selected_reason=recommendation.get("selected_reason"),
        reason_codes=recommendation.get("reason_codes") or [],

        competitor_min_price=recommendation.get("competitor_min_price"),
        competitor_avg_price=recommendation.get("competitor_avg_price"),
        tier1_min_price=recommendation.get("tier1_min_price"),
        analysis_warnings=state.get("warnings") or [],
    )

    try:
        response = await slm_explanation_client.generate_explanation(request)

        state["slm_explanation"] = {
            "explanation": response.explanation,
            "model_name": response.model_name,
        }

    except Exception as exc:
        state["slm_explanation"] = None
        state.setdefault("errors", []).append(
            f"SLM_EXPLANATION_FAILED: {str(exc)}"
        )

    return state
