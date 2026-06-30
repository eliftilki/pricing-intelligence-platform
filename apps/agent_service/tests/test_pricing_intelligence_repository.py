import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories.pricing_intelligence_repository import (
    PricingIntelligenceRepository,
)


class PricingIntelligenceRepositoryTests(unittest.TestCase):
    def test_partial_success_uses_shared_success_lifecycle_status(self):
        db = MagicMock()
        repository = PricingIntelligenceRepository(db)
        output_payload = {"status": "PARTIAL_SUCCESS", "warnings": ["SLM unavailable"]}

        run = repository.save_run(
            product_id=uuid4(),
            seller_product_id=None,
            company_id=None,
            input_payload={"lookback_hours": 12},
            output_payload=output_payload,
            status="PARTIAL_SUCCESS",
        )

        self.assertEqual(run.status, "SUCCESS")
        self.assertEqual(run.output_payload["status"], "PARTIAL_SUCCESS")
        db.add.assert_called_once_with(run)
        db.commit.assert_called_once_with()

    def test_failed_status_is_preserved(self):
        db = MagicMock()
        repository = PricingIntelligenceRepository(db)

        run = repository.save_run(
            product_id=uuid4(),
            seller_product_id=None,
            company_id=None,
            input_payload={},
            output_payload={"status": "FAILED"},
            status="FAILED",
        )

        self.assertEqual(run.status, "FAILED")


if __name__ == "__main__":
    unittest.main()
