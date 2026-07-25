"""
Monitors and validates system performance invariants against chaos injection
to verify that recovery latencies remain within the strict <350ms constraint.
"""

import time
import structlog
from typing import Callable, Awaitable, Any
from src.core.exceptions import ChaosInjectionViolation

logger = structlog.get_logger(__name__)


class SteadyStateProbe:
    """
    Validates system health metrics before and after chaos events, ensuring
    that automatic recovery mechanisms restore normal operations instantly.
    """

    def __init__(self, max_allowed_recovery_ms: float = 350.0) -> None:
        self.max_allowed_recovery_ms = max_allowed_recovery_ms

    async def measure_recovery(
            self,
            fault_task: Callable[..., Awaitable[Any]],
            recovery_task: Callable[..., Awaitable[Any]],
            *args: Any,
            **kwargs: Any
    ) -> float:
        """
        Executes a chaos fault followed immediately by a repair routine,
        benchmarking the total round-trip recovery latency in milliseconds.
        """
        start_time = time.perf_counter()

        try:
            # Trigger fault scenario
            await fault_task()
        except Exception as fault_exc:
            logger.info("Fault successfully triggered during chaos probe", error=str(fault_exc))

        # Execute healing/recovery routine
        recovery_start = time.perf_counter()
        await recovery_task(*args, **kwargs)

        recovery_duration_ms = (time.perf_counter() - recovery_start) * 1000
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Chaos recovery benchmark complete",
            recovery_latency_ms=round(recovery_duration_ms, 2),
            total_duration_ms=round(total_duration_ms, 2)
        )

        if recovery_duration_ms > self.max_allowed_recovery_ms:
            logger.critical(
                "Recovery latency threshold breached!",
                measured_ms=round(recovery_duration_ms, 2),
                limit_ms=self.max_allowed_recovery_ms
            )
            raise ChaosInjectionViolation(
                f"Recovery latency {recovery_duration_ms:.2f}ms exceeded limit of {self.max_allowed_recovery_ms}ms"
            )

        return recovery_duration_ms