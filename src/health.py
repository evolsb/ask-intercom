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
        # For Railway/production deployment, API keys are optional (user-provided via UI)
        # Only require log directory to be writable for system health
        is_valid = results["log_directory"] == "writable"

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
        import json
        from datetime import datetime, timedelta

        try:
            # Path to log files
            log_dir = Path(".ask-intercom-analytics/logs")
            if not log_dir.exists():
                return self._default_metrics()

            # Get log files from last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            response_times = []
            total_queries = 0
            error_count = 0
            last_query_time = 0

            # Process log files
            for log_file in log_dir.glob("backend-*.jsonl"):
                try:
                    # Extract date from filename (backend-YYYY-MM-DD.jsonl)
                    date_str = log_file.stem.replace("backend-", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    # Skip files older than 24 hours
                    if file_date < cutoff_time.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ):
                        continue

                    with open(log_file, "r") as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())

                                # Skip entries older than 24 hours
                                if "timestamp" in entry:
                                    entry_time = datetime.fromisoformat(
                                        entry["timestamp"].replace("Z", "+00:00")
                                    )
                                    if entry_time < cutoff_time:
                                        continue

                                # Track query completions
                                if entry.get(
                                    "event_type"
                                ) == "query_completed" or "Query completed" in entry.get(
                                    "message", ""
                                ):
                                    total_queries += 1
                                    # Convert duration from seconds to milliseconds
                                    duration_ms = int(
                                        entry.get("duration_seconds", 0) * 1000
                                    )
                                    response_times.append(duration_ms)
                                    last_query_time = max(last_query_time, duration_ms)

                                # Track errors
                                if (
                                    entry.get("level") == "ERROR"
                                    or entry.get("event_type") == "query_error"
                                    or "error" in entry.get("message", "").lower()
                                ):
                                    error_count += 1

                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue

                except Exception:
                    continue

            # Calculate metrics
            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0.0
            )
            error_rate = error_count / max(total_queries + error_count, 1)

            return PerformanceMetrics(
                last_query_time_ms=last_query_time,
                avg_response_time_24h=avg_response_time,
                error_rate_24h=error_rate,
                total_queries_24h=total_queries,
            )

        except Exception as e:
            self.logger.error(f"Failed to calculate performance metrics: {e}")
            return self._default_metrics()

    def _default_metrics(self) -> PerformanceMetrics:
        """Return default metrics when calculation fails."""
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
                # Only check connectivity if API keys are actually present
                env_status.intercom_token == "present"
                and connectivity_status.intercom_api != "reachable"
            ) or (
                env_status.openai_key == "present"
                and connectivity_status.openai_api != "reachable"
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
