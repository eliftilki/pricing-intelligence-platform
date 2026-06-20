from typing import TypedDict
from uuid import UUID


class CompetitorGraphState(TypedDict, total=False):
    product_id: UUID
    lookback_hours: int
    status: str
    analyzed_count: int
    inserted_count: int
    message: str
    results: list[dict]
