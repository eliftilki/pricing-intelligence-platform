import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.pricing_intelligence_schema import PricingIntelligenceRunRequest


class PricingIntelligenceSchemaTests(unittest.TestCase):
    def test_ingestion_marketplaces_are_normalized_and_deduplicated(self):
        request = PricingIntelligenceRunRequest(
            product_id=uuid4(),
            ingestion_marketplaces=["trendyol", " TRENDYOL ", "amazon"],
        )

        self.assertEqual(
            request.ingestion_marketplaces,
            ["TRENDYOL", "AMAZON"],
        )

    def test_unsupported_ingestion_marketplace_is_rejected(self):
        with self.assertRaises(ValidationError):
            PricingIntelligenceRunRequest(
                product_id=uuid4(),
                ingestion_marketplaces=["UNKNOWN"],
            )

    def test_ingestion_query_requires_company_id(self):
        with self.assertRaises(ValidationError):
            PricingIntelligenceRunRequest(
                product_id=uuid4(),
                ingestion_query="Logitech G305",
            )


if __name__ == "__main__":
    unittest.main()
