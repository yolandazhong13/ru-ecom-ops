#!/usr/bin/env python3
"""API integration monitoring for WB and Ozon platforms.

Tracks API availability, rate limits, error rates, and performance metrics.
Integrates with health tracking system for unified platform monitoring.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_HEALTH_DB = ROOT / "outputs" / "api_health_tracking.json"


class APIStatus(str, Enum):
    """API integration status."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class APIMetric:
    """Single API call metric."""
    api_endpoint: str
    method: str
    platform: str
    status_code: int | None = None
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: str | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class APIEndpointHealth:
    """Aggregated health metrics for API endpoint."""
    endpoint: str
    platform: str
    method: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    average_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    error_rate: float = 0.0
    status: APIStatus = APIStatus.UNKNOWN
    last_call: str | None = None
    last_error: str | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        data = asdict(self)
        data["success_rate"] = self.success_rate
        return data


class APIHealthTracker:
    """Tracks API integration health across platforms."""

    def __init__(self, api_health_db_path: Path = API_HEALTH_DB):
        """Initialize API health tracker.

        Args:
            api_health_db_path: Path to API health database JSON file
        """
        self.api_health_db_path = api_health_db_path
        self.metrics: list[APIMetric] = []
        self.aggregated: dict[str, APIEndpointHealth] = {}
        self._load_api_health_db()

    def _load_api_health_db(self) -> None:
        """Load existing API health database if available."""
        if self.api_health_db_path.exists():
            try:
                data = json.loads(self.api_health_db_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "metrics" in data:
                    for m in data.get("metrics", []):
                        self.metrics.append(APIMetric(**m))
                    self._recalculate_aggregated()
            except Exception:
                pass

    def _recalculate_aggregated(self) -> None:
        """Recalculate aggregated metrics from API metrics."""
        self.aggregated.clear()
        durations_by_endpoint: dict[str, list[int]] = {}

        for metric in self.metrics:
            key = f"{metric.method}:{metric.api_endpoint}@{metric.platform}"

            if key not in self.aggregated:
                self.aggregated[key] = APIEndpointHealth(
                    endpoint=metric.api_endpoint,
                    platform=metric.platform,
                    method=metric.method,
                )
                durations_by_endpoint[key] = []

            agg = self.aggregated[key]
            agg.total_calls += 1
            agg.last_call = metric.timestamp

            # Update rate limit info
            if metric.rate_limit_remaining is not None:
                agg.rate_limit_remaining = metric.rate_limit_remaining
            if metric.rate_limit_reset is not None:
                agg.rate_limit_reset = metric.rate_limit_reset

            # Update call status
            if metric.status_code and 200 <= metric.status_code < 300:
                agg.successful_calls += 1
            else:
                agg.failed_calls += 1
                agg.last_error = metric.error_message

            # Track duration
            durations_by_endpoint[key].append(metric.duration_ms)

        # Calculate duration percentiles and error rate
        for key, agg in self.aggregated.items():
            durations = sorted(durations_by_endpoint[key])
            if durations:
                agg.average_duration_ms = sum(durations) / len(durations)
                agg.p95_duration_ms = durations[int(len(durations) * 0.95)]

            agg.error_rate = (agg.failed_calls / agg.total_calls * 100) if agg.total_calls > 0 else 0.0
            agg.status = self._determine_api_status(agg)
            agg.updated_at = datetime.now(timezone.utc).isoformat()

    def _determine_api_status(self, metrics: APIEndpointHealth) -> APIStatus:
        """Determine API endpoint status based on metrics.

        Status thresholds:
        - AVAILABLE: error_rate <= 1%
        - DEGRADED: 1% < error_rate <= 10%
        - UNAVAILABLE: error_rate > 10%
        """
        if metrics.total_calls == 0:
            return APIStatus.UNKNOWN

        if metrics.error_rate > 10:
            return APIStatus.UNAVAILABLE
        elif metrics.error_rate > 1:
            return APIStatus.DEGRADED
        else:
            return APIStatus.AVAILABLE

    def record_api_call(
        self,
        api_endpoint: str,
        method: str,
        platform: str,
        status_code: int | None = None,
        duration_ms: int = 0,
        error_message: str | None = None,
        rate_limit_remaining: int | None = None,
        rate_limit_reset: str | None = None,
    ) -> None:
        """Record API call metric.

        Args:
            api_endpoint: API endpoint path (e.g., "/v3/product/info/list")
            method: HTTP method (GET, POST, etc.)
            platform: Platform name (WB_CN, Ozon, etc.)
            status_code: HTTP status code
            duration_ms: Call duration in milliseconds
            error_message: Error message if call failed
            rate_limit_remaining: Remaining rate limit quota
            rate_limit_reset: Rate limit reset timestamp
        """
        metric = APIMetric(
            api_endpoint=api_endpoint,
            method=method,
            platform=platform,
            status_code=status_code,
            duration_ms=duration_ms,
            error_message=error_message,
            rate_limit_remaining=rate_limit_remaining,
            rate_limit_reset=rate_limit_reset,
        )
        self.metrics.append(metric)
        self._recalculate_aggregated()

    def get_endpoint_health(self, api_endpoint: str, platform: str) -> APIEndpointHealth | None:
        """Get health metrics for specific API endpoint.

        Args:
            api_endpoint: API endpoint path
            platform: Platform name

        Returns:
            APIEndpointHealth if found, None otherwise
        """
        for key, health in self.aggregated.items():
            if health.endpoint == api_endpoint and health.platform == platform:
                return health
        return None

    def get_platform_health(self, platform: str) -> dict[str, APIEndpointHealth]:
        """Get all API endpoints for a platform.

        Args:
            platform: Platform name

        Returns:
            Dict of endpoint -> health metrics for platform
        """
        return {
            key: health for key, health in self.aggregated.items()
            if health.platform == platform
        }

    def get_overall_api_health(self) -> dict[str, Any]:
        """Get overall API integration health summary.

        Returns:
            Summary with status distribution, alerts, and health metrics
        """
        if not self.aggregated:
            return {
                "overall_status": APIStatus.UNKNOWN.value,
                "total_platforms": 0,
                "total_endpoints": 0,
                "total_calls": 0,
                "total_successful": 0,
                "total_failed": 0,
                "overall_error_rate": 0.0,
                "by_platform": {},
                "alerts": [],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Aggregate by platform
        by_platform = {}
        total_calls = 0
        total_successful = 0
        total_failed = 0
        alerts = []

        for endpoint_key, metrics in self.aggregated.items():
            platform = metrics.platform
            if platform not in by_platform:
                by_platform[platform] = {
                    "endpoints": 0,
                    "total_calls": 0,
                    "successful": 0,
                    "failed": 0,
                    "error_rate": 0.0,
                    "status": APIStatus.UNKNOWN.value,
                }

            platform_info = by_platform[platform]
            platform_info["endpoints"] += 1
            platform_info["total_calls"] += metrics.total_calls
            platform_info["successful"] += metrics.successful_calls
            platform_info["failed"] += metrics.failed_calls

            total_calls += metrics.total_calls
            total_successful += metrics.successful_calls
            total_failed += metrics.failed_calls

            # Generate alerts for degraded/unavailable endpoints
            if metrics.status in (APIStatus.DEGRADED, APIStatus.UNAVAILABLE):
                alerts.append({
                    "endpoint": metrics.endpoint,
                    "platform": metrics.platform,
                    "status": metrics.status.value,
                    "error_rate": f"{metrics.error_rate:.1f}%",
                    "last_error": metrics.last_error,
                })

        # Calculate platform error rates
        for platform, info in by_platform.items():
            if info["total_calls"] > 0:
                info["error_rate"] = (info["failed"] / info["total_calls"] * 100)
                if info["error_rate"] > 10:
                    info["status"] = APIStatus.UNAVAILABLE.value
                elif info["error_rate"] > 1:
                    info["status"] = APIStatus.DEGRADED.value
                else:
                    info["status"] = APIStatus.AVAILABLE.value

        # Determine overall status
        unavailable_count = sum(1 for p in by_platform.values() if p["status"] == APIStatus.UNAVAILABLE.value)
        degraded_count = sum(1 for p in by_platform.values() if p["status"] == APIStatus.DEGRADED.value)

        if unavailable_count > 0:
            overall_status = APIStatus.UNAVAILABLE
        elif degraded_count > 0:
            overall_status = APIStatus.DEGRADED
        else:
            overall_status = APIStatus.AVAILABLE

        return {
            "overall_status": overall_status.value,
            "total_platforms": len(by_platform),
            "total_endpoints": len(self.aggregated),
            "total_calls": total_calls,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "overall_error_rate": (total_failed / total_calls * 100) if total_calls > 0 else 0.0,
            "by_platform": by_platform,
            "alerts": alerts,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_api_health_db(self) -> None:
        """Save API health database to JSON file."""
        self.api_health_db_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "aggregated": {k: v.to_dict() for k, v in self.aggregated.items()},
            "summary": self.get_overall_api_health(),
        }

        self.api_health_db_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def main() -> None:
    """Demo API health tracking usage."""
    tracker = APIHealthTracker()

    print(f"[API Health] Loading existing API metrics...")
    print(f"[API Health] Total API calls tracked: {len(tracker.metrics)}")

    summary = tracker.get_overall_api_health()
    print(f"\n[API Health] API Integration Health Summary:")
    print(f"  Overall Status: {summary['overall_status']}")
    print(f"  Total Platforms: {summary['total_platforms']}")
    print(f"  Total Endpoints: {summary['total_endpoints']}")
    print(f"  Total API Calls: {summary['total_calls']}")
    print(f"  Overall Error Rate: {summary['overall_error_rate']:.1f}%")

    if summary.get("by_platform"):
        print(f"\n[API Health] Platform Status:")
        for platform, info in summary["by_platform"].items():
            print(f"  {platform}:")
            print(f"    Status: {info['status']}")
            print(f"    Endpoints: {info['endpoints']}")
            print(f"    Calls: {info['total_calls']} (success={info['successful']}, failed={info['failed']})")
            print(f"    Error Rate: {info['error_rate']:.1f}%")

    if summary.get("alerts"):
        print(f"\n[API Health] Alerts ({len(summary['alerts'])}):")
        for alert in summary["alerts"]:
            print(f"  - {alert['endpoint']} ({alert['platform']}): {alert['status']} "
                  f"(error_rate={alert['error_rate']})")

    tracker.save_api_health_db()
    print(f"\n[API Health] ✓ API health database saved: {API_HEALTH_DB}")


if __name__ == "__main__":
    main()
