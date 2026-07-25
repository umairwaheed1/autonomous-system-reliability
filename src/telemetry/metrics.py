"""
Configures OpenTelemetry meters, counters, and histograms to track
pipeline execution times, recovery latencies, and circuit breaker trips.
"""

import structlog
from typing import Optional
from opentelemetry import metrics
from opentelemetry.metrics import Meter, Counter, Histogram

logger = structlog.get_logger(__name__)


class TelemetryMetrics:
    """
    Manages custom OpenTelemetry metric instruments for real-time dashboarding
    and execution graph generation.
    """

    def __init__(self, service_name: str = "autonomous-system-reliability") -> None:
        self.meter: Meter = metrics.get_meter(service_name)

        # Initialize telemetry instruments
        self.execution_counter: Counter = self.meter.create_counter(
            name="pipeline_executions_total",
            description="Total count of pipeline executions categorized by status",
            unit="1"
        )
        self.recovery_latency_histogram: Histogram = self.meter.create_histogram(
            name="recovery_latency_milliseconds",
            description="Distribution of fault recovery and self-healing latencies",
            unit="ms"
        )
        self.circuit_breaker_counter: Counter = self.meter.create_counter(
            name="circuit_breaker_trips_total",
            description="Total count of circuit breaker state transitions to OPEN",
            unit="1"
        )

    def record_execution(self, operation: str, status: str) -> None:
        """Records an execution success or failure event."""
        self.execution_counter.add(1, {"operation": operation, "status": status})

    def record_recovery_latency(self, operation: str, latency_ms: float) -> None:
        """Records the recovery duration of a self-healing cycle."""
        self.recovery_latency_histogram.record(latency_ms, {"operation": operation})

    def record_circuit_trip(self, reason: str) -> None:
        """Records a circuit breaker trip event."""
        self.circuit_breaker_counter.add(1, {"reason": reason})