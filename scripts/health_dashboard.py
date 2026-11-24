#!/usr/bin/env python3
"""Health monitoring dashboard and reporting for guarded workflows.

Provides real-time health status visualization and reporting capabilities.
Generates alerts for degraded or unhealthy modules.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from health_tracker import HealthTracker, HealthStatus

ROOT = Path(__file__).resolve().parents[1]
HEALTH_DB = ROOT / "outputs" / "health_tracking.json"


class HealthDashboard:
    """Real-time health monitoring dashboard."""

    def __init__(self, health_db_path: Path = HEALTH_DB):
        """Initialize dashboard.

        Args:
            health_db_path: Path to health database JSON file
        """
        self.health_db_path = health_db_path
        self.tracker = HealthTracker(health_db_path)

    def print_overall_status(self) -> None:
        """Print overall platform health status."""
        summary = self.tracker.get_health_summary()

        # Color codes for terminal output
        colors = {
            "healthy": "\033[92m",  # Green
            "degraded": "\033[93m",  # Yellow
            "unhealthy": "\033[91m",  # Red
            "unknown": "\033[94m",  # Blue
            "reset": "\033[0m",
        }

        status = summary["overall_status"]
        color = colors.get(status, colors["reset"])

        print(f"\n{color}{'='*60}")
        print(f"  PLATFORM HEALTH STATUS: {status.upper()}")
        print(f"{'='*60}{colors['reset']}\n")

        print(f"  Total Modules: {summary['total_modules']}")
        print(f"  Total Executions: {summary['total_executions']}")
        print(f"  Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"  Overall Error Rate: {summary['overall_error_rate']:.1f}%")

        # Module status distribution
        if summary.get("module_status_distribution"):
            print(f"\n  Module Status Distribution:")
            for status_name, count in summary["module_status_distribution"].items():
                color = colors.get(status_name, colors["reset"])
                print(f"    {color}{status_name.upper()}: {count}{colors['reset']}")

    def print_module_details(self) -> None:
        """Print detailed health metrics for each module."""
        if not self.tracker.aggregated:
            print("\n  No modules with health data yet.")
            return

        print(f"\n{'='*60}")
        print(f"  MODULE HEALTH DETAILS")
        print(f"{'='*60}\n")

        colors = {
            "healthy": "\033[92m",
            "degraded": "\033[93m",
            "unhealthy": "\033[91m",
            "unknown": "\033[94m",
            "reset": "\033[0m",
        }

        for key in sorted(self.tracker.aggregated.keys()):
            metrics = self.tracker.aggregated[key]
            status_color = colors.get(metrics.status.value, colors["reset"])

            print(f"{status_color}📊 {metrics.module_name}{colors['reset']}")
            print(f"  Status: {status_color}{metrics.status.value.upper()}{colors['reset']}")
            print(f"  Executions: {metrics.total_executions}")
            print(f"    - Successful: {metrics.successful_executions}")
            print(f"    - Failed: {metrics.failed_executions}")
            print(f"    - Blocked: {metrics.blocked_executions}")
            print(f"    - Awaiting Confirmation: {metrics.awaiting_confirmation}")
            print(f"  Success Rate: {metrics.success_rate:.1f}%")
            print(f"  Error Rate: {metrics.error_rate:.1f}%")
            print(f"  Latency (ms):")
            print(f"    - Average: {metrics.average_duration_ms:.1f}")
            print(f"    - P50: {metrics.p50_duration_ms:.1f}")
            print(f"    - P95: {metrics.p95_duration_ms:.1f}")
            print(f"    - P99: {metrics.p99_duration_ms:.1f}")
            if metrics.last_error:
                print(f"  Last Error: {metrics.last_error}")
            print()

    def print_alerts(self) -> None:
        """Print active alerts for degraded or unhealthy modules."""
        summary = self.tracker.get_health_summary()
        alerts = summary.get("alerts", [])

        if not alerts:
            print(f"\n✓ No active alerts - all modules healthy!\n")
            return

        print(f"\n{'='*60}")
        print(f"  ⚠️  ACTIVE ALERTS ({len(alerts)})")
        print(f"{'='*60}\n")

        for alert in alerts:
            status_emoji = "🔴" if alert["status"] == "unhealthy" else "🟡"
            print(f"{status_emoji} {alert['module']}")
            print(f"    Status: {alert['status']}")
            print(f"    Success Rate: {alert['success_rate']}")
            print(f"    Error Rate: {alert['error_rate']}")
            if alert.get("last_error"):
                print(f"    Last Error: {alert['last_error']}")
            print()

    def print_sla_report(self) -> None:
        """Print SLA compliance report."""
        print(f"\n{'='*60}")
        print(f"  SLA COMPLIANCE REPORT")
        print(f"{'='*60}\n")

        # SLA thresholds
        sla_thresholds = {
            "success_rate": 99.0,  # 99% success rate target
            "p95_latency_ms": 1000,  # 1 second p95 latency target
            "error_rate": 1.0,  # 1% error rate threshold
        }

        print(f"SLA Targets:")
        print(f"  - Success Rate: ≥ {sla_thresholds['success_rate']:.1f}%")
        print(f"  - P95 Latency: ≤ {sla_thresholds['p95_latency_ms']:.0f}ms")
        print(f"  - Error Rate: ≤ {sla_thresholds['error_rate']:.1f}%")

        summary = self.tracker.get_health_summary()
        success_rate = summary.get("overall_success_rate", 0.0)
        error_rate = summary.get("overall_error_rate", 0.0)

        print(f"\nPlatform SLA Status:")
        print(f"  ✓ Success Rate: {success_rate:.1f}%", end="")
        if success_rate >= sla_thresholds["success_rate"]:
            print(" ✓ MET")
        else:
            print(f" ✗ MISS (target: {sla_thresholds['success_rate']:.1f}%)")

        print(f"  ✓ Error Rate: {error_rate:.1f}%", end="")
        if error_rate <= sla_thresholds["error_rate"]:
            print(" ✓ MET")
        else:
            print(f" ✗ MISS (target: ≤{sla_thresholds['error_rate']:.1f}%)")

        # Check p95 latency
        max_p95 = 0
        for metrics in self.tracker.aggregated.values():
            if metrics.p95_duration_ms > max_p95:
                max_p95 = metrics.p95_duration_ms

        print(f"  ✓ P95 Latency: {max_p95:.0f}ms", end="")
        if max_p95 <= sla_thresholds["p95_latency_ms"]:
            print(" ✓ MET")
        else:
            print(f" ✗ MISS (target: ≤{sla_thresholds['p95_latency_ms']:.0f}ms)")
        print()

    def export_report(self, output_path: Path | None = None) -> Path:
        """Export comprehensive health report to JSON.

        Args:
            output_path: Output file path (default: outputs/health_report.json)

        Returns:
            Path to exported report
        """
        if output_path is None:
            output_path = ROOT / "outputs" / "health_report.json"

        summary = self.tracker.get_health_summary()
        aggregated = {k: v.to_dict() for k, v in self.tracker.aggregated.items()}

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_summary": summary,
            "module_metrics": aggregated,
            "execution_history": [m.to_dict() for m in self.tracker.metrics[-100:]],  # Last 100 executions
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def display(self) -> None:
        """Display complete health dashboard."""
        self.print_overall_status()
        self.print_module_details()
        self.print_alerts()
        self.print_sla_report()

        # Export report
        report_path = self.export_report()
        print(f"\n📊 Health report exported to: {report_path}")


def main() -> None:
    """Display health monitoring dashboard."""
    dashboard = HealthDashboard()
    dashboard.display()


if __name__ == "__main__":
    main()
