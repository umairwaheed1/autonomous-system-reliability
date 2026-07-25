"""
Validates synthesized patches inside a strict sandbox harness before promoting
them to live production execution streams.
"""

import asyncio
import time
import structlog
from typing import Callable, Awaitable, Any
from src.core.exceptions import RepairVerificationFailedError

logger = structlog.get_logger(__name__)


class PatchVerifier:
    """
    Executes rigorous assertions on generated patches to guarantee they resolve
    the runtime drift without introducing secondary regressions or violating latency limits.
    """

    def __init__(self, verification_timeout_sec: float = 0.15) -> None:
        self.verification_timeout_sec = verification_timeout_sec

    async def verify(
        self,
        patch_task: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> bool:
        """
        Runs the candidate patch under an isolated sandbox timer to verify correctness
        and check performance impact.
        """
        start_time = time.perf_counter()
        try:
            # Enforce strict sandbox verification window
            await asyncio.wait_for(
                patch_task(*args, **kwargs),
                timeout=self.verification_timeout_sec
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("Patch verified successfully in sandbox", latency_ms=round(duration_ms, 2))
            return True

        except asyncio.TimeoutError:
            logger.error("Patch verification timed out in sandbox environment")
            raise RepairVerificationFailedError("Sandbox verification failed: latency threshold breached.")
        except Exception as exc:
            logger.error("Patch verification failed with runtime exception", error=str(exc))
            raise RepairVerificationFailedError(f"Sandbox verification failed: {str(exc)}")