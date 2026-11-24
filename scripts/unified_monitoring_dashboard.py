#!/usr/bin/env python3
"""Unified monitoring dashboard integrating all health, API, and validation metrics.

Provides comprehensive real-time view of platform health across execution,
API integration, and data quality dimensions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from health_tracker import HealthTracker, HealthStatus
from api_health_tracker import APIHealthTracker, APIStatus
from data_quality_validator import DataQualityValidator, ValidationStatus

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs"


class UnifiedMonitoringDashboard:
    """Unified monitoring dashboard aggregating all platform metrics."""

    def __init__(self):
        """Initialize dashboard with all trackers."""
        self.health_tracker = HealthTracker()
        self.api_tracker = APIHealthTracker()
        self.validator = DataQualityValidator()

    def get_unified_status(self) -> dict[str, Any]:
        """Get unified platform status across all dimensions.

        Returns:
            Comprehensive status dict with all metrics
        """
        health_summary = self.health_tracker.get_health_summary()
        api_summary = self.api_tracker.get_overall_api_health()
        validation_report = self.validator.get_validation_report()

        # Determine overall platform status
        statuses = [
            health_summary.get("overall_status", "unknown"),
            api_summary.get("overall_status", "unknown"),
        ]

        # Map to severity levels for overall determination
        severity_levels = {
            "healthy": 0,
            "available": 0,
            "degraded": 1,
            "warning": 1,
            "unavailable": 2,
            "invalid": 2,
            "unknown": -1,
        }

        max_severity = max(
            (severity_levels.get(s, -1) for s in statuses),
            default=-1
        )

        if max_severity == 2:
            overall_status = "🔴 CRITICAL"
        elif max_severity == 1:
            overall_status = "🟡 DEGRADED"
        elif max_severity == 0:
            overall_status = "🟢 HEALTHY"
        else:
            overall_status = "⚪ UNKNOWN"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "dimensions": {
                "execution_health": health_summary,
                "api_integration": api_summary,
                "data_quality": validation_report.get("summary", {}),
            },
        }

    def print_dashboard(self) -> None:
        """Print comprehensive unified monitoring dashboard."""
        unified = self.get_unified_status()

        # Color codes
        colors = {
            "critical": "\033[91m",    # Red
            "degraded": "\033[93m",    # Yellow
            "healthy": "\033[92m",     # Green
            "unknown": "\033[94m",     # Blue
            "reset": "\033[0m",
        }

        print(f"\n{colors['reset']}")
        print("┌" + "─" * 78 + "┐")
        print("│" + " " * 78 + "│")
        print("│" + f"  UNIFIED PLATFORM MONITORING DASHBOARD".center(78) + "│")
        print("│" + " " * 78 + "│")
        print("└" + "─" * 78 + "┘")

        # Overall status
        status_line = unified["overall_status"]
        if "CRITICAL" in status_line:
            color = colors["critical"]
        elif "DEGRADED" in status_line:
            color = colors["degraded"]
        elif "HEALTHY" in status_line:
            color = colors["healthy"]
        else:
            color = colors["unknown"]

        print(f"\n{color}═══════════════════════════════════════════════════════════════════════════════")
        print(f"  PLATFORM STATUS: {status_line}")
        print(f"═══════════════════════════════════════════════════════════════════════════════{colors['reset']}\n")

        # Print each dimension
        self._print_execution_health(unified["dimensions"]["execution_health"])
        self._print_api_integration(unified["dimensions"]["api_integration"])
        self._print_data_quality(unified["dimensions"]["data_quality"])

        # Print summary metrics
        self._print_summary_metrics(unified)

        # Print alerts
        self._print_active_alerts(unified)

    def _print_execution_health(self, health_summary: dict[str, Any]) -> None:
        """Print execution health metrics."""
        print("┌─ 📊 EXECUTION HEALTH" + "─" * 57 + "┐")

        status = health_summary.get("overall_status", "unknown").upper()
        status_emoji = self._get_status_emoji(status)

        print(f"│  Status: {status_emoji} {status}")
        print(f"│  Modules: {health_summary.get('total_modules', 0)} active")
        print(f"│  Executions: {health_summary.get('total_executions', 0)} total")
        print(f"│  Success Rate: {health_summary.get('overall_success_rate', 0):.1f}%")
        print(f"│  Error Rate: {health_summary.get('overall_error_rate', 0):.1f}%")

        # Module status distribution
        dist = health_summary.get("module_status_distribution", {})
        if dist:
            print(f"│  Distribution:", end="")
            for status_type, count in sorted(dist.items()):
                print(f" {status_type}={count}", end="")
            print()

        print("└" + "─" * 79 + "┘\n")

    def _print_api_integration(self, api_summary: dict[str, Any]) -> None:
        """Print API integration metrics."""
        print("┌─ 🔌 API INTEGRATION" + "─" * 59 + "┐")

        status = api_summary.get("overall_status", "unknown").upper()
        status_emoji = self._get_status_emoji(status)

        print(f"│  Status: {status_emoji} {status}")
        print(f"│  Platforms: {api_summary.get('total_platforms', 0)}")
        print(f"│  Endpoints: {api_summary.get('total_endpoints', 0)} total")
        print(f"│  API Calls: {api_summary.get('total_calls', 0)} total")
        print(f"│  Success Rate: {100 - api_summary.get('overall_error_rate', 0):.1f}%")
        print(f"│  Error Rate: {api_summary.get('overall_error_rate', 0):.1f}%")

        # Platform status
        by_platform = api_summary.get("by_platform", {})
        if by_platform:
            print(f"│  Platform Status:", end="")
            for platform, info in sorted(by_platform.items()):
                platform_emoji = self._get_status_emoji(info["status"].upper())
                print(f" {platform_emoji} {platform}", end="")
            print()

        print("└" + "─" * 79 + "┘\n")

    def _print_data_quality(self, validation_summary: dict[str, Any]) -> None:
        """Print data quality metrics."""
        print("┌─ ✓ DATA QUALITY" + "─" * 62 + "┐")

        total_val = validation_summary.get("total_validations", 0)
        valid = validation_summary.get("valid", 0)
        invalid = validation_summary.get("invalid", 0)
        warning = validation_summary.get("warning", 0)

        if total_val > 0:
            pass_rate = validation_summary.get("overall_pass_rate", 0)
            status = "VALID" if pass_rate >= 99 else "DEGRADED" if pass_rate >= 80 else "INVALID"
            status_emoji = self._get_status_emoji(status)
            print(f"│  Status: {status_emoji} {status}")
        else:
            print(f"│  Status: ⚪ NO DATA")

        print(f"│  Total Validations: {total_val}")
        print(f"│  Valid: {valid} | Warning: {warning} | Invalid: {invalid}")
        if total_val > 0:
            print(f"│  Overall Pass Rate: {validation_summary.get('overall_pass_rate', 0):.1f}%")

        rule_stats = validation_summary.get("total_validations", 0)
        if rule_stats:
            print(f"│  Total Rules: {total_val} | Pass Rate: {validation_summary.get('overall_pass_rate', 0):.1f}%")

        print("└" + "─" * 79 + "┘\n")

    def _print_summary_metrics(self, unified: dict[str, Any]) -> None:
        """Print summary metrics across all dimensions."""
        print("┌─ 📈 SUMMARY METRICS" + "─" * 57 + "┐")

        health = unified["dimensions"]["execution_health"]
        api = unified["dimensions"]["api_integration"]
        quality = unified["dimensions"]["data_quality"]

        print(f"│  Execution:")
        print(f"│    • Modules Healthy: {health.get('total_modules', 0)}")
        print(f"│    • Execution Success Rate: {health.get('overall_success_rate', 0):.1f}%")

        print(f"│  API:")
        print(f"│    • Endpoints Monitored: {api.get('total_endpoints', 0)}")
        print(f"│    • API Error Rate: {api.get('overall_error_rate', 0):.1f}%")

        print(f"│  Data Quality:")
        if quality.get("total_validations", 0) > 0:
            print(f"│    • Validation Pass Rate: {quality.get('overall_pass_rate', 0):.1f}%")
        else:
            print(f"│    • No validations recorded yet")

        print("└" + "─" * 79 + "┘\n")

    def _print_active_alerts(self, unified: dict[str, Any]) -> None:
        """Print active alerts across all dimensions."""
        alerts = []

        # Execution alerts
        health_alerts = unified["dimensions"]["execution_health"].get("alerts", [])
        for alert in health_alerts:
            alerts.append({
                "type": "EXECUTION",
                "module": alert.get("module"),
                "detail": f"{alert.get('status')}: {alert.get('success_rate')}",
            })

        # API alerts
        api_alerts = unified["dimensions"]["api_integration"].get("alerts", [])
        for alert in api_alerts:
            alerts.append({
                "type": "API",
                "module": f"{alert.get('endpoint')}@{alert.get('platform')}",
                "detail": f"{alert.get('status')}: {alert.get('error_rate')}",
            })

        if alerts:
            print("┌─ ⚠️  ACTIVE ALERTS" + "─" * 59 + "┐")
            for alert in alerts:
                print(f"│  [{alert['type']}] {alert['module']}")
                print(f"│    └─ {alert['detail']}")
            print("└" + "─" * 79 + "┘\n")
        else:
            print("┌─ ✓ ALERTS" + "─" * 67 + "┐")
            print("│  No active alerts - all systems nominal")
            print("└" + "─" * 79 + "┘\n")

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status."""
        status_lower = status.lower()
        if "critical" in status_lower or "unavailable" in status_lower or "invalid" in status_lower:
            return "🔴"
        elif "degraded" in status_lower or "warning" in status_lower:
            return "🟡"
        elif "healthy" in status_lower or "available" in status_lower or "valid" in status_lower:
            return "🟢"
        else:
            return "⚪"

    def export_unified_report(self, output_path: Path | None = None) -> Path:
        """Export unified monitoring report to JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to exported report
        """
        if output_path is None:
            output_path = OUTPUTS_DIR / "unified_monitoring_report.json"

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "unified_status": self.get_unified_status(),
            "execution_health": self.health_tracker.get_health_summary(),
            "api_integration": self.api_tracker.get_overall_api_health(),
            "data_quality": self.validator.get_validation_report(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path


def main() -> None:
    """Display unified monitoring dashboard."""
    dashboard = UnifiedMonitoringDashboard()

    # Display dashboard
    dashboard.print_dashboard()

    # Export report
    report_path = dashboard.export_unified_report()
    print(f"📊 Unified monitoring report exported to: {report_path}\n")


if __name__ == "__main__":
    main()
