#!/usr/bin/env python3
"""Advanced real-time dashboard for order management system.

Displays:
1. Live order processing metrics
2. Recovery status and success rates
3. SLA compliance trends
4. Anomaly detection summary
5. Shop performance ranking
6. Alert dispatch status
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger
from order_analytics import OrderAnalytics
from sla_compliance import SLACompliance
from order_anomaly_detector import OrderAnomalyDetector
from predictive_alerting import PredictiveAlerting
from order_recovery_engine import OrderRecoveryEngine


class AdvancedDashboard:
    """Advanced real-time monitoring dashboard."""

    def __init__(self):
        """Initialize dashboard."""
        self.ledger = OrderLedger()
        self.analytics = OrderAnalytics(self.ledger)
        self.sla = SLACompliance(self.ledger)
        self.anomalies = OrderAnomalyDetector(self.ledger)
        self.predictor = PredictiveAlerting(self.ledger)
        self.recovery = OrderRecoveryEngine(self.ledger)

    def render_full_dashboard(self) -> str:
        """Render complete dashboard.

        Returns:
            Formatted dashboard string
        """
        output = []
        output.append("\n" + "=" * 100)
        output.append("ADVANCED ORDER MANAGEMENT DASHBOARD".center(100))
        output.append("=" * 100)
        output.append(f"Generated: {datetime.now(timezone.utc).isoformat()[:19]}Z\n")

        # Section 1: Pipeline Overview
        output.extend(self._render_pipeline_overview())

        # Section 2: Performance Metrics
        output.extend(self._render_performance_metrics())

        # Section 3: SLA Compliance
        output.extend(self._render_sla_section())

        # Section 4: Recovery & Operations
        output.extend(self._render_recovery_section())

        # Section 5: Risk Assessment
        output.extend(self._render_risk_section())

        # Section 6: Shop Rankings
        output.extend(self._render_shop_rankings())

        output.append("=" * 100 + "\n")

        return "\n".join(output)

    def _render_pipeline_overview(self) -> list[str]:
        """Render pipeline overview section."""
        output = ["📊 PIPELINE OVERVIEW"]
        output.append("-" * 100)

        total_orders = len(self.ledger.entries)

        matched = sum(1 for e in self.ledger.entries.values() if e.matched_on_platform)
        unmatched = sum(1 for e in self.ledger.entries.values() if not e.matched_on_platform)
        confirmed = sum(1 for e in self.ledger.entries.values() if e.state_machine_state == "confirmed")

        output.append(f"  Total Orders: {total_orders}")
        matched_pct = (matched/total_orders*100) if total_orders > 0 else 0
        unmatched_pct = (unmatched/total_orders*100) if total_orders > 0 else 0
        confirmed_pct = (confirmed/total_orders*100) if total_orders > 0 else 0
        output.append(f"  ✓ Matched:     {matched:>3} ({matched_pct:.0f}%)")
        output.append(f"  ✗ Unmatched:   {unmatched:>3} ({unmatched_pct:.0f}%)")
        output.append(f"  ✅ Confirmed:  {confirmed:>3} ({confirmed_pct:.0f}%)")
        output.append("")

        return output

    def _render_performance_metrics(self) -> list[str]:
        """Render performance metrics."""
        output = ["⚡ PERFORMANCE METRICS"]
        output.append("-" * 100)

        trends = self.analytics.analyze_trends(days=30)
        velocity = self.analytics.get_velocity_metrics()

        output.append(f"  Processing Velocity:")
        output.append(f"    Orders/day avg:    {trends.orders_per_day_avg:>6.1f}")
        output.append(f"    Orders/day range:  {velocity.get('orders_per_day_min', 0)}-{velocity.get('orders_per_day_max', 0)}")
        output.append(f"    Revenue/day avg:   {velocity.get('revenue_per_day_avg', 0):>6.2f} RUB")
        output.append("")
        output.append(f"  Anomaly Analysis:")
        output.append(f"    Total anomalies:   {trends.total_anomalies:>3}")
        output.append(f"    Anomaly rate:      {trends.anomaly_rate_pct:>6.1f}%")
        output.append(f"    Avg per day:       {trends.anomalies_per_day_avg:>6.1f}")
        output.append("")

        return output

    def _render_sla_section(self) -> list[str]:
        """Render SLA compliance section."""
        output = ["📋 SLA COMPLIANCE"]
        output.append("-" * 100)

        sla_report = self.sla.check_compliance(days=30)

        output.append(f"  Overall Compliance: {sla_report.overall_compliance_pct:.1f}%")
        output.append(f"  Total Violations:   {sla_report.total_violations}")
        output.append("")
        output.append(f"  Per-SLA Breakdown:")

        for metric in sla_report.sla_metrics:
            bar_len = int(metric.compliance_pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            output.append(f"    {metric.sla_type.value:20} {bar} {metric.compliance_pct:.1f}%")

        output.append("")
        return output

    def _render_recovery_section(self) -> list[str]:
        """Render recovery and operations section."""
        output = ["🔧 RECOVERY & OPERATIONS"]
        output.append("-" * 100)

        recovery_report = self.recovery.execute_recovery()

        output.append(f"  Recovery Status:")
        output.append(f"    Candidates found:      {recovery_report.metrics.total_candidates:>3}")
        output.append(f"    Successful recoveries: {recovery_report.metrics.recovery_successful:>3}")
        output.append(f"    Escalated to ops:      {recovery_report.metrics.escalated_operations:>3}")
        output.append(f"    Escalated to customer: {recovery_report.metrics.escalated_customer:>3}")
        output.append(f"    Manual review flagged: {recovery_report.metrics.manual_review_flagged:>3}")
        output.append("")

        return output

    def _render_risk_section(self) -> list[str]:
        """Render risk assessment section."""
        output = ["⚠️  RISK ASSESSMENT"]
        output.append("-" * 100)

        pred_report = self.predictor.analyze_predictions()
        anomaly_report = self.anomalies.detect_anomalies()

        output.append(f"  Predictive Analysis:")
        output.append(f"    Total predictions:  {pred_report.total_predictions:>3}")
        output.append(f"    High risk (>75%):   {pred_report.high_risk_count:>3} 🔴")
        output.append(f"    Medium risk (50-75%): {pred_report.medium_risk_count:>3} 🟡")
        output.append(f"    Low risk (<50%):    {pred_report.low_risk_count:>3} 🟢")
        output.append("")
        output.append(f"  Anomaly Summary:")
        output.append(f"    P0 (Immediate):     {anomaly_report.p0_immediate:>3}")
        output.append(f"    P1 (Hourly):        {anomaly_report.p1_hourly:>3}")
        output.append(f"    P2 (Daily):         {anomaly_report.p2_daily:>3}")
        output.append("")

        return output

    def _render_shop_rankings(self) -> list[str]:
        """Render shop performance rankings."""
        output = ["🏆 TOP SHOPS BY REVENUE"]
        output.append("-" * 100)

        top_shops = self.analytics.get_top_shops(limit=5)

        if top_shops:
            output.append(f"  {'Rank':<6} {'Shop ID':<15} {'Platform':<10} {'Orders':<10} {'Revenue':<15}")
            output.append(f"  {'-'*6} {'-'*15} {'-'*10} {'-'*10} {'-'*15}")
            for i, shop in enumerate(top_shops, 1):
                output.append(
                    f"  {i:<6} {shop['shop_id']:<15} {shop['platform']:<10} "
                    f"{shop['orders']:<10} {shop['revenue']:>13.2f} RUB"
                )
        else:
            output.append("  No shop data available")

        output.append("")
        return output

    def save_dashboard_state(self, output_path: Optional[Path] = None) -> Path:
        """Save dashboard state as JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not output_path:
            output_path = ROOT / "outputs" / "advanced_dashboard_state.json"

        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline": {
                "total_orders": len(self.ledger.entries),
                "matched": sum(1 for e in self.ledger.entries.values() if e.matched_on_platform),
            },
            "trends": self.analytics.analyze_trends(days=30).to_dict(),
            "sla": self.sla.check_compliance(days=30).to_dict(),
            "recovery": self.recovery.execute_recovery().to_dict(),
            "predictions": self.predictor.analyze_predictions().to_dict(),
            "anomalies": self.anomalies.detect_anomalies().to_dict(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

        return output_path


def main() -> None:
    """Display advanced dashboard."""
    dashboard = AdvancedDashboard()
    output = dashboard.render_full_dashboard()
    print(output)
    dashboard.save_dashboard_state()
    print(f"✓ Dashboard state saved to outputs/advanced_dashboard_state.json")


if __name__ == "__main__":
    main()
