"""
Provides distributed tracing context managers to trace request paths across
microservices and async execution boundaries.
"""

import structlog
from contextlib import contextmanager
from typing import Generator, Any
from opentelemetry import trace
from opentelemetry.trace import Tracer, Span

logger = structlog.get_logger(__name__)


class TelemetryTracer:
    """
    Wraps OpenTelemetry tracer utilities to generate structured execution spans
    for analysis during chaos testing and runtime repair workflows.
    """

    def __init__(self, service_name: str = "autonomous-system-reliability") -> None:
        self.tracer: Tracer = trace.get_tracer(service_name)

    @contextmanager
    def trace_span(self, span_name: str, attributes: Optional[dict[str, Any]] = None) -> Generator[Span, None, None]:
        """Context manager to start and cleanly close an OpenTelemetry trace span."""
        with self.tracer.start_as_current_span(span_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            try:
                yield span
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise