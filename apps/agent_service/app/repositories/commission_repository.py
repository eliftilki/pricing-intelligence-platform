from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class CommissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_company_override(
        self,
        company_id: UUID,
        marketplace: str,
        category_id: UUID | None,
        effective_date: date | None = None,
    ) -> Decimal | None:
        # category_id NULL olabilir (urunun category_id'si atanmamis) - bu
        # durumda "category_id IS NULL" kuralina (genel/default kural) duser.
        # "category_id = :category_id" NULL ile hicbir zaman eslesmez, bu
        # yuzden ayri bir IS NULL kolu gerekiyor.
        query = text(
            """
            SELECT commission_rate
            FROM public.company_marketplace_commission_overrides
            WHERE company_id = :company_id
              AND marketplace = :marketplace
              AND (
                    (:category_id IS NULL AND category_id IS NULL)
                    OR category_id = :category_id
                  )
              AND is_active = true
              AND (valid_from IS NULL OR valid_from <= :effective_date)
              AND (valid_to IS NULL OR valid_to >= :effective_date)
            ORDER BY valid_from DESC NULLS LAST, created_at DESC
            LIMIT 1
            """
        )

        row = self.db.execute(
            query,
            {
                "company_id": str(company_id),
                "marketplace": marketplace.upper(),
                "category_id": str(category_id) if category_id else None,
                "effective_date": effective_date or date.today(),
            },
        ).mappings().first()

        return Decimal(str(row["commission_rate"])) if row else None

    def get_default_rule(
        self,
        marketplace: str,
        category_id: UUID | None,
        effective_date: date | None = None,
    ) -> Decimal | None:
        query = text(
            """
            SELECT commission_rate
            FROM public.marketplace_commission_rules
            WHERE marketplace = :marketplace
              AND (
                    (:category_id IS NULL AND category_id IS NULL)
                    OR category_id = :category_id
                  )
              AND is_active = true
              AND (valid_from IS NULL OR valid_from <= :effective_date)
              AND (valid_to IS NULL OR valid_to >= :effective_date)
            ORDER BY valid_from DESC NULLS LAST, created_at DESC
            LIMIT 1
            """
        )

        row = self.db.execute(
            query,
            {
                "marketplace": marketplace.upper(),
                "category_id": str(category_id) if category_id else None,
                "effective_date": effective_date or date.today(),
            },
        ).mappings().first()

        return Decimal(str(row["commission_rate"])) if row else None
