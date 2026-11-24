#!/usr/bin/env python3
"""Runtime health tracking schema and monitoring for guarded workflows.

Tracks execution metrics, failures, performance, and health status across all
workflow modules. Enables proactive alerting and post-mortem analysis.

Health tracking dimensions:
1. Execution metrics (count, success rate, duration)
2. Error tracking (type, frequency, resolution)
3. Performance SLAs (p50, p95, p99 latencies)
4. Data quality (schema validation, consistency)
5. Approval gate health (confirm delays, expiration rate)
6. Platform integration status (API availability, rate limits)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
HEALTH_DB = ROOT / "outputs" / "health_tracking.json"


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ExecutionResult(str, Enum):
    """Execution result states."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXPIRED = "expired"


@dataclass
class ExecutionMetric:
    """Single execution metric data point."""
    task_id: str
    action_type: str
    platform: str
    result: ExecutionResult
    duration_ms: int
    timestamp: str
    error_message: str | None = None
    p02_status: str | None = None
    verification_passed: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class HealthMetrics:
    """Aggregated health metrics for a workflow module."""
    module_name: str
    action_type: str
    platform: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    blocked_executions: int = 0
    awaiting_confirmation: int = 0
    average_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    error_rate: float = 0.0
    last_execution: str | None = None
    last_error: str | None = None
    status: HealthStatus = HealthStatus.UNKNOWN
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        data = asdict(self)
        data["success_rate"] = self.success_rate
        return data


class HealthTracker:
    """Tracks runtime health metrics across all workflow modules."""

    def __init__(self, health_db_path: Path = HEALTH_DB):
        """Initialize health tracker.

        Args:
            health_db_path: Path to health database JSON file
        """
        self.health_db_path = health_db_path
        self.metrics: list[ExecutionMetric] = []
        self.aggregated: dict[str, HealthMetrics] = {}
        self._load_health_db()

    def _load_health_db(self) -> None:
        """Load existing health database if available."""
        if self.health_db_path.exists():
            try:
                data = json.loads(self.health_db_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "metrics" in data:
                    for m in data.get("metrics", []):
                        self.metrics.append(ExecutionMetric(**m))
                    self._recalculate_aggregated()
            except Exception:
                pass

    def _recalculate_aggregated(self) -> None:
        """Recalculate aggregated metrics from execution metrics."""
        self.aggregated.clear()
        durations_by_module: dict[str, list[int]] = defaultdict(list)

        for metric in self.metrics:
            key = f"{metric.action_type}@{metric.platform}"

            if key not in self.aggregated:
                self.aggregated[key] = HealthMetrics(
                    module_name=key,
                    action_type=metric.action_type,
                    platform=metric.platform,
                )

            agg = self.aggregated[key]
            agg.total_executions += 1
            agg.last_execution = metric.timestamp

            # Update counters by result
            if metric.result == ExecutionResult.SUCCESS:
                agg.successful_executions += 1
            elif metric.result == ExecutionResult.FAILED:
                agg.failed_executions += 1
                agg.last_error = metric.error_message
            elif metric.result == ExecutionResult.BLOCKED:
                agg.blocked_executions += 1
            elif metric.result == ExecutionResult.AWAITING_CONFIRMATION:
                agg.awaiting_confirmation += 1

            # Track duration for percentile calculations
            durations_by_module[key].append(metric.duration_ms)

        # Calculate duration percentiles and error rate
        for key, agg in self.aggregated.items():
            durations = sorted(durations_by_module[key])
            if durations:
                agg.average_duration_ms = sum(durations) / len(durations)
                agg.p50_duration_ms = durations[len(durations) // 2]
                agg.p95_duration_ms = durations[int(len(durations) * 0.95)]
                agg.p99_duration_ms = durations[int(len(durations) * 0.99)]

            agg.error_rate = (agg.failed_executions / agg.total_executions * 100) if agg.total_executions > 0 else 0.0
            agg.status = self._determine_health_status(agg)
            agg.updated_at = datetime.now(timezone.utc).isoformat()

    def _determine_health_status(self, metrics: HealthMetrics) -> HealthStatus:
        """Determine health status based on metrics.

        Health thresholds:
        - UNHEALTHY: success_rate < 50% or error_rate > 20%
        - DEGRADED: success_rate < 80% or error_rate > 5%
        - HEALTHY: success_rate >= 80% and error_rate <= 5%
        """
        if metrics.total_executions == 0:
            return HealthStatus.UNKNOWN

        success_rate = metrics.success_rate
        error_rate = metrics.error_rate

        if success_rate < 50 or error_rate > 20:
            return HealthStatus.UNHEALTHY
        elif success_rate < 80 or error_rate > 5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def record_execution(
        self,
        task_id: str,
        action_type: str,
        platform: str,
        result: ExecutionResult,
        duration_ms: int,
        error_message: str | None = None,
        p02_status: str | None = None,
        verification_passed: bool | None = None,
    ) -> None:
        """Record a single execution metric.

        Args:
            task_id: Unique task identifier
            action_type: Type of action (e.g., "inventory_update")
            platform: Target platform (e.g., "WB_CN")
            result: Execution result status
            duration_ms: Execution duration in milliseconds
            error_message: Error message if execution failed
            p02_status: P0-2 approval status
            verification_passed: Whether post-execution verification passed
        """
        metric = ExecutionMetric(
            task_id=task_id,
            action_type=action_type,
            platform=platform,
            result=result,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            error_message=error_message,
            p02_status=p02_status,
            verification_passed=verification_passed,
        )
        self.metrics.append(metric)
        self._recalculate_aggregated()

    def get_module_health(self, action_type: str, platform: str) -> HealthMetrics | None:
        """Get health metrics for a specific module.

        Args:
            action_type: Action type
            platform: Platform name

        Returns:
            HealthMetrics if found, None otherwise
        """
        key = f"{action_type}@{platform}"
        return self.aggregated.get(key)

    def get_all_health(self) -> dict[str, HealthMetrics]:
        """Get all aggregated health metrics.

        Returns:
            Dict mapping module names to health metrics
        """
        return self.aggregated.copy()

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall platform health summary.

        Returns:
            Summary with overall status, module status, and alerts
        """
        if not self.aggregated:
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "total_modules": 0,
                "total_executions": 0,
                "total_successful": 0,
                "total_failed": 0,
                "overall_success_rate": 0.0,
                "overall_error_rate": 0.0,
                "alerts": [],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Count status distribution
        status_counts = defaultdict(int)
        total_executions = 0
        total_successful = 0
        total_failed = 0
        alerts = []

        for metrics in self.aggregated.values():
            status_counts[metrics.status.value] += 1
            total_executions += metrics.total_executions
            total_successful += metrics.successful_executions
            total_failed += metrics.failed_executions

            # Generate alerts for unhealthy or degraded modules
            if metrics.status in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED):
                alerts.append({
                    "module": metrics.module_name,
                    "status": metrics.status.value,
                    "success_rate": f"{metrics.success_rate:.1f}%",
                    "error_rate": f"{metrics.error_rate:.1f}%",
                    "last_error": metrics.last_error,
                })

        # Determine overall status
        if status_counts.get(HealthStatus.UNHEALTHY.value, 0) > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts.get(HealthStatus.DEGRADED.value, 0) > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "total_modules": len(self.aggregated),
            "module_status_distribution": {k: v for k, v in status_counts.items()},
            "total_executions": total_executions,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "overall_success_rate": (total_successful / total_executions * 100) if total_executions > 0 else 0.0,
            "overall_error_rate": (total_failed / total_executions * 100) if total_executions > 0 else 0.0,
            "alerts": alerts,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_health_db(self) -> None:
        """Save health database to JSON file."""
        self.health_db_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "aggregated": {k: v.to_dict() for k, v in self.aggregated.items()},
            "summary": self.get_health_summary(),
        }

        self.health_db_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def prune_old_metrics(self, days: int = 30) -> int:
        """Remove metrics older than specified days.

        Args:
            days: Number of days to keep (default 30)

        Returns:
            Number of metrics removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        original_count = len(self.metrics)

        self.metrics = [
            m for m in self.metrics
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]

        removed = original_count - len(self.metrics)
        if removed > 0:
            self._recalculate_aggregated()
            self.save_health_db()

        return removed


def main() -> None:
    """Demo health tracking usage."""
    tracker = HealthTracker()

    print(f"[Health] Loading existing metrics...")
    print(f"[Health] Total executions tracked: {len(tracker.metrics)}")

    # Display current health summary
    summary = tracker.get_health_summary()
    print(f"\n[Health] Platform Health Summary:")
    print(f"  Overall Status: {summary['overall_status']}")
    print(f"  Total Modules: {summary['total_modules']}")
    print(f"  Total Executions: {summary['total_executions']}")
    print(f"  Overall Success Rate: {summary['overall_success_rate']:.1f}%")

    if summary["alerts"]:
        print(f"\n[Health] Alerts ({len(summary['alerts'])}):")
        for alert in summary["alerts"]:
            print(f"  - {alert['module']}: {alert['status']} "
                  f"(success={alert['success_rate']}, error={alert['error_rate']})")

    # Display module health
    if tracker.aggregated:
        print(f"\n[Health] Module Health Metrics:")
        for key, metrics in sorted(tracker.aggregated.items()):
            print(f"  {key}:")
            print(f"    Status: {metrics.status.value}")
            print(f"    Executions: {metrics.total_executions} "
                  f"(success={metrics.successful_executions}, "
                  f"failed={metrics.failed_executions})")
            print(f"    Success Rate: {metrics.success_rate:.1f}%")
            print(f"    Latency: avg={metrics.average_duration_ms:.0f}ms, "
                  f"p95={metrics.p95_duration_ms:.0f}ms, "
                  f"p99={metrics.p99_duration_ms:.0f}ms")

    # Save health database
    tracker.save_health_db()
    print(f"\n[Health] ✓ Health database saved: {HEALTH_DB}")


if __name__ == "__main__":
    main()
