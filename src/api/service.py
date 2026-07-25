"""
Lightweight asynchronous control plane and mock microservice API server
exposing health checks, pipeline triggers, and telemetry endpoints.
"""

import asyncio
import structlog
from aiohttp import web
from src.core.supervisor import SystemSupervisor
from src.core.pipeline import ExecutionPipeline
from src.telemetry.metrics import TelemetryMetrics

logger = structlog.get_logger(__name__)


class ReliabilityServiceAPI:
    """
    HTTP server exposing operational endpoints for the self-healing architecture.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.app = web.Application()
        self.supervisor = SystemSupervisor(failure_threshold=3, recovery_timeout_sec=0.35)
        self.pipeline = ExecutionPipeline(supervisor=self.supervisor, default_timeout=0.35)
        self.metrics = TelemetryMetrics()

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Registers HTTP routes for liveness, readiness, and task execution."""
        self.app.router.add_get("/healthz", self.handle_liveness)
        self.app.router.add_get("/readyz", self.handle_readiness)
        self.app.router.post("/execute", self.handle_execute_task)

    async def handle_liveness(self, request: web.Request) -> web.Response:
        """Kubernetes liveness probe endpoint."""
        return web.json_response({"status": "ALIVE", "circuit_state": self.supervisor.state})

    async def handle_readiness(self, request: web.Request) -> web.Response:
        """Kubernetes readiness probe endpoint verifying circuit breaker health."""
        if self.supervisor.state == "OPEN":
            return web.json_response({"status": "NOT_READY", "reason": "Circuit breaker is OPEN"}, status=503)
        return web.json_response({"status": "READY"})

    async def handle_execute_task(self, request: web.Request) -> web.Response:
        """Executes a target simulated workload through the resilient pipeline."""
        try:
            data = await request.json()
            task_name = data.get("operation", "default_workload")
            simulate_failure = data.get("simulate_failure", False)

            async def mock_workload() -> str:
                if simulate_failure:
                    raise TimeoutError("Simulated edge execution timeout.")
                await asyncio.sleep(0.02)
                return f"Workload '{task_name}' executed successfully."

            result = await self.pipeline.run(task_name, mock_workload)
            self.metrics.record_execution(task_name, "SUCCESS")
            return web.json_response({"status": "SUCCESS", "result": result})

        except Exception as exc:
            logger.error("API execution request failed", error=str(exc))
            self.metrics.record_execution("api_request", "FAILURE")
            return web.json_response({"status": "ERROR", "message": str(exc)}, status=500)

    def run(self) -> None:
        """Starts the aiohttp microservice server."""
        logger.info("Starting Reliability Service API control plane", host=self.host, port=self.port)
        web.run_app(self.app, host=self.host, port=self.port)


if __name__ == "__main__":
    service = ReliabilityServiceAPI()
    service.run()