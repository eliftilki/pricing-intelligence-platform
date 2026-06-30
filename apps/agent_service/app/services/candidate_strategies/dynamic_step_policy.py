import math

MIN_PRICE_STEP = 50
TARGET_MARKET_INTERVALS = 15


def choose_step(min_price: float, max_price: float) -> int:
    width = max(0.0, max_price - min_price)
    if width == 0:
        return MIN_PRICE_STEP

    raw_step = max(MIN_PRICE_STEP, width / TARGET_MARKET_INTERVALS)
    magnitude = 10 ** math.floor(math.log10(raw_step))

    for multiplier in (1, 2.5, 5, 10):
        candidate = multiplier * magnitude
        if candidate >= raw_step:
            return max(MIN_PRICE_STEP, int(candidate))

    raise RuntimeError("Unable to determine a dynamic price step.")


def generate_extended_market_range(
    min_price: float,
    max_price: float,
    step: int,
    padding_steps: int = 5,
) -> list[float]:
    """Create one positive price grid covering the market plus equal padding."""
    step = max(step, MIN_PRICE_STEP)
    padding_steps = max(0, padding_steps)

    aligned_min = math.floor(min_price / step) * step
    aligned_max = math.ceil(max_price / step) * step
    start = max(step, aligned_min - (padding_steps * step))
    end = aligned_max + (padding_steps * step)

    return [float(price) for price in range(int(start), int(end) + step, step)]
