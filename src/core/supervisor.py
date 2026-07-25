"""
Principal-grade process supervisor implementing asynchronous state tracking,
steady-state probing, and rapid self-healing dispatch.
"""

import asyncio
import time
import structlog
from typing import Callable, Awaitable, Any, Optional
from src.core.exceptions import SystemReliabilityError, CircuitBreakerOpenError

logger = structlog.get_logger(__name__)

class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class SystemSupervisor:
    """
    Manages execution health, monitors recovery latencies, and orchestrates
    circuit-breaking behaviors under chaotic edge workloads.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_sec: float = 0.35  # Enforcing the <350ms constraint
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.perf_counter()
        self._lock = asyncio.Lock()

    async def execute(
        self,
        task: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Executes a pipeline task under strict supervisor watch, short-circuiting
        or routing to self-healing handlers when degradation occurs.
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.perf_counter() - self.last_state_change > self.recovery_timeout_sec:
                    logger.info("Circuit breaker entering HALF_OPEN state for probing.")
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(
                        "Circuit breaker is OPEN. Fast-failing execution stream."
                    )

        start_time = time.perf_counter()
        try:
            result = await task(*args, **kwargs)
            await self._handle_success()
            return result
        except Exception as exc:
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Pipeline execution anomaly caught",
                error=str(exc),
                latency_ms=round(duration, 2)
            )
            await self._handle_failure(exc)
            raise

    async def _handle_success(self) -> None:
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Probe successful. Resetting circuit breaker to CLOSED.")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = time.perf_counter()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

    async def _handle_failure(self, exc: Exception) -> None:
        async with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.last_state_change = time.perf_counter()
                logger.critical(
                    "Circuit breaker tripped to OPEN",
                    failures=self.failure_count,
                    threshold=self.failure_threshold
                )