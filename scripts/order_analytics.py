#!/usr/bin/env python3
"""Order processing analytics and historical trend analysis.

Tracks metrics over time:
1. Order processing velocity (orders/hour, orders/day)
2. Anomaly trends (baseline vs current)
3. Alert frequency trends
4. Reconciliation health over time
5. Revenue trends by shop

Generates time-series reports for trend analysis and forecasting.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, List, Dict
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger
from order_state_machine import SeverityLevel


@dataclass
class DailyMetrics:
    """Daily aggregated metrics."""
    date: str
    orders_processed: int = 0
    anomalies_detected: int = 0
    p0_count: int = 0
    p1_count: int = 0
    p2_count: int = 0
    alerts_dispatched: int = 0
    discrepancies_found: int = 0
    revenue_total: float = 0.0
    confirmed_revenue: float = 0.0
    matched_orders: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrendReport:
    """Historical trend analysis report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    period_days: int = 30
    start_date: str = ""
    end_date: str = ""

    # Daily metrics history
    daily_metrics: List[DailyMetrics] = field(default_factory=list)

    # Aggregated statistics
    total_orders: int = 0
    total_anomalies: int = 0
    total_revenue: float = 0.0

    # Trends
    orders_per_day_avg: float = 0.0
    anomalies_per_day_avg: float = 0.0
    anomaly_rate_pct: float = 0.0

    # SLA metrics
    p0_anomalies_total: int = 0
    p1_anomalies_total: int = 0
    alerts_dispatched_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "period_days": self.period_days,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "daily_metrics": [m.to_dict() for m in self.daily_metrics],
            "aggregated": {
                "total_orders": self.total_orders,
                "total_anomalies": self.total_anomalies,
                "total_revenue": self.total_revenue,
                "orders_per_day_avg": self.orders_per_day_avg,
                "anomalies_per_day_avg": self.anomalies_per_day_avg,
                "anomaly_rate_pct": self.anomaly_rate_pct,
                "p0_anomalies_total": self.p0_anomalies_total,
                "p1_anomalies_total": self.p1_anomalies_total,
                "alerts_dispatched_total": self.alerts_dispatched_total,
            },
        }


class OrderAnalytics:
    """Analyzes historical trends in order processing."""

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize analytics engine.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.report = None

    def analyze_trends(self, days: int = 30) -> TrendReport:
        """Analyze trends over period.

        Args:
            days: Number of days to analyze

        Returns:
            TrendReport with historical metrics
        """
        report = TrendReport(period_days=days)

        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days)).date()
        end_date = now.date()

        report.start_date = start_date.isoformat()
        report.end_date = end_date.isoformat()

        # Generate metrics for each day
        current_date = start_date
        while current_date <= end_date:
            daily_metrics = self._compute_daily_metrics(current_date)
            report.daily_metrics.append(daily_metrics)
            current_date += timedelta(days=1)

        # Compute aggregates
        if report.daily_metrics:
            report.total_orders = sum(m.orders_processed for m in report.daily_metrics)
            report.total_anomalies = sum(m.anomalies_detected for m in report.daily_metrics)
            report.total_revenue = sum(m.revenue_total for m in report.daily_metrics)
            report.p0_anomalies_total = sum(m.p0_count for m in report.daily_metrics)
            report.p1_anomalies_total = sum(m.p1_count for m in report.daily_metrics)
            report.alerts_dispatched_total = sum(m.alerts_dispatched for m in report.daily_metrics)

            report.orders_per_day_avg = report.total_orders / len(report.daily_metrics) if report.daily_metrics else 0
            report.anomalies_per_day_avg = report.total_anomalies / len(report.daily_metrics) if report.daily_metrics else 0
            report.anomaly_rate_pct = (report.total_anomalies / report.total_orders * 100) if report.total_orders > 0 else 0

        self.report = report
        return report

    def _compute_daily_metrics(self, date: Any) -> DailyMetrics:
        """Compute metrics for a specific day.

        Args:
            date: Date to analyze (date or str)

        Returns:
            DailyMetrics for that day
        """
        if isinstance(date, str):
            date = datetime.fromisoformat(date).date()

        metrics = DailyMetrics(date=date.isoformat())

        # Query orders from that day
        start_dt = datetime.fromisoformat(f"{date.isoformat()}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{date.isoformat()}T23:59:59+00:00")

        orders = self.ledger.query_by_date_range(start_dt.isoformat(), end_dt.isoformat())

        for order in orders:
            metrics.orders_processed += 1
            metrics.revenue_total += order.total_amount

            if order.state_machine_state == "confirmed":
                metrics.confirmed_revenue += order.total_amount
                metrics.matched_orders += 1

        return metrics

    def get_velocity_metrics(self) -> Dict[str, Any]:
        """Get processing velocity metrics.

        Returns:
            Dict with velocity statistics
        """
        if not self.report or not self.report.daily_metrics:
            return {}

        metrics = self.report.daily_metrics

        return {
            "orders_per_day_avg": self.report.orders_per_day_avg,
            "orders_per_day_min": min(m.orders_processed for m in metrics),
            "orders_per_day_max": max(m.orders_processed for m in metrics),
            "anomalies_per_day_avg": self.report.anomalies_per_day_avg,
            "anomaly_rate_pct": self.report.anomaly_rate_pct,
            "revenue_per_day_avg": self.report.total_revenue / len(metrics) if metrics else 0,
        }

    def get_top_shops(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top shops by revenue.

        Args:
            limit: Number of shops to return

        Returns:
            List of shop stats
        """
        if not self.ledger.entries:
            return []

        shop_stats = {}
        for entry in self.ledger.entries.values():
            key = f"{entry.shop_id}_{entry.platform}"
            if key not in shop_stats:
                shop_stats[key] = {
                    "shop_id": entry.shop_id,
                    "platform": entry.platform,
                    "orders": 0,
                    "revenue": 0.0,
                }
            shop_stats[key]["orders"] += 1
            shop_stats[key]["revenue"] += entry.total_amount

        # Sort by revenue
        sorted_shops = sorted(shop_stats.values(), key=lambda x: x["revenue"], reverse=True)
        return sorted_shops[:limit]

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save trend report.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - analyze_trends() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "trend_analysis_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_report(self) -> Optional[TrendReport]:
        """Get trend report.

        Returns:
            TrendReport or None
        """
        return self.report


def main() -> None:
    """Demo analytics."""
    print("[OrderAnalytics] Testing Order Analytics\n")

    analytics = OrderAnalytics()
    report = analytics.analyze_trends(days=30)
    analytics.save_report()

    print(f"[OrderAnalytics] Trend Analysis (30 days):")
    print(f"  Period: {report.start_date} to {report.end_date}")
    print(f"  Total orders: {report.total_orders}")
    print(f"  Total anomalies: {report.total_anomalies}")
    print(f"  Orders/day avg: {report.orders_per_day_avg:.1f}")
    print(f"  Anomaly rate: {report.anomaly_rate_pct:.1f}%")
    print(f"  Total revenue: {report.total_revenue:.2f} RUB")

    # Velocity metrics
    velocity = analytics.get_velocity_metrics()
    if velocity:
        print(f"\n[OrderAnalytics] Velocity Metrics:")
        print(f"  Orders/day avg: {velocity['orders_per_day_avg']:.1f}")
        print(f"  Orders/day range: {velocity['orders_per_day_min']}-{velocity['orders_per_day_max']}")
        print(f"  Revenue/day avg: {velocity['revenue_per_day_avg']:.2f}")

    # Top shops
    top_shops = analytics.get_top_shops(limit=5)
    if top_shops:
        print(f"\n[OrderAnalytics] Top Shops by Revenue:")
        for i, shop in enumerate(top_shops, 1):
            print(f"  {i}. {shop['shop_id']} ({shop['platform']}): {shop['revenue']:.2f} RUB ({shop['orders']} orders)")

    print(f"\n[OrderAnalytics] ✓ Analytics completed")


if __name__ == "__main__":
    main()
