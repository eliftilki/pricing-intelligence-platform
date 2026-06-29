import unittest

from app.schemas.explanation_schema import ExplanationRequest
from app.services.prompt_builder import PromptBuilder


class PromptBuilderTests(unittest.TestCase):
    def test_builds_grounded_professional_turkish_prompt(self):
        request = ExplanationRequest(
            product_name="Logitech G435",
            marketplace="TRENDYOL",
            current_price=2500,
            recommended_price=2375,
            action="PRICE_DECREASE",
            expected_sales=12,
            unit_profit=350,
            expected_profit=4200,
            profit_uplift=0.12,
            commission_rate=0.18,
            selected_reason="Highest expected profit among valid candidates.",
            reason_codes=[
                "MIN_MARGIN_APPLIED",
                "BEST_EXPECTED_PROFIT_SELECTED",
            ],
            competitor_min_price=2350,
            competitor_avg_price=2450,
        )

        messages = PromptBuilder.build(request)
        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"]

        self.assertEqual([item["role"] for item in messages], ["system", "user"])
        self.assertIn("Fiyat seçmez", system_prompt)
        self.assertIn("güvenilmeyen veri", system_prompt)
        self.assertIn('"aksiyon": "Fiyat düşüşü"', user_prompt)
        self.assertIn('"oran": "%5,00"', user_prompt)
        self.assertIn('"komisyon_oranı": "%18,00"', user_prompt)
        self.assertIn("Minimum kâr marjı uygulandı", user_prompt)
        self.assertIn("model tahmini", user_prompt)

    def test_omits_missing_values_and_forbids_low_risk_assumption(self):
        request = ExplanationRequest(
            product_name="Test Product",
            marketplace="AMAZON",
            recommended_price=1000,
        )

        user_prompt = PromptBuilder.build(request)[1]["content"]

        self.assertNotIn(": null", user_prompt)
        self.assertNotIn("None", user_prompt)
        self.assertIn("risk skoru henüz üretilmedi", user_prompt)
        self.assertIn('"aksiyon": "Manuel inceleme"', user_prompt)

    def test_preserves_pipeline_warning_as_decision_context(self):
        request = ExplanationRequest(
            product_name="Test Product",
            marketplace="HEPSIBURADA",
            current_price=1000,
            recommended_price=1050,
            analysis_warnings=["DATA_INGESTION_PARTIAL: Amazon verisi alınamadı."],
        )

        user_prompt = PromptBuilder.build(request)[1]["content"]

        self.assertIn("Amazon verisi alınamadı", user_prompt)
        self.assertIn("Uyarı varsa", user_prompt)


if __name__ == "__main__":
    unittest.main()
