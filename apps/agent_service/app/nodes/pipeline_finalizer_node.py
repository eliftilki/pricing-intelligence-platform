from __future__ import annotations


STAGE_LABELS = {
    "data_ingestion": "data ingestion",
    "competitor_intelligence": "competitor intelligence",
    "feature_engineering": "feature engineering",
    "candidate_price_generator": "candidate price generation",
    "demand_prediction": "demand prediction",
    "optimization": "optimization",
    "recommendation": "recommendation generation",
}


def pipeline_finalizer_node(state: dict) -> dict:
    """Build the public pipeline status from all requested stages."""
    completed_stages = _completed_stages(state)
    failed_stage = state.get("failed_stage")

    if state.get("status") == "FAILED":
        original_message = state.get("message") or "Unknown pipeline error."
        stage_label = STAGE_LABELS.get(failed_stage, failed_stage or "unknown stage")
        state["message"] = f"Pricing pipeline failed at {stage_label}: {original_message}"
        state["pipeline_summary"] = {
            "outcome": "FAILED",
            "completed_stages": completed_stages,
            "failed_stage": failed_stage,
            "warning_count": len(state.get("warnings") or []),
            "error_count": len(state.get("errors") or []),
        }
        return state

    partial_reasons = _partial_reasons(state)
    if partial_reasons:
        state["status"] = "PARTIAL_SUCCESS"
        state["message"] = (
            "Pricing pipeline completed with partial success: "
            + " ".join(partial_reasons)
        )
    else:
        state["status"] = "SUCCESS"
        state["message"] = _success_message(state)

    state["pipeline_summary"] = {
        "outcome": state["status"],
        "completed_stages": completed_stages,
        "failed_stage": None,
        "warning_count": len(state.get("warnings") or []),
        "error_count": len(state.get("errors") or []),
    }
    return state


def _completed_stages(state: dict) -> list[str]:
    completed: list[str] = []
    ingestion_status = str((state.get("ingestion_result") or {}).get("status", "")).upper()
    if ingestion_status in {"COMPLETED", "PARTIAL"}:
        completed.append("data_ingestion")
    if "results" in state or state.get("analyzed_count") is not None:
        completed.append("competitor_intelligence")
    event_status = str((state.get("market_event_features") or {}).get("status", "")).upper()
    if state.get("market_event_features") and event_status != "FAILED":
        completed.append("event_agent")
    if state.get("pricing_features"):
        completed.append("feature_engineering")
    if state.get("candidate_price_result"):
        completed.append("candidate_price_generator")
    if state.get("demand_prediction_meta"):
        completed.append("demand_prediction")
    if state.get("optimization_result"):
        completed.append("optimization")
    if state.get("recommendation"):
        completed.append("recommendation")
    if state.get("slm_explanation"):
        completed.append("slm_explanation")
    if (state.get("recommendation_persistence") or {}).get("status") == "PERSISTED":
        completed.append("recommendation_persistence")
    return completed


def _partial_reasons(state: dict) -> list[str]:
    reasons: list[str] = []
    ingestion_status = str((state.get("ingestion_result") or {}).get("status", "")).upper()
    if ingestion_status == "PARTIAL":
        reasons.append("Marketplace ingestion was only partially successful.")

    event_status = str((state.get("market_event_features") or {}).get("status", "")).upper()
    if event_status == "FAILED":
        reasons.append("Market event analysis failed and neutral/fallback signals were used.")

    if state.get("run_optimization"):
        if not state.get("recommendation"):
            reasons.append("Optimization completed but no valid recommendation was produced.")
        elif not state.get("slm_explanation"):
            reasons.append("The recommendation was produced but its SLM explanation failed.")

    persistence_status = (state.get("recommendation_persistence") or {}).get("status")
    if persistence_status == "FAILED":
        reasons.append("The recommendation could not be persisted.")

    if (state.get("errors") or []) and not reasons:
        reasons.append("One or more non-critical stages reported errors.")
    if (state.get("warnings") or []) and not reasons:
        reasons.append("One or more stages completed with warnings.")

    return reasons


def _success_message(state: dict) -> str:
    if state.get("run_optimization"):
        if not state.get("demand_prediction_meta"):
            return (
                "Pricing pipeline completed successfully using the supplied demand "
                "predictions; optimization, recommendation and SLM explanation were generated."
            )
        return (
            "Pricing pipeline completed successfully; demand prediction, optimization, "
            "recommendation and SLM explanation were generated."
        )
    if state.get("run_candidate_prices"):
        return "Pricing pipeline completed successfully through candidate price generation."
    return "Pricing pipeline completed successfully through feature engineering."
