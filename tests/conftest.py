"""
Pytest configuration providing shared asynchronous event loops and test fixtures
for the self-healing architecture test suite.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from src.core.supervisor import SystemSupervisor
from src.core.pipeline import ExecutionPipeline
from src.apr.analyzer import DriftAnalyzer
from src.apr.patcher import DynamicPatcher
from src.apr.verifier import PatchVerifier
from src.chaos.injector import ChaosInjector
from src.chaos.probes import SteadyStateProbe


@pytest.fixture(scope="session")
def event_loop():
    """Forces session-scoped event loop for async test execution."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def reliability_pipeline() -> ExecutionPipeline:
    """Provides a fresh execution pipeline wrapped with a high-sensitivity supervisor."""
    supervisor = SystemSupervisor(failure_threshold=2, recovery_timeout_sec=0.35)
    return ExecutionPipeline(supervisor=supervisor, default_timeout=0.35)


@pytest.fixture
def apr_toolkit() -> tuple[DriftAnalyzer, DynamicPatcher, PatchVerifier]:
    """Provides the complete Automated Program Repair subsystem toolkit."""
    return DriftAnalyzer(), DynamicPatcher(), PatchVerifier(verification_timeout_sec=0.15)


@pytest.fixture
def chaos_harness() -> tuple[ChaosInjector, SteadyStateProbe]:
    """Provides chaos injection suites and steady-state recovery probes."""
    return ChaosInjector(), SteadyStateProbe(max_allowed_recovery_ms=350.0)