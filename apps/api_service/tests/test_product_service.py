import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.services.product_service import ProductService


class FakeProductRepository:
    def __init__(self, seller_product=None, total_sales=0):
        self.seller_product = seller_product
        self.total_sales = total_sales

    def get_seller_product(self, _seller_product_id):
        return self.seller_product

    def get_sales_total(self, _seller_product_id, *, period_days):
        period_end = datetime(2026, 6, 30, tzinfo=timezone.utc)
        return (
            self.total_sales,
            period_end - timedelta(days=period_days),
            period_end,
        )


class ProductServiceSalesAverageTests(unittest.TestCase):
    def build_service(self, repository):
        service = ProductService.__new__(ProductService)
        service.repo = repository
        return service

    def test_returns_daily_average_for_last_seven_days(self):
        seller_product_id = uuid4()
        service = self.build_service(
            FakeProductRepository(
                seller_product=SimpleNamespace(id=seller_product_id),
                total_sales=14,
            )
        )

        result = service.get_sales_7d_average(seller_product_id)

        self.assertEqual(result["period_days"], 7)
        self.assertEqual(result["total_sales"], 14)
        self.assertEqual(result["sales_7d_avg"], 2.0)

    def test_missing_seller_product_returns_not_found(self):
        service = self.build_service(FakeProductRepository())

        with self.assertRaises(HTTPException) as context:
            service.get_sales_7d_average(uuid4())

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
