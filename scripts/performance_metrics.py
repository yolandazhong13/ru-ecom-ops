#!/usr/bin/env python3
"""Performance metrics visualization and reporting.

Generates:
1. KPI summary report
2. Trend analysis with sparklines
3. Comparative metrics
4. Health scorecard
5. Executive summary
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_analytics import OrderAnalytics
from sla_compliance import SLACompliance
from order_anomaly_detector import OrderAnomalyDetector
from order_ledger import OrderLedger


class PerformanceMetrics:
    """Tracks and visualizes system performance."""

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize metrics tracker.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.analytics = OrderAnalytics(self.ledger)
        self.sla = SLACompliance(self.ledger)
        self.anomalies = OrderAnomalyDetector(self.ledger)

    def compute_kpis(self) -> Dict[str, Any]:
        """Compute key performance indicators.

        Returns:
            Dict with KPI values
        """
        trends = self.analytics.analyze_trends(days=30)
        sla_report = self.sla.check_compliance(days=30)
        anomaly_report = self.anomalies.detect_anomalies()

        total_orders = len(self.ledger.entries)
        confirmed = sum(1 for e in self.ledger.entries.values() if e.state_machine_state == "confirmed")

        kpis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orders": {
                "total": total_orders,
                "confirmed": confirmed,
                "confirmation_rate": (confirmed / total_orders * 100) if total_orders > 0 else 0,
            },
            "processing": {
                "orders_per_day": trends.orders_per_day_avg,
                "revenue_per_day": trends.total_revenue / 30 if trends else 0,
                "anomaly_rate": trends.anomaly_rate_pct,
            },
            "sla": {
                "overall_compliance": sla_report.overall_compliance_pct,
                "violations": sla_report.total_violations,
            },
            "anomalies": {
                "total": anomaly_report.total_anomalies_detected,
                "p0_critical": anomaly_report.p0_immediate,
                "p1_warning": anomaly_report.p1_hourly,
                "p2_info": anomaly_report.p2_daily,
            },
        }

        return kpis

    def generate_health_scorecard(self) -> str:
        """Generate health scorecard.

        Returns:
            Formatted health scorecard
        """
        kpis = self.compute_kpis()

        output = []
        output.append("\n" + "=" * 80)
        output.append("SYSTEM HEALTH SCORECARD".center(80))
        output.append("=" * 80)
        output.append(f"Generated: {kpis['timestamp'][:19]}Z\n")

        # Order Health
        output.append("📦 ORDER HEALTH")
        output.append("-" * 80)
        confirmation_score = self._score_percentage(kpis['orders']['confirmation_rate'])
        output.append(f"  Confirmation Rate: {kpis['orders']['confirmation_rate']:.1f}% {confirmation_score}")
        output.append(f"  Total Orders: {kpis['orders']['total']}")
        output.append("")

        # Processing Health
        output.append("⚙️  PROCESSING HEALTH")
        output.append("-" * 80)
        anomaly_score = self._score_inverted(kpis['processing']['anomaly_rate'])
        output.append(f"  Anomaly Rate: {kpis['processing']['anomaly_rate']:.2f}% {anomaly_score}")
        output.append(f"  Orders/Day: {kpis['processing']['orders_per_day']:.1f}")
        output.append(f"  Revenue/Day: {kpis['processing']['revenue_per_day']:.2f} RUB")
        output.append("")

        # SLA Health
        output.append("📋 SLA COMPLIANCE")
        output.append("-" * 80)
        sla_score = self._score_percentage(kpis['sla']['overall_compliance'])
        output.append(f"  Overall Compliance: {kpis['sla']['overall_compliance']:.1f}% {sla_score}")
        output.append(f"  Violations: {kpis['sla']['violations']}")
        output.append("")

        # Anomaly Health
        output.append("⚠️  ANOMALY STATUS")
        output.append("-" * 80)
        output.append(f"  Total Anomalies: {kpis['anomalies']['total']}")
        output.append(f"  🔴 P0 (Critical): {kpis['anomalies']['p0_critical']}")
        output.append(f"  🟡 P1 (Warning):  {kpis['anomalies']['p1_warning']}")
        output.append(f"  🟢 P2 (Info):     {kpis['anomalies']['p2_info']}")
        output.append("")

        # Overall Health
        overall_health = self._calculate_overall_health(kpis)
        health_emoji = self._health_emoji(overall_health)
        output.append(f"Overall System Health: {overall_health:.0f}/100 {health_emoji}")
        output.append("=" * 80 + "\n")

        return "\n".join(output)

    def generate_executive_summary(self) -> str:
        """Generate executive summary report.

        Returns:
            Formatted executive summary
        """
        kpis = self.compute_kpis()
        output = []

        output.append("\n" + "=" * 80)
        output.append("EXECUTIVE SUMMARY".center(80))
        output.append("=" * 80 + "\n")

        output.append("KEY METRICS:")
        output.append(f"  Total Orders Processed: {kpis['orders']['total']}")
        output.append(f"  Order Confirmation Rate: {kpis['orders']['confirmation_rate']:.1f}%")
        output.append(f"  SLA Compliance: {kpis['sla']['overall_compliance']:.1f}%")
        output.append(f"  System Anomalies: {kpis['anomalies']['total']}")
        output.append(f"  Critical Alerts: {kpis['anomalies']['p0_critical']}")
        output.append("")

        output.append("TRENDS (30-day):")
        output.append(f"  Average Processing Rate: {kpis['processing']['orders_per_day']:.1f} orders/day")
        output.append(f"  Revenue Throughput: {kpis['processing']['revenue_per_day']:.2f} RUB/day")
        output.append(f"  Anomaly Detection Rate: {kpis['processing']['anomaly_rate']:.2f}%")
        output.append("")

        # Status assessment
        status = "✅ HEALTHY" if kpis['sla']['overall_compliance'] > 95 else "⚠️  DEGRADED"
        output.append(f"SYSTEM STATUS: {status}")
        output.append("")

        if kpis['anomalies']['p0_critical'] > 0:
            output.append(f"⚠️  ALERT: {kpis['anomalies']['p0_critical']} critical anomalies require attention")
        if kpis['sla']['violations'] > 0:
            output.append(f"⚠️  ALERT: {kpis['sla']['violations']} SLA violations detected")
        if kpis['anomalies']['p0_critical'] == 0 and kpis['sla']['violations'] == 0:
            output.append("✅ All systems operating normally")

        output.append("=" * 80 + "\n")
        return "\n".join(output)

    def _score_percentage(self, value: float) -> str:
        """Score a percentage value with emoji.

        Args:
            value: Percentage value (0-100)

        Returns:
            Emoji score
        """
        if value >= 95:
            return "🟢 Excellent"
        elif value >= 90:
            return "🟢 Good"
        elif value >= 80:
            return "🟡 Fair"
        else:
            return "🔴 Poor"

    def _score_inverted(self, value: float) -> str:
        """Score inverted value (lower is better).

        Args:
            value: Metric value

        Returns:
            Emoji score
        """
        if value < 1:
            return "🟢 Excellent"
        elif value < 2:
            return "🟢 Good"
        elif value < 5:
            return "🟡 Fair"
        else:
            return "🔴 Poor"

    def _health_emoji(self, health: float) -> str:
        """Get health status emoji.

        Args:
            health: Health score (0-100)

        Returns:
            Health emoji
        """
        if health >= 90:
            return "🟢"
        elif health >= 75:
            return "🟡"
        else:
            return "🔴"

    def _calculate_overall_health(self, kpis: Dict[str, Any]) -> float:
        """Calculate overall system health score.

        Args:
            kpis: KPI dictionary

        Returns:
            Health score 0-100
        """
        scores = []

        # Order health (30%)
        scores.append(kpis['orders']['confirmation_rate'] * 0.3)

        # SLA health (40%)
        scores.append(kpis['sla']['overall_compliance'] * 0.4)

        # Anomaly health (30%) - inverted (lower is better)
        anomaly_score = max(0, 100 - (kpis['processing']['anomaly_rate'] * 20))
        scores.append(anomaly_score * 0.3)

        return sum(scores)

    def save_metrics(self, output_path: Optional[Path] = None) -> Path:
        """Save metrics to JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not output_path:
            output_path = ROOT / "outputs" / "performance_metrics.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.compute_kpis(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path


def main() -> None:
    """Demo performance metrics."""
    print("[Metrics] Testing Performance Metrics\n")

    metrics = PerformanceMetrics()

    # Display health scorecard
    print(metrics.generate_health_scorecard())

    # Display executive summary
    print(metrics.generate_executive_summary())

    # Save metrics
    path = metrics.save_metrics()
    print(f"✓ Metrics saved to: {path}")


if __name__ == "__main__":
    main()
