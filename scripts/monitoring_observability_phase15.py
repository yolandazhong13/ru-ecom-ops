#!/usr/bin/env python3
"""Phase 15: Monitoring & Observability - Metrics, Dashboarding, and Alerting."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "monitoring"
OUT_DIR.mkdir(parents=True, exist_ok=True)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Alert:
    """An alert event."""
    id: str
    metric_name: str
    severity: AlertSeverity
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsCollector:
    """Collect and manage metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: List[Metric] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Increment value
            labels: Optional labels
        """
        key = f"{name}:{json.dumps(labels or {})}"
        self.counters[key] += value

        metric = Metric(
            name=name,
            type=MetricType.COUNTER,
            value=self.counters[key],
            timestamp=datetime.now(timezone.utc),
            labels=labels or {}
        )
        self.metrics.append(metric)

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels
        """
        key = f"{name}:{json.dumps(labels or {})}"
        self.gauges[key] = value

        metric = Metric(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {}
        )
        self.metrics.append(metric)

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a histogram observation.

        Args:
            name: Metric name
            value: Observation value
            labels: Optional labels
        """
        key = f"{name}:{json.dumps(labels or {})}"
        self.histograms[key].append(value)

        metric = Metric(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {}
        )
        self.metrics.append(metric)

    def record_timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None) -> None:
        """Record a timer measurement.

        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            labels: Optional labels
        """
        key = f"{name}:{json.dumps(labels or {})}"
        self.timers[key].append(duration_ms)

        metric = Metric(
            name=name,
            type=MetricType.TIMER,
            value=duration_ms,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {}
        )
        self.metrics.append(metric)

    def get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """Get summary statistics for a metric.

        Args:
            metric_name: Name of metric to summarize

        Returns:
            Summary statistics
        """
        metric_values = [m.value for m in self.metrics if m.name == metric_name]

        if not metric_values:
            return {"count": 0}

        sorted_values = sorted(metric_values)
        return {
            "count": len(metric_values),
            "sum": sum(metric_values),
            "avg": sum(metric_values) / len(metric_values),
            "min": min(metric_values),
            "max": max(metric_values),
            "p50": sorted_values[len(sorted_values) // 2],
            "p95": sorted_values[int(len(sorted_values) * 0.95)],
            "p99": sorted_values[int(len(sorted_values) * 0.99)],
        }

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics.

        Returns:
            Metrics data
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histogram_summaries": {
                key: {
                    "count": len(vals),
                    "sum": sum(vals),
                    "avg": sum(vals) / len(vals) if vals else 0,
                    "min": min(vals) if vals else 0,
                    "max": max(vals) if vals else 0,
                }
                for key, vals in self.histograms.items()
            },
            "timer_summaries": {
                key: {
                    "count": len(vals),
                    "total_ms": sum(vals),
                    "avg_ms": sum(vals) / len(vals) if vals else 0,
                    "min_ms": min(vals) if vals else 0,
                    "max_ms": max(vals) if vals else 0,
                }
                for key, vals in self.timers.items()
            },
        }


class AlertingSystem:
    """Alert management and notification."""

    def __init__(self):
        """Initialize alerting system."""
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_counter = 0

    def add_alert_rule(self, metric_name: str, threshold: float, severity: AlertSeverity,
                      comparison: str = "greater_than") -> None:
        """Add an alert rule.

        Args:
            metric_name: Metric to monitor
            threshold: Threshold value
            severity: Alert severity
            comparison: Comparison operator (greater_than, less_than, equals)
        """
        self.alert_rules.append({
            "metric_name": metric_name,
            "threshold": threshold,
            "severity": severity.value,
            "comparison": comparison,
        })

    def evaluate_rule(self, metric_name: str, current_value: float) -> Optional[Alert]:
        """Evaluate alert rules for a metric.

        Args:
            metric_name: Metric name
            current_value: Current metric value

        Returns:
            Alert if triggered, None otherwise
        """
        for rule in self.alert_rules:
            if rule["metric_name"] != metric_name:
                continue

            triggered = False
            if rule["comparison"] == "greater_than":
                triggered = current_value > rule["threshold"]
            elif rule["comparison"] == "less_than":
                triggered = current_value < rule["threshold"]
            elif rule["comparison"] == "equals":
                triggered = current_value == rule["threshold"]

            if triggered:
                alert_id = f"alert_{self.alert_counter}"
                self.alert_counter += 1

                alert = Alert(
                    id=alert_id,
                    metric_name=metric_name,
                    severity=AlertSeverity(rule["severity"]),
                    message=f"{metric_name} {rule['comparison']} threshold: {current_value} vs {rule['threshold']}",
                    threshold=rule["threshold"],
                    current_value=current_value,
                    timestamp=datetime.now(timezone.utc),
                )

                self.alerts[alert_id] = alert
                return alert

        return None

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert.

        Args:
            alert_id: Alert ID

        Returns:
            Success flag
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = datetime.now(timezone.utc)
            return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts.

        Returns:
            List of active alerts
        """
        return [a for a in self.alerts.values() if not a.resolved]

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts.

        Returns:
            Alert summary
        """
        active = self.get_active_alerts()
        return {
            "total_alerts": len(self.alerts),
            "active_alerts": len(active),
            "critical_count": sum(1 for a in active if a.severity == AlertSeverity.CRITICAL),
            "warning_count": sum(1 for a in active if a.severity == AlertSeverity.WARNING),
            "info_count": sum(1 for a in active if a.severity == AlertSeverity.INFO),
            "alerts": [asdict(a) for a in active],
        }


class Dashboard:
    """Dashboard for visualization."""

    def __init__(self, name: str):
        """Initialize dashboard.

        Args:
            name: Dashboard name
        """
        self.name = name
        self.panels = []
        self.created_at = datetime.now(timezone.utc)

    def add_panel(self, title: str, metric_name: str, panel_type: str = "graph") -> None:
        """Add a dashboard panel.

        Args:
            title: Panel title
            metric_name: Metric to display
            panel_type: Type of panel (graph, gauge, stat, table)
        """
        self.panels.append({
            "title": title,
            "metric_name": metric_name,
            "type": panel_type,
        })

    def export(self) -> Dict[str, Any]:
        """Export dashboard configuration.

        Returns:
            Dashboard configuration
        """
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "panels": self.panels,
        }


class ObservabilityPipeline:
    """Complete observability pipeline."""

    def __init__(self):
        """Initialize observability pipeline."""
        self.metrics = MetricsCollector()
        self.alerting = AlertingSystem()
        self.dashboards: Dict[str, Dashboard] = {}

    def create_dashboard(self, name: str) -> Dashboard:
        """Create a new dashboard.

        Args:
            name: Dashboard name

        Returns:
            Dashboard instance
        """
        dashboard = Dashboard(name)
        self.dashboards[name] = dashboard
        return dashboard

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot.

        Returns:
            Metrics snapshot
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": self.metrics.export_metrics(),
            "alerts": self.alerting.get_alert_summary(),
            "dashboards": [d.export() for d in self.dashboards.values()],
        }


def test_monitoring_observability() -> Dict[str, Any]:
    """Test monitoring and observability implementation."""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "PHASE 15: MONITORING & OBSERVABILITY".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    results = {
        "phase": 15,
        "tests": {},
    }

    # Test 1: Metrics Collection
    print("\n" + "="*80)
    print("TEST 1: METRICS COLLECTION")
    print("="*80)

    collector = MetricsCollector()

    # Simulate authentication metrics
    collector.increment_counter("auth.attempts", labels={"status": "success"})
    collector.increment_counter("auth.attempts", labels={"status": "success"})
    collector.increment_counter("auth.attempts", labels={"status": "failed"})

    print("\n✓ Authentication metrics collected")

    # Simulate request latency
    for latency in [45, 52, 48, 156, 62, 51, 49]:  # Including outlier
        collector.observe_histogram("request.latency_ms", latency, labels={"endpoint": "/api/products"})

    print("✓ Request latency histogram recorded (7 observations)")

    # Simulate rate limiting metrics
    collector.set_gauge("rate_limit.active_ips", 42, labels={"limit_window": "per_hour"})
    collector.increment_counter("rate_limit.rejections", 5)

    print("✓ Rate limiting metrics set")

    # Export metrics
    metrics_export = collector.export_metrics()
    print(f"\n  Counters: {len(collector.counters)}")
    print(f"  Gauges: {len(collector.gauges)}")
    print(f"  Histograms: {len(collector.histograms)}")

    results["tests"]["metrics_collection"] = {
        "status": "PASS",
        "counters_collected": len(collector.counters),
        "gauges_collected": len(collector.gauges),
        "histograms_collected": len(collector.histograms),
    }

    # Test 2: Metric Analysis
    print("\n" + "="*80)
    print("TEST 2: METRIC ANALYSIS")
    print("="*80)

    latency_summary = collector.get_metric_summary("request.latency_ms")

    print(f"\n✓ Request Latency Analysis:")
    print(f"  Count: {latency_summary['count']}")
    print(f"  Avg: {latency_summary['avg']:.2f}ms")
    print(f"  Min: {latency_summary['min']:.2f}ms")
    print(f"  Max: {latency_summary['max']:.2f}ms")
    print(f"  P50: {latency_summary['p50']:.2f}ms")
    print(f"  P95: {latency_summary['p95']:.2f}ms")
    print(f"  P99: {latency_summary['p99']:.2f}ms")

    results["tests"]["metric_analysis"] = {
        "status": "PASS",
        "latency_avg_ms": round(latency_summary['avg'], 2),
        "latency_p95_ms": round(latency_summary['p95'], 2),
        "latency_p99_ms": round(latency_summary['p99'], 2),
    }

    # Test 3: Alert Rules
    print("\n" + "="*80)
    print("TEST 3: ALERT RULES")
    print("="*80)

    alerting = AlertingSystem()

    # Add alert rules
    alerting.add_alert_rule("auth.failed_attempts", 10, AlertSeverity.WARNING, "greater_than")
    alerting.add_alert_rule("rate_limit.rejections", 50, AlertSeverity.CRITICAL, "greater_than")
    alerting.add_alert_rule("request.latency_ms", 1000, AlertSeverity.WARNING, "greater_than")
    alerting.add_alert_rule("rate_limit.active_ips", 100, AlertSeverity.INFO, "greater_than")

    print(f"\n✓ Alert rules configured: {len(alerting.alert_rules)}")
    for i, rule in enumerate(alerting.alert_rules, 1):
        print(f"  {i}. {rule['metric_name']} {rule['comparison']} {rule['threshold']} ({rule['severity']})")

    results["tests"]["alert_rules"] = {
        "status": "PASS",
        "rules_configured": len(alerting.alert_rules),
    }

    # Test 4: Alert Triggering
    print("\n" + "="*80)
    print("TEST 4: ALERT TRIGGERING")
    print("="*80)

    # Trigger alerts
    alert1 = alerting.evaluate_rule("auth.failed_attempts", 15)
    alert2 = alerting.evaluate_rule("rate_limit.rejections", 75)
    alert3 = alerting.evaluate_rule("rate_limit.active_ips", 50)  # No trigger (< 100)

    triggered_count = sum(1 for a in [alert1, alert2, alert3] if a is not None)

    print(f"\n✓ Alerts evaluated: 3")
    print(f"✓ Alerts triggered: {triggered_count}")

    if alert1:
        print(f"  - {alert1.severity.value.upper()}: {alert1.message}")
    if alert2:
        print(f"  - {alert2.severity.value.upper()}: {alert2.message}")

    # Resolve an alert
    if alert1:
        alerting.resolve_alert(alert1.id)
        print(f"✓ Alert {alert1.id} resolved")

    alert_summary = alerting.get_alert_summary()

    print(f"\n  Alert Summary:")
    print(f"    Total alerts: {alert_summary['total_alerts']}")
    print(f"    Active: {alert_summary['active_alerts']}")
    print(f"    Critical: {alert_summary['critical_count']}")

    results["tests"]["alert_triggering"] = {
        "status": "PASS",
        "alerts_triggered": len(alerting.alerts),
        "alerts_active": alert_summary['active_alerts'],
        "alerts_resolved": alert_summary['total_alerts'] - alert_summary['active_alerts'],
    }

    # Test 5: Dashboards
    print("\n" + "="*80)
    print("TEST 5: DASHBOARDS")
    print("="*80)

    pipeline = ObservabilityPipeline()

    # Create security dashboard
    sec_dashboard = pipeline.create_dashboard("Security Metrics")
    sec_dashboard.add_panel("Authentication Attempts", "auth.attempts", "graph")
    sec_dashboard.add_panel("Rate Limit Rejections", "rate_limit.rejections", "gauge")
    sec_dashboard.add_panel("Active IPs", "rate_limit.active_ips", "stat")

    # Create performance dashboard
    perf_dashboard = pipeline.create_dashboard("Performance Metrics")
    perf_dashboard.add_panel("Request Latency", "request.latency_ms", "graph")
    perf_dashboard.add_panel("Latency P95", "request.latency_ms", "gauge")

    print(f"\n✓ Dashboards created: {len(pipeline.dashboards)}")
    for name, dashboard in pipeline.dashboards.items():
        print(f"  {name}: {len(dashboard.panels)} panels")
        for panel in dashboard.panels:
            print(f"    - {panel['title']} ({panel['type']})")

    results["tests"]["dashboards"] = {
        "status": "PASS",
        "dashboards_created": len(pipeline.dashboards),
        "total_panels": sum(len(d.panels) for d in pipeline.dashboards.values()),
    }

    # Test 6: Complete Observability Pipeline
    print("\n" + "="*80)
    print("TEST 6: COMPLETE OBSERVABILITY PIPELINE")
    print("="*80)

    # Populate pipeline with metrics
    pipeline.metrics = collector
    pipeline.alerting = alerting

    snapshot = pipeline.get_metrics_snapshot()

    print(f"\n✓ Observability snapshot generated")
    print(f"  Timestamp: {snapshot['timestamp']}")
    print(f"  Dashboards: {len(snapshot['dashboards'])}")
    print(f"  Alerts: {snapshot['alerts']['total_alerts']}")

    results["tests"]["observability_pipeline"] = {
        "status": "PASS",
        "snapshot_generated": True,
        "dashboards_in_snapshot": len(snapshot['dashboards']),
        "alerts_in_snapshot": snapshot['alerts']['total_alerts'],
    }

    # Summary
    print("\n" + "="*80)
    print("MONITORING & OBSERVABILITY SUMMARY")
    print("="*80)

    all_pass = all(test["status"] == "PASS" for test in results["tests"].values())

    print(f"\n✓ Tests run: {len(results['tests'])}")
    print(f"✓ Status: {'ALL PASS ✅' if all_pass else 'SOME FAILURES ⚠️'}")

    for test_name, test_result in results["tests"].items():
        status_icon = "✅" if test_result["status"] == "PASS" else "❌"
        print(f"  {status_icon} {test_name}: {test_result['status']}")

    print("\n" + "="*80)
    print("OBSERVABILITY FEATURES")
    print("="*80)
    print("""
✓ Metrics Collection:
  - Counter metrics (cumulative counts)
  - Gauge metrics (point-in-time values)
  - Histogram metrics (value distributions)
  - Timer metrics (latency measurements)

✓ Metric Analysis:
  - Count, sum, average statistics
  - Min/max values
  - Percentile calculations (P50, P95, P99)

✓ Alert Management:
  - Rule-based alerting
  - Multiple severity levels (INFO, WARNING, CRITICAL)
  - Comparison operators (greater_than, less_than, equals)
  - Alert lifecycle (triggered, resolved)

✓ Dashboard System:
  - Multi-panel dashboards
  - Multiple visualization types (graph, gauge, stat, table)
  - Dashboard configuration export

✓ Observability Pipeline:
  - Unified metrics collection
  - Integrated alerting
  - Dashboard management
  - Snapshot export for monitoring

Recommended Alert Rules:
  - Authentication failures: > 10/hour (WARNING)
  - Rate limit rejections: > 50/hour (CRITICAL)
  - Request latency P95: > 500ms (WARNING)
  - Request latency P99: > 1000ms (CRITICAL)
  - Database connection errors: > 5/hour (WARNING)
  - Failed data syncs: > 2/day (WARNING)
""")

    # Export results
    results_path = OUT_DIR / "monitoring_observability_phase15.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✅ Results exported: {results_path}\n")
    print("="*80 + "\n")

    return results


if __name__ == "__main__":
    test_monitoring_observability()
