"""
Domain-specific exceptions for the self-healing microservices architecture.
Designed with distinct failure categories to allow the APR and Chaos engines
to isolate drift, resource exhaustion, and concurrency violations instantly.
"""

class SystemReliabilityError(Exception):
    """Base exception for all reliability and execution pipeline errors."""
    def __init__(self, message: str, error_code: str, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable


class RuntimeDriftError(SystemReliabilityError):
    """Raised when execution state diverges from the steady-state hypothesis."""
    def __init__(self, message: str):
        super().__init__(message, error_code="ERR_RUNTIME_DRIFT", retryable=True)


class ChaosInjectionViolation(SystemReliabilityError):
    """Raised when a chaos probe detects an unhandled safety boundary violation."""
    def __init__(self, message: str):
        super().__init__(message, error_code="ERR_CHAOS_VIOLATION", retryable=False)


class RepairVerificationFailedError(SystemReliabilityError):
    """Raised when an automated patch fails the sandbox verification loop."""
    def __init__(self, message: str):
        super().__init__(message, error_code="ERR_REPAIR_FAILED", retryable=False)


class CircuitBreakerOpenError(SystemReliabilityError):
    """Raised when the execution pipeline trips due to cascading node degradation."""
    def __init__(self, message: str):
        super().__init__(message, error_code="ERR_CIRCUIT_OPEN", retryable=False)