"""
Simulates edge node failures, malicious network jitter, resource exhaustion,
and concurrency deadlocks to test system resilience.
"""

import asyncio
import time
import random
import structlog
from typing import Callable, Awaitable, Any

logger = structlog.get_logger(__name__)


class ChaosInjector:
    """
    Orchestrates runtime chaos scenarios, injecting controlled faults into
    execution pipelines to benchmark fault-tolerance and self-healing performance.
    """

    @staticmethod
    async def inject_latency(delay_sec: float = 0.40) -> None:
        """Injects artificial network latency exceeding normal bounds to test timeouts."""
        logger.warning("CHAOS INJECTION: Simulating severe network latency", injected_delay_sec=delay_sec)
        await asyncio.sleep(delay_sec)

    @staticmethod
    async def inject_memory_leak(allocation_size_mb: int = 150) -> bytes:
        """Allocates memory blocks to simulate memory pressure and resource drift."""
        logger.warning("CHAOS INJECTION: Simulating memory leak/exhaustion", size_mb=allocation_size_mb)
        # Allocate dummy payload to stress memory subsystem
        return b"X" * (allocation_size_mb * 1024 * 1024)

    @staticmethod
    async def simulate_thread_lock(lock_duration_sec: float = 0.25) -> None:
        """Simulates a thread deadlock or CPU starvation bottleneck."""
        logger.warning("CHAOS INJECTION: Simulating thread execution stall", stall_sec=lock_duration_sec)
        await asyncio.sleep(lock_duration_sec)