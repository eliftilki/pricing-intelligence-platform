import math


MIN_PRICE_STEP = 50


def choose_step(min_price: float, max_price: float) -> int:
    width = max(0.0, max_price - min_price)

    if width <= 500:
        return 50
    if width <= 1500:
        return 100
    if width <= 3000:
        return 250
    return 500


def choose_dense_step(start_price: float, end_price: float) -> int:
    width = max(0.0, end_price - start_price)

    if width <= 300:
        return 50
    if width <= 800:
        return 100
    return 250


def generate_aligned_range(
    min_price: float,
    max_price: float,
    step: int,
    *,
    include_ceiling: bool = False,
) -> list[float]:
    step = max(step, MIN_PRICE_STEP)
    start = math.floor(min_price / step) * step
    if include_ceiling:
        end = math.ceil(max_price / step) * step
    else:
        end = math.floor(max_price / step) * step

    if end < start:
        end = start

    return [
        float(price)
        for price in range(int(start), int(end) + step, step)
    ]
