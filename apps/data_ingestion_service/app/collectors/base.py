import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _run_in_new_loop(coro):
    """Coroutine'i yeni bir event loop'ta thread içinde çalıştırır.
    Playwright, uvicorn'un event loop'uyla çakışır; bu wrapper bunu önler."""
    return asyncio.run(coro)


class BaseMarketplaceCollector(ABC):
    """
    Standart çıktı şeması:
    {
        "source": str,           # "hepsiburada" | "trendyol" | "amazon"
        "url": str,
        "scraped_at": str,       # ISO 8601 UTC
        "product": {
            "name": str | None,
            "sku": str | None,
            "brand": str | None,
            "rating": float | None,      # ürün puanı
            "review_count": int | None
        },
        "sellers": [
            {
                "rank": int | None,           # buybox sırası
                "seller_name": str | None,
                "seller_score": float | None, # satıcı puanı
                "seller_review_count": int | None,
                "seller_city": str | None,
                "is_authorized": bool,
                "price": float | None,
                "original_price": float | None,
                "discount_rate": float | None,  # yüzde
                "currency": str,
                "stock": int | None,
                "is_in_stock": bool,
                "free_shipping": bool,
                "fast_shipping": bool,
                "shipment_days": int | None
            }
        ]
    }
    """

    @abstractmethod
    async def scrape_product_by_url(self, url: str) -> Dict[str, Any]:
        pass

    async def _scrape_with_retry(
        self,
        coro_func: Callable[..., Any],
        *args,
        max_retries: int = 3,
        **kwargs
    ) -> T:
        """
        Execute async function with exponential backoff retry.

        Args:
            coro_func: Async function to retry
            max_retries: Number of retry attempts (default 3)
            *args, **kwargs: Arguments to pass to coro_func

        Returns:
            Result from coro_func on success

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Playwright, mevcut bir event loop içinde çalışamaz (Windows/uvicorn uyumsuzluğu).
                # asyncio.to_thread yeni bir thread + asyncio.run() ile izole bir loop açar.
                return await asyncio.to_thread(_run_in_new_loop, coro_func(*args, **kwargs))
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{max_retries}, "
                        f"retrying in {wait_time}s: {args}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries} retries exhausted for {args[0] if args else 'unknown'}"
                    )
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Error on attempt {attempt + 1}/{max_retries}: {type(e).__name__}, "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} retries exhausted: {type(e).__name__}: {e}")

        raise last_exception
