from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class CompetitorIntelligenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_listings_by_session(self, session_id: UUID) -> List[Dict[str, Any]]:
        sql = text("""
            SELECT
                cl.id,
                cl.scrape_id,
                cl.marketplace,
                cl.rank,
                cl.seller_name,
                cl.seller_score,
                cl.seller_review_count,
                cl.seller_city,
                cl.is_authorized,
                cl.price,
                cl.original_price,
                cl.discount_rate,
                cl.currency,
                cl.stock,
                cl.is_in_stock,
                cl.free_shipping,
                cl.fast_shipping,
                cl.shipment_days,
                cl.scraped_at
            FROM competitor_listings cl
            JOIN marketplace_scrapes ms ON cl.scrape_id = ms.id
            WHERE ms.session_id = :session_id
            ORDER BY cl.marketplace, cl.rank NULLS LAST
        """)
        rows = self.db.execute(sql, {"session_id": str(session_id)}).fetchall()
        return [
            {
                "id": str(row.id),
                "scrape_id": str(row.scrape_id),
                "marketplace": row.marketplace,
                "rank": row.rank,
                "seller_name": row.seller_name,
                "seller_score": float(row.seller_score) if row.seller_score is not None else None,
                "seller_review_count": row.seller_review_count,
                "seller_city": row.seller_city,
                "is_authorized": bool(row.is_authorized),
                "price": float(row.price) if row.price is not None else None,
                "original_price": float(row.original_price) if row.original_price is not None else None,
                "discount_rate": float(row.discount_rate) if row.discount_rate is not None else None,
                "currency": row.currency or "TRY",
                "stock": row.stock,
                "is_in_stock": bool(row.is_in_stock),
                "free_shipping": bool(row.free_shipping),
                "fast_shipping": bool(row.fast_shipping),
                "shipment_days": row.shipment_days,
                "scraped_at": row.scraped_at.isoformat() if row.scraped_at else None,
            }
            for row in rows
        ]
