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

    def test_seller_product_marketplaces_are_normalized_and_primary_is_selected(self):
        trendyol_id = uuid4()
        amazon_id = uuid4()

        request = PricingIntelligenceRunRequest(
            product_id=uuid4(),
            ingestion_marketplaces=["amazon", "trendyol"],
            seller_product_ids={
                "trendyol": trendyol_id,
                " AMAZON ": amazon_id,
            },
        )

        self.assertEqual(
            request.seller_product_ids,
            {"TRENDYOL": trendyol_id, "AMAZON": amazon_id},
        )
        self.assertEqual(request.seller_product_id, amazon_id)

    def test_unsupported_seller_product_marketplace_is_rejected(self):
        with self.assertRaises(ValidationError):
            PricingIntelligenceRunRequest(
                product_id=uuid4(),
                seller_product_ids={"UNKNOWN": uuid4()},
            )


if __name__ == "__main__":
    unittest.main()
