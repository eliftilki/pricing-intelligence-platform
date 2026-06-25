import unittest
from decimal import Decimal
from uuid import uuid4

from app.services.commission_service import (
    CommissionRateNotFoundError,
    CommissionService,
)


class FakeCommissionRepository:
    def __init__(self, override_rate=None, default_rate=None):
        self.override_rate = override_rate
        self.default_rate = default_rate
        self.calls = []

    def get_company_override(self, **kwargs):
        self.calls.append(("override", kwargs))
        return self.override_rate

    def get_default_rule(self, **kwargs):
        self.calls.append(("default", kwargs))
        return self.default_rate


class CommissionServiceTests(unittest.TestCase):
    def test_company_override_takes_priority(self):
        category_id = uuid4()
        repository = FakeCommissionRepository(
            override_rate=Decimal("0.14"),
            default_rate=Decimal("0.18"),
        )

        rate = CommissionService(repository).get_commission_rate(
            company_id=uuid4(),
            marketplace="trendyol",
            category_id=category_id,
        )

        self.assertEqual(rate, Decimal("0.14"))
        self.assertEqual([call[0] for call in repository.calls], ["override"])
        self.assertEqual(repository.calls[0][1]["marketplace"], "TRENDYOL")
        self.assertEqual(repository.calls[0][1]["category_id"], category_id)

    def test_default_rule_is_used_when_override_missing(self):
        category_id = uuid4()
        repository = FakeCommissionRepository(default_rate=Decimal("0.18"))

        rate = CommissionService(repository).get_commission_rate(
            company_id=uuid4(),
            marketplace="TRENDYOL",
            category_id=category_id,
        )

        self.assertEqual(rate, Decimal("0.18"))
        self.assertEqual([call[0] for call in repository.calls], ["override", "default"])

    def test_raises_when_no_commission_rate_exists(self):
        repository = FakeCommissionRepository()

        with self.assertRaises(CommissionRateNotFoundError) as context:
            CommissionService(repository).get_commission_rate(
                company_id=uuid4(),
                marketplace="TRENDYOL",
                category_id=uuid4(),
            )

        self.assertEqual(context.exception.code, "COMMISSION_RATE_NOT_FOUND")

    def test_raises_when_category_is_missing(self):
        repository = FakeCommissionRepository(default_rate=Decimal("0.18"))

        with self.assertRaises(CommissionRateNotFoundError):
            CommissionService(repository).get_commission_rate(
                company_id=uuid4(),
                marketplace="TRENDYOL",
                category_id=None,
            )

        self.assertEqual(repository.calls, [])


if __name__ == "__main__":
    unittest.main()
