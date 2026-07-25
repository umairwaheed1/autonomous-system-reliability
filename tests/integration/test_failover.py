"""
End-to-end integration tests validating fault tolerance, automated recovery latencies,
and chaos engineering resilience bounds (<350ms recovery target).
"""

import pytest
import asyncio
from src.core.exceptions import CircuitBreakerOpenError, RepairVerificationFailedError


@pytest.mark.asyncio
async def test_pipeline_successful_execution(reliability_pipeline):
    """Verifies standard pipeline task execution under healthy conditions."""
    async def mock_service_call():
        await asyncio.sleep(0.05)
        return "SUCCESS"

    result = await reliability_pipeline.run("test_success", mock_service_call)
    assert result == "SUCCESS"


@pytest.mark.asyncio
async def test_chaos_latency_and_recovery_benchmark(reliability_pipeline, chaos_harness):
    """
    Simulates severe edge network latency, tests supervisor circuit-breaking,
    and benchmarks recovery latency against the <350ms threshold.
    """
    injector, probe = chaos_harness

    async def faulty_operation():
        await injector.inject_latency(delay_sec=0.40)  # Exceeds default timeout
        return "SHOULD_FAIL"

    async def healing_operation():
        # Simulated fallback/repair routine resolving the drift
        await asyncio.sleep(0.05)
        return "HEALED_STATE"

    # Measure total fault and recovery round-trip duration via steady-state probe
    recovery_ms = await probe.measure_recovery(
        fault_task=faulty_operation,
        recovery_task=healing_operation
    )

    assert recovery_ms < 350.0, f"Recovery latency {recovery_ms}ms violated <350ms constraint!"


@pytest.mark.asyncio
async def test_apr_sandbox_verification_loop(apr_toolkit):
    """Validates that candidate runtime patches pass or fail sandbox checks correctly."""
    analyzer, patcher, verifier = apr_toolkit

    # Register a successful fallback patch
    async def healthy_patch():
        await asyncio.sleep(0.02)
        return True

    patcher.register_patch("ARITHMETIC_OVERFLOW_DRIFT", healthy_patch)

    # Verify sandbox evaluation passes
    is_verified = await verifier.verify(patcher.apply_patch, "ARITHMETIC_OVERFLOW_DRIFT")
    assert is_verified is True

    # Register a failing/slow patch that violates sandbox limits
    async def unstable_patch():
        await asyncio.sleep(0.20)  # Exceeds sandbox 150ms limit
        return False

    patcher.register_patch("RESOURCE_EXHAUSTION_LEAK", unstable_patch)

    with pytest.raises(RepairVerificationFailedError):
        await verifier.verify(patcher.apply_patch, "RESOURCE_EXHAUSTION_LEAK")