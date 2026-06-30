import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.nodes.feature_engineering_node import _get_feature_seller_products


class FakeFeatureEngineeringRepository:
    def __init__(self, seller_products):
        self.seller_products = seller_products

    def get_seller_product(self, *, product_id, seller_product_id):
        seller_product = self.seller_products[seller_product_id]
        if seller_product.product_id != product_id:
            raise ValueError("Seller product does not belong to product.")
        return seller_product


class FeatureEngineeringNodeTests(unittest.TestCase):
    def test_resolves_all_unique_marketplace_seller_products(self):
        product_id = uuid4()
        trendyol_id = uuid4()
        amazon_id = uuid4()
        seller_products = {
            trendyol_id: SimpleNamespace(id=trendyol_id, product_id=product_id),
            amazon_id: SimpleNamespace(id=amazon_id, product_id=product_id),
        }

        result = _get_feature_seller_products(
            state={
                "seller_product_ids": {
                    "TRENDYOL": trendyol_id,
                    "AMAZON": amazon_id,
                    "AMAZON_DUPLICATE": amazon_id,
                }
            },
            repository=FakeFeatureEngineeringRepository(seller_products),
            product_id=product_id,
            fallback=seller_products[trendyol_id],
        )

        self.assertEqual(
            [item.id for item in result],
            [trendyol_id, amazon_id],
        )

    def test_falls_back_to_primary_for_legacy_single_marketplace_request(self):
        fallback = SimpleNamespace(id=uuid4())

        result = _get_feature_seller_products(
            state={},
            repository=FakeFeatureEngineeringRepository({}),
            product_id=uuid4(),
            fallback=fallback,
        )

        self.assertEqual(result, [fallback])


if __name__ == "__main__":
    unittest.main()
