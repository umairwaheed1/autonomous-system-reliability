"""
Resilient execution pipeline orchestrating task flows, telemetry recording,
and automatic fallback/repair invocation under high-concurrency stress.
"""

import asyncio
import time
import structlog
from typing import Callable, Awaitable, Any, Optional, Dict

from src.core.supervisor import SystemSupervisor
from src.core.exceptions import SystemReliabilityError, CircuitBreakerOpenError

logger = structlog.get_logger(__name__)


class ExecutionPipeline:
    """
    Manages the end-to-end execution lifecycle of microservice workloads,
    binding supervisor state checks with real-time performance tracking.
    """

    def __init__(
        self,
        supervisor: Optional[SystemSupervisor] = None,
        default_timeout: float = 0.35
    ):
        self.supervisor = supervisor or SystemSupervisor(recovery_timeout_sec=default_timeout)
        self.default_timeout = default_timeout
        self._metrics_collector: Optional[Callable[[str, float, bool], Awaitable[None]]] = None

    def register_telemetry_hook(
        self,
        hook: Callable[[str, float, bool], Awaitable[None]]
    ) -> None:
        """Registers an asynchronous callback to stream execution metrics directly to OpenTelemetry."""
        self._metrics_collector = hook

    async def run(
        self,
        operation_name: str,
        task: Callable[..., Awaitable[Any]],
        fallback_handler: Optional[Callable[..., Awaitable[Any]]] = None,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Executes a target task through the supervisor wrapper, measuring recovery
        latencies and seamlessly executing fallbacks or triggering APR paths on failure.
        """
        success = True
        start_time = time.perf_counter()

        try:
            # Enforce strict execution boundary using asyncio.wait_for to bind latency limits
            result = await asyncio.wait_for(
                self.supervisor.execute(task, *args, **kwargs),
                timeout=self.default_timeout
            )
            return result

        except (Exception, asyncio.TimeoutError) as exc:
            success = False
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.warning(
                "Pipeline execution intercepted by fault handler",
                operation=operation_name,
                error=str(exc),
                duration_ms=round(duration_ms, 2)
            )

            # Stream failure and latency telemetry
            if self._metrics_collector:
                try:
                    await self._metrics_collector(operation_name, duration_ms, success)
                except Exception as telemetry_err:
                    logger.error("Failed to emit telemetry metric", error=str(telemetry_err))

            # Trigger fallback handler if supplied, otherwise propagate the exception for APR ingestion
            if fallback_handler is not None:
                logger.info("Executing registered fallback handler", operation=operation_name)
                try:
                    return await fallback_handler(*args, **kwargs)
                except Exception as fallback_exc:
                    logger.critical(
                        "Fallback handler failed catastrophically",
                        operation=operation_name,
                        error=str(fallback_exc)
                    )
                    raise fallback_exc

            raise

        finally:
            if success:
                duration_ms = (time.perf_counter() - start_time) * 1000
                if self._metrics_collector:
                    try:
                        await self._metrics_collector(operation_name, duration_ms, success)
                    except Exception as telemetry_err:
                        logger.error("Failed to emit success telemetry metric", error=str(telemetry_err))