CURRENT_PRICE_MARKET_DISTANCE_THRESHOLD = 0.30


def normalize_prices_to_step(
    prices: list[float],
    step: int,
) -> list[float]:
    if step <= 0:
        return sorted(set(round(price, 2) for price in prices if price > 0))

    normalized = [
        float(round(price / step) * step)
        for price in prices
        if price > 0
    ]
    return sorted(set(normalized))


def is_current_price_near_market(
    current_price: float,
    market_reference_price: float,
) -> bool:
    if current_price <= 0 or market_reference_price <= 0:
        return False

    relative_distance = (
        abs(current_price - market_reference_price)
        / market_reference_price
    )
    return relative_distance < CURRENT_PRICE_MARKET_DISTANCE_THRESHOLD


def current_price_candidates(
    current_price: float,
    market_reference_price: float,
    step: int,
) -> list[float]:
    if not is_current_price_near_market(
        current_price=current_price,
        market_reference_price=market_reference_price,
    ):
        return []

    return [
        current_price,
        current_price - step,
        current_price + step,
    ]


def current_price_constraint(
    current_price: float,
    market_reference_price: float,
) -> str:
    if is_current_price_near_market(
        current_price=current_price,
        market_reference_price=market_reference_price,
    ):
        return "CURRENT_PRICE_NEAR_MARKET_INCLUDED"

    return "CURRENT_PRICE_OUTLIER_EXCLUDED"
