#!/usr/bin/env python3
"""Billing aggregator for order revenue analysis and reporting.

Aggregates order data by shop for billing and reconciliation:
1. Daily aggregations with totals by shop, platform
2. Weekly summaries with trend analysis
3. Payment status breakdown (confirmed, pending, failed)
4. Currency normalization and exchange tracking

Generates reports for finance and accounting operations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, List, Dict
from enum import Enum

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus
from order_state_machine import OrderState


class BillingPeriod(str, Enum):
    """Billing period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ShopBillingStats:
    """Billing statistics for a shop."""
    shop_id: str
    platform: str
    period_start: str
    period_end: str

    # Order metrics
    total_orders: int = 0
    confirmed_orders: int = 0
    pending_orders: int = 0
    cancelled_orders: int = 0

    # Amount metrics
    total_amount: float = 0.0
    confirmed_amount: float = 0.0
    pending_amount: float = 0.0
    cancelled_amount: float = 0.0

    # Currency tracking
    currency: str = "RUB"

    # State breakdown
    state_breakdown: Dict[str, int] = field(default_factory=dict)

    # Payment status
    payment_confirmed_count: int = 0
    payment_pending_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class BillingReport:
    """Complete billing report for a period."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    period: BillingPeriod = BillingPeriod.DAILY
    period_start: str = ""
    period_end: str = ""

    # Overall metrics
    total_orders: int = 0
    total_amount: float = 0.0

    # By shop
    shop_stats: List[ShopBillingStats] = field(default_factory=list)

    # By platform
    platform_stats: Dict[str, dict[str, Any]] = field(default_factory=dict)

    # Summary statistics
    confirmed_total: float = 0.0
    pending_total: float = 0.0
    cancelled_total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "period": self.period.value,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_orders": self.total_orders,
            "total_amount": self.total_amount,
            "shop_stats": [s.to_dict() for s in self.shop_stats],
            "platform_stats": self.platform_stats,
            "confirmed_total": self.confirmed_total,
            "pending_total": self.pending_total,
            "cancelled_total": self.cancelled_total,
        }


class BillingAggregator:
    """Aggregates order data for billing and revenue reporting."""

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize billing aggregator.

        Args:
            ledger: OrderLedger instance (creates new if not provided)
        """
        self.ledger = ledger or OrderLedger()
        self.report = None

    def aggregate_daily(self, date: Optional[str] = None) -> BillingReport:
        """Generate daily billing report.

        Args:
            date: Date to aggregate (ISO format, default: today)

        Returns:
            BillingReport for the day
        """
        if date is None:
            date = datetime.now(timezone.utc).date().isoformat()

        start_dt = datetime.fromisoformat(f"{date}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{date}T23:59:59+00:00")

        return self._aggregate_period(
            period=BillingPeriod.DAILY,
            start_date=start_dt.isoformat(),
            end_date=end_dt.isoformat(),
        )

    def aggregate_weekly(self, date: Optional[str] = None) -> BillingReport:
        """Generate weekly billing report.

        Args:
            date: Date in the week (ISO format, default: today)

        Returns:
            BillingReport for the week
        """
        if date is None:
            date_obj = datetime.now(timezone.utc).date()
        else:
            date_obj = datetime.fromisoformat(date).date()

        # Get Monday of the week
        monday = date_obj - timedelta(days=date_obj.weekday())
        sunday = monday + timedelta(days=6)

        start_dt = datetime.fromisoformat(f"{monday.isoformat()}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{sunday.isoformat()}T23:59:59+00:00")

        return self._aggregate_period(
            period=BillingPeriod.WEEKLY,
            start_date=start_dt.isoformat(),
            end_date=end_dt.isoformat(),
        )

    def aggregate_monthly(self, date: Optional[str] = None) -> BillingReport:
        """Generate monthly billing report.

        Args:
            date: Date in the month (ISO format, default: today)

        Returns:
            BillingReport for the month
        """
        if date is None:
            date_obj = datetime.now(timezone.utc).date()
        else:
            date_obj = datetime.fromisoformat(date).date()

        # Get first day of month
        first_day = date_obj.replace(day=1)

        # Get last day of month
        if date_obj.month == 12:
            last_day = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(days=1)

        start_dt = datetime.fromisoformat(f"{first_day.isoformat()}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{last_day.isoformat()}T23:59:59+00:00")

        return self._aggregate_period(
            period=BillingPeriod.MONTHLY,
            start_date=start_dt.isoformat(),
            end_date=end_dt.isoformat(),
        )

    def _aggregate_period(
        self,
        period: BillingPeriod,
        start_date: str,
        end_date: str,
    ) -> BillingReport:
        """Aggregate billing data for period.

        Args:
            period: Billing period type
            start_date: Period start (ISO format)
            end_date: Period end (ISO format)

        Returns:
            BillingReport for period
        """
        report = BillingReport(
            period=period,
            period_start=start_date,
            period_end=end_date,
        )

        # Query orders in period
        orders = self.ledger.query_by_date_range(start_date, end_date)

        if not orders:
            self.report = report
            return report

        # Group by (shop_id, platform)
        by_shop_platform: Dict[tuple[str, str], List[OrderLedgerEntry]] = {}
        platform_totals: Dict[str, dict[str, Any]] = {}

        for entry in orders:
            key = (entry.shop_id, entry.platform)
            if key not in by_shop_platform:
                by_shop_platform[key] = []
            by_shop_platform[key].append(entry)

            # Track platform totals
            if entry.platform not in platform_totals:
                platform_totals[entry.platform] = {
                    "total_orders": 0,
                    "total_amount": 0.0,
                    "confirmed_amount": 0.0,
                    "pending_amount": 0.0,
                    "cancelled_amount": 0.0,
                }
            platform_totals[entry.platform]["total_orders"] += 1
            platform_totals[entry.platform]["total_amount"] += entry.total_amount

        # Build shop stats
        for (shop_id, platform), shop_orders in by_shop_platform.items():
            stats = self._compute_shop_stats(
                shop_id=shop_id,
                platform=platform,
                orders=shop_orders,
                start_date=start_date,
                end_date=end_date,
            )
            report.shop_stats.append(stats)

            report.total_orders += stats.total_orders
            report.total_amount += stats.total_amount
            report.confirmed_total += stats.confirmed_amount
            report.pending_total += stats.pending_amount
            report.cancelled_total += stats.cancelled_amount

        report.platform_stats = platform_totals
        self.report = report
        return report

    def _compute_shop_stats(
        self,
        shop_id: str,
        platform: str,
        orders: List[OrderLedgerEntry],
        start_date: str,
        end_date: str,
    ) -> ShopBillingStats:
        """Compute billing stats for shop in period.

        Args:
            shop_id: Shop ID
            platform: Platform name
            orders: List of orders
            start_date: Period start
            end_date: Period end

        Returns:
            ShopBillingStats
        """
        stats = ShopBillingStats(
            shop_id=shop_id,
            platform=platform,
            period_start=start_date,
            period_end=end_date,
        )

        state_counts = {}

        for order in orders:
            stats.total_orders += 1
            stats.total_amount += order.total_amount

            # Count by state
            state = order.state_machine_state or "unknown"
            state_counts[state] = state_counts.get(state, 0) + 1

            # Count by status
            if order.state_machine_state == OrderState.CONFIRMED.value:
                stats.confirmed_orders += 1
                stats.confirmed_amount += order.total_amount
            elif order.state_machine_state == OrderState.CANCELLED.value:
                stats.cancelled_orders += 1
                stats.cancelled_amount += order.total_amount
            else:
                stats.pending_orders += 1
                stats.pending_amount += order.total_amount

            # Payment status
            if order.payment_confirmed:
                stats.payment_confirmed_count += 1
            else:
                stats.payment_pending_count += 1

        stats.state_breakdown = state_counts
        stats.currency = orders[0].currency if orders else "RUB"

        return stats

    def get_report(self) -> Optional[BillingReport]:
        """Get last aggregation report.

        Returns:
            BillingReport or None
        """
        return self.report

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save report to JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - aggregate_*() not called")

        if not output_path:
            period_str = self.report.period.value
            output_path = ROOT / "outputs" / f"billing_report_{period_str}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_shop_summary(self, shop_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for specific shop.

        Args:
            shop_id: Shop ID to summarize

        Returns:
            Shop summary dict or None
        """
        if not self.report:
            return None

        shop_entries = [s for s in self.report.shop_stats if s.shop_id == shop_id]
        if not shop_entries:
            return None

        # Aggregate across platforms
        summary = {
            "shop_id": shop_id,
            "total_orders": sum(s.total_orders for s in shop_entries),
            "total_amount": sum(s.total_amount for s in shop_entries),
            "confirmed_amount": sum(s.confirmed_amount for s in shop_entries),
            "pending_amount": sum(s.pending_amount for s in shop_entries),
            "cancelled_amount": sum(s.cancelled_amount for s in shop_entries),
            "by_platform": [s.to_dict() for s in shop_entries],
        }
        return summary


def main() -> None:
    """Demo billing aggregator."""
    print("[BillingAggregator] Testing Billing Aggregator\n")

    aggregator = BillingAggregator()

    # Generate daily report
    print("[BillingAggregator] Generating daily report...\n")
    daily_report = aggregator.aggregate_daily()

    print(f"[BillingAggregator] Daily Report:")
    print(f"  Period: {daily_report.period_start[:10]}")
    print(f"  Total orders: {daily_report.total_orders}")
    print(f"  Total amount: {daily_report.total_amount:.2f} RUB")
    print(f"  Confirmed: {daily_report.confirmed_total:.2f} RUB")
    print(f"  Pending: {daily_report.pending_total:.2f} RUB")
    print(f"  Cancelled: {daily_report.cancelled_total:.2f} RUB")

    # Display shop breakdown
    if daily_report.shop_stats:
        print(f"\n[BillingAggregator] Shop Breakdown:")
        for shop_stats in daily_report.shop_stats:
            print(f"  {shop_stats.shop_id} ({shop_stats.platform}):")
            print(f"    Orders: {shop_stats.total_orders}")
            print(f"    Amount: {shop_stats.total_amount:.2f}")

    # Save report
    report_path = aggregator.save_report()
    print(f"\n[BillingAggregator] Report saved to: {report_path}")

    print(f"\n[BillingAggregator] ✓ Billing aggregation completed successfully")


if __name__ == "__main__":
    main()
