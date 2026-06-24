from typing import TypedDict
from uuid import UUID


class CompetitorGraphState(TypedDict, total=False):
    product_id: UUID
    seller_product_id: UUID | None

    lookback_hours: int

    status: str
    analyzed_count: int
    inserted_count: int
    message: str
    results: list[dict]

    price_step: int
    base_price_step: int
    dense_price_step: int

    candidate_price_result: dict
    candidate_prices: list[float]
    selected_candidate_strategy: str

    pricing_features: dict
    market_event_features: dict