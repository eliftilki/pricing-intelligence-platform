import unittest

from app.nodes.pipeline_finalizer_node import pipeline_finalizer_node


def build_successful_full_state() -> dict:
    return {
        "status": "SUCCESS",
        "run_candidate_prices": True,
        "run_optimization": True,
        "ingestion_result": {"status": "COMPLETED"},
        "analyzed_count": 3,
        "results": [],
        "market_event_features": {"status": "SUCCESS"},
        "pricing_features": {"marketplace": "TRENDYOL"},
        "candidate_price_result": {"candidate_prices": [100.0]},
        "demand_prediction_meta": {"model_name": "test-model"},
        "optimization_result": {"marketplace_results": []},
        "recommendation": {"recommended_price": 100.0},
        "slm_explanation": {"explanation": "Test explanation"},
        "recommendation_persistence": {"status": "PERSISTED"},
        "warnings": [],
        "errors": [],
    }


class PipelineFinalizerNodeTests(unittest.TestCase):
    def test_full_pipeline_success_replaces_stage_message(self):
        state = build_successful_full_state()
        state["message"] = "Competitor intelligence completed."

        result = pipeline_finalizer_node(state)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("Pricing pipeline completed successfully", result["message"])
        self.assertEqual(result["pipeline_summary"]["outcome"], "SUCCESS")
        self.assertIn("slm_explanation", result["pipeline_summary"]["completed_stages"])

    def test_slm_failure_is_partial_success(self):
        state = build_successful_full_state()
        state["slm_explanation"] = None
        state["errors"] = ["SLM_EXPLANATION_FAILED: timeout"]

        result = pipeline_finalizer_node(state)

        self.assertEqual(result["status"], "PARTIAL_SUCCESS")
        self.assertIn("SLM explanation failed", result["message"])
        self.assertEqual(result["pipeline_summary"]["error_count"], 1)

    def test_persistence_failure_is_partial_success(self):
        state = build_successful_full_state()
        state["recommendation_persistence"] = {"status": "FAILED"}
        state["warnings"] = ["RECOMMENDATION_PERSISTENCE_FAILED"]

        result = pipeline_finalizer_node(state)

        self.assertEqual(result["status"], "PARTIAL_SUCCESS")
        self.assertIn("could not be persisted", result["message"])

    def test_critical_failure_reports_failed_stage(self):
        state = {
            "status": "FAILED",
            "failed_stage": "demand_prediction",
            "message": "ML service is unavailable.",
            "warnings": [],
            "errors": [],
        }

        result = pipeline_finalizer_node(state)

        self.assertEqual(result["status"], "FAILED")
        self.assertIn("demand prediction", result["message"])
        self.assertEqual(
            result["pipeline_summary"]["failed_stage"],
            "demand_prediction",
        )

    def test_candidate_only_run_has_pipeline_level_message(self):
        state = {
            "status": "SUCCESS",
            "run_candidate_prices": True,
            "run_optimization": False,
            "ingestion_result": {"status": "COMPLETED"},
            "candidate_price_result": {"candidate_prices": [100.0]},
            "warnings": [],
            "errors": [],
        }

        result = pipeline_finalizer_node(state)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("candidate price generation", result["message"])


if __name__ == "__main__":
    unittest.main()
