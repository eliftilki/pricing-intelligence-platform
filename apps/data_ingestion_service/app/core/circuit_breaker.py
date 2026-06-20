import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MarketplaceCircuitBreaker:
    """
    Lightweight circuit breaker for marketplace availability.

    States:
    - CLOSED: Normal operation, requests processed
    - OPEN: Failing repeatedly, requests fail immediately
    - HALF_OPEN: Testing if service recovered, 1 request allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self, marketplace: str, failure_threshold: int = 5, reset_timeout: int = 60
    ):
        self.marketplace = marketplace
        self.state = self.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None

    def record_success(self) -> None:
        """Record successful request."""
        if self.state == self.HALF_OPEN:
            self.state = self.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit breaker {self.marketplace}: HALF_OPEN → CLOSED (recovered)")
        self.last_success_time = time.time()

    def record_failure(self) -> None:
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == self.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning(
                    f"Circuit breaker {self.marketplace}: CLOSED → OPEN "
                    f"({self.failure_count} consecutive failures)"
                )
        elif self.state == self.HALF_OPEN:
            self.state = self.OPEN
            logger.warning(
                f"Circuit breaker {self.marketplace}: HALF_OPEN → OPEN (recovery failed)"
            )

    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        if self.state == self.CLOSED:
            return True

        if self.state == self.OPEN:
            if self.last_failure_time and time.time() - self.last_failure_time > self.reset_timeout:
                self.state = self.HALF_OPEN
                logger.info(
                    f"Circuit breaker {self.marketplace}: OPEN → HALF_OPEN "
                    f"(recovery timeout elapsed, attempting recovery)"
                )
                return True
            return False

        if self.state == self.HALF_OPEN:
            return True

        return False

    def get_status(self) -> dict:
        """Get current circuit status."""
        return {
            "marketplace": self.marketplace,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
        }
