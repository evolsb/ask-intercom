"""
Environment validation and health check functionality.
"""
import asyncio
import os
import re
from pathlib import Path

import httpx
from pydantic import BaseModel

from .logging import session_logger


class EnvironmentStatus(BaseModel):
    """Environment validation results."""

    valid: bool
    intercom_token: str  # "present", "missing", "invalid_format"
    openai_key: str  # "present", "missing", "invalid_format"
    log_directory: str  # "writable", "readonly", "missing"


class ConnectivityStatus(BaseModel):
    """API connectivity test results."""

    intercom_api: str  # "reachable", "unreachable", "unauthorized"
    openai_api: str  # "reachable", "unreachable", "unauthorized"


class PerformanceMetrics(BaseModel):
    """Performance and usage metrics."""

    last_query_time_ms: int
    avg_response_time_24h: float
    error_rate_24h: float
    total_queries_24h: int


class HealthStatus(BaseModel):
    """Overall system health status."""

    status: str  # "healthy", "degraded", "unhealthy"
    environment: EnvironmentStatus
    connectivity: ConnectivityStatus
    performance: PerformanceMetrics
    timestamp: str


class EnvironmentValidator:
    """Validates environment configuration and external dependencies."""

    def __init__(self):
        self.logger = session_logger

    def validate_environment(self) -> EnvironmentStatus:
        """Validate all environment variables and configurations."""
        results = {}

        # Check Intercom token
        intercom_token = os.getenv("INTERCOM_ACCESS_TOKEN", "").strip()
        if not intercom_token:
            results["intercom_token"] = "missing"
        elif not self._is_valid_intercom_token(intercom_token):
            results["intercom_token"] = "invalid_format"
        else:
            results["intercom_token"] = "present"

        # Check OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not openai_key:
            results["openai_key"] = "missing"
        elif not self._is_valid_openai_key(openai_key):
            results["openai_key"] = "invalid_format"
        else:
            results["openai_key"] = "present"

        # Check log directory permissions
        log_dir = Path(".ask-intercom-analytics")
        if not log_dir.exists():
            try:
                log_dir.mkdir(exist_ok=True)
                results["log_directory"] = "writable"
            except PermissionError:
                results["log_directory"] = "missing"
        elif os.access(log_dir, os.W_OK):
            results["log_directory"] = "writable"
        else:
            results["log_directory"] = "readonly"

        # Determine overall validity
        is_valid = all(
            status in ["present", "writable"]
            for status in [
                results["intercom_token"],
                results["openai_key"],
                results["log_directory"],
            ]
        )

        status = EnvironmentStatus(valid=is_valid, **results)

        # Log validation results
        self.logger.info(
            f"Environment validation {'passed' if is_valid else 'failed'}",
            event="environment_validation",
            data={"results": results},
        )

        return status

    def _is_valid_intercom_token(self, token: str) -> bool:
        """Check if Intercom token has valid format."""
        # Intercom tokens are typically base64-encoded and start with 'dG9r' or similar
        return len(token) > 20 and re.match(r"^[A-Za-z0-9+/=]+$", token)

    def _is_valid_openai_key(self, key: str) -> bool:
        """Check if OpenAI key has valid format."""
        # OpenAI keys start with 'sk-' followed by alphanumeric characters
        return key.startswith("sk-") and len(key) > 40

    async def test_connectivity(self) -> ConnectivityStatus:
        """Test connectivity to external APIs."""
        results = {}

        # Test Intercom API
        try:
            results["intercom_api"] = await self._test_intercom_connection()
        except Exception as e:
            self.logger.error(
                f"Intercom connectivity test failed: {str(e)}",
                event="connectivity_test",
                service="intercom",
                exc_info=True,
            )
            results["intercom_api"] = "unreachable"

        # Test OpenAI API
        try:
            results["openai_api"] = await self._test_openai_connection()
        except Exception as e:
            self.logger.error(
                f"OpenAI connectivity test failed: {str(e)}",
                event="connectivity_test",
                service="openai",
                exc_info=True,
            )
            results["openai_api"] = "unreachable"

        return ConnectivityStatus(**results)

    async def _test_intercom_connection(self) -> str:
        """Test Intercom API connectivity."""
        token = os.getenv("INTERCOM_ACCESS_TOKEN")
        if not token:
            return "unauthorized"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Intercom-Version": "2.10",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    "https://api.intercom.io/me", headers=headers
                )

                if response.status_code == 200:
                    return "reachable"
                elif response.status_code == 401:
                    return "unauthorized"
                else:
                    return "unreachable"

            except httpx.TimeoutException:
                return "unreachable"
            except httpx.RequestError:
                return "unreachable"

    async def _test_openai_connection(self) -> str:
        """Test OpenAI API connectivity."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "unauthorized"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Simple models list request to test auth
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    "https://api.openai.com/v1/models", headers=headers
                )

                if response.status_code == 200:
                    return "reachable"
                elif response.status_code == 401:
                    return "unauthorized"
                else:
                    return "unreachable"

            except httpx.TimeoutException:
                return "unreachable"
            except httpx.RequestError:
                return "unreachable"


class PerformanceTracker:
    """Tracks system performance metrics."""

    def __init__(self):
        self.logger = session_logger

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics from logs."""
        # This would analyze log files for metrics
        # For now, return placeholder values
        return PerformanceMetrics(
            last_query_time_ms=0,
            avg_response_time_24h=0.0,
            error_rate_24h=0.0,
            total_queries_24h=0,
        )


class HealthChecker:
    """Main health check orchestrator."""

    def __init__(self):
        self.env_validator = EnvironmentValidator()
        self.performance_tracker = PerformanceTracker()
        self.logger = session_logger

    async def get_health_status(self) -> HealthStatus:
        """Get comprehensive system health status."""
        try:
            # Run all health checks
            env_status = self.env_validator.validate_environment()
            connectivity_status = await self.env_validator.test_connectivity()
            performance_metrics = self.performance_tracker.get_performance_metrics()

            # Determine overall health status
            if not env_status.valid:
                overall_status = "unhealthy"
            elif (
                connectivity_status.intercom_api != "reachable"
                or connectivity_status.openai_api != "reachable"
            ):
                overall_status = "degraded"
            else:
                overall_status = "healthy"

            health_status = HealthStatus(
                status=overall_status,
                environment=env_status,
                connectivity=connectivity_status,
                performance=performance_metrics,
                timestamp=str(asyncio.get_event_loop().time()),
            )

            self.logger.info(
                f"Health check completed: {overall_status}",
                event="health_check",
                data={"status": overall_status},
            )

            return health_status

        except Exception as e:
            self.logger.error(
                f"Health check failed: {str(e)}",
                event="health_check_error",
                exc_info=True,
            )

            # Return minimal unhealthy status
            return HealthStatus(
                status="unhealthy",
                environment=EnvironmentStatus(
                    valid=False,
                    intercom_token="unknown",
                    openai_key="unknown",
                    log_directory="unknown",
                ),
                connectivity=ConnectivityStatus(
                    intercom_api="unknown", openai_api="unknown"
                ),
                performance=PerformanceMetrics(
                    last_query_time_ms=0,
                    avg_response_time_24h=0.0,
                    error_rate_24h=1.0,
                    total_queries_24h=0,
                ),
                timestamp=str(asyncio.get_event_loop().time()),
            )


# Global health checker instance
health_checker = HealthChecker()
