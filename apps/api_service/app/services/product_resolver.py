import re
import unicodedata

from app.schemas.product_schema import ProductCreate


def normalize_token(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = (
        value.strip()
        .lower()
        .replace("\u0131", "i")
        .replace("\u011f", "g")
        .replace("\u00fc", "u")
        .replace("\u015f", "s")
        .replace("\u00f6", "o")
        .replace("\u00e7", "c")
    )
    normalized = unicodedata.normalize("NFKD", cleaned)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    token = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")

    return token or None


def build_normalized_key(payload: ProductCreate) -> str | None:
    required_tokens = [
        normalize_token(payload.brand),
        normalize_token(payload.model),
        normalize_token(payload.category),
        normalize_token(payload.color),
        normalize_token(payload.connection_type),
    ]

    if any(token is None for token in required_tokens):
        return None

    return "|".join(required_tokens)
