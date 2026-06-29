from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.repositories.commission_repository import CommissionRepository


class CommissionRateNotFoundError(ValueError):
    code = "COMMISSION_RATE_NOT_FOUND"

    def __init__(self, marketplace: str, category_id: UUID | None):
        self.marketplace = marketplace
        self.category_id = category_id
        super().__init__(
            f"Commission rate not found for marketplace={marketplace}, category_id={category_id}."
        )


class CommissionService:
    def __init__(self, repository: "CommissionRepository"):
        self.repository = repository

    def get_commission_rate(
        self,
        company_id: UUID,
        marketplace: str,
        category_id: UUID | None,
        effective_date: date | None = None,
    ) -> Decimal:
        # category_id None olabilir (urune kategori atanmamis) - bu durumda
        # category_id IS NULL icin tanimli genel/default kurala (varsa)
        # dusulur, repository katmaninda ayrica ele alinir. Erken raise
        # ETMIYORUZ; aksi halde DB'deki genel kurallar hic denenmeden
        # COMMISSION_RATE_NOT_FOUND donerdi.
        normalized_marketplace = marketplace.upper()

        override_rate = self.repository.get_company_override(
            company_id=company_id,
            marketplace=normalized_marketplace,
            category_id=category_id,
            effective_date=effective_date,
        )

        if override_rate is not None:
            return override_rate

        default_rate = self.repository.get_default_rule(
            marketplace=normalized_marketplace,
            category_id=category_id,
            effective_date=effective_date,
        )

        if default_rate is not None:
            return default_rate

        raise CommissionRateNotFoundError(
            marketplace=normalized_marketplace,
            category_id=category_id,
        )
