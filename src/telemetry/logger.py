"""
Configures production-ready structured logging (structlog) with automatic
rollback log generation for auditing self-healing events.
"""

import logging
import sys
import structlog
from typing import Any, Dict

def configure_logging() -> None:
    """Configures global structlog and standard library logging integration."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RollbackAuditor:
    """
    Generates structured audit logs whenever an automated rollback or
    runtime patch is applied by the self-healing architecture.
    """

    def __init__(self) -> None:
        self.logger = structlog.get_logger("rollback_auditor")

    def log_rollback(self, operation: str, reason: str, metadata: Dict[str, Any]) -> None:
        """Emits a critical structured audit log for system state rollbacks."""
        self.logger.critical(
            "AUTOMATED_ROLLBACK_EXECUTED",
            operation=operation,
            reason=reason,
            context=metadata
        )