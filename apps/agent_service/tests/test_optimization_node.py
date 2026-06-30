import unittest
from decimal import Decimal
from uuid import uuid4

from app.nodes.optimization_node import _build_marketplaces
from app.schemas.optimization_schema import Marketplace


class FakeOptimizationRepository:
    def __init__(self, contexts):
        self.contexts = contexts

    def get_seller_product_context(self, seller_product_id):
        return self.contexts[seller_product_id]

    def build_marketplace_input_from_context(self, context, commission_rate):
        from app.schemas.optimization_schema import MarketplaceOptimizationInput

        return MarketplaceOptimizationInput(
            marketplace=context["marketplace"],
            seller_product_id=context["seller_product_id"],
            cost_price=context["cost_price"],
            current_price=context["current_price"],
            commission_rate=commission_rate,
            market_average_price=context.get("market_average_price"),
        )


class FakeCommissionService:
    def get_commission_rate(self, *, marketplace, **_):
        return {
            "TRENDYOL": Decimal("0.10"),
            "AMAZON": Decimal("0.20"),
        }[str(marketplace).upper()]


class OptimizationNodeTests(unittest.TestCase):
    def test_builds_marketplace_contexts_from_seller_product_mapping(self):
        trendyol_id = uuid4()
        amazon_id = uuid4()
        contexts = {
            trendyol_id: {
                "seller_product_id": trendyol_id,
                "company_id": uuid4(),
                "category_id": uuid4(),
                "marketplace": "TRENDYOL",
                "cost_price": Decimal("60"),
                "current_price": Decimal("100"),
            },
            amazon_id: {
                "seller_product_id": amazon_id,
                "company_id": uuid4(),
                "category_id": uuid4(),
                "marketplace": "AMAZON",
                "cost_price": Decimal("75"),
                "current_price": Decimal("110"),
            },
        }

        results = _build_marketplaces(
            state={
                "seller_product_ids": {
                    "TRENDYOL": trendyol_id,
                    "AMAZON": amazon_id,
                },
                "candidate_price_result": {"avg_competitor_price": "105"},
            },
            repository=FakeOptimizationRepository(contexts),
            commission_service=FakeCommissionService(),
            seller_context=contexts[trendyol_id],
        )

        self.assertEqual([item.marketplace for item in results], [Marketplace.TRENDYOL, Marketplace.AMAZON])
        self.assertEqual([item.seller_product_id for item in results], [trendyol_id, amazon_id])
        self.assertEqual([item.commission_rate for item in results], [Decimal("0.10"), Decimal("0.20")])
        self.assertTrue(all(item.market_average_price == Decimal("105") for item in results))


if __name__ == "__main__":
    unittest.main()
