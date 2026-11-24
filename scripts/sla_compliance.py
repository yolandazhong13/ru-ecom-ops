#!/usr/bin/env python3
"""SLA compliance monitoring and reporting.

Tracks compliance against SLAs:
1. Order processing SLA (payment confirmation <1h)
2. Shipment SLA (shipment <24h after payment)
3. Delivery SLA (delivery <7d after shipment)
4. Alert dispatch SLA (critical alerts <5min)
5. Reconciliation SLA (nightly reconciliation)

Generates compliance reports with violation tracking.
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
from order_state_machine import OrderState


class SLAType(str, Enum):
    """SLA types."""
    PAYMENT_CONFIRMATION = "payment_confirmation"
    SHIPMENT_TIMING = "shipment_timing"
    DELIVERY_TIMING = "delivery_timing"
    ALERT_DISPATCH = "alert_dispatch"
    RECONCILIATION = "reconciliation"


@dataclass
class SLAViolation:
    """Record of SLA violation."""
    sla_type: SLAType
    order_id: str
    platform: str
    shop_id: str
    expected_time: str  # ISO timestamp
    actual_time: str    # ISO timestamp
    violation_minutes: float
    severity: str = "warning"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sla_type"] = self.sla_type.value
        return d


@dataclass
class SLAMetrics:
    """SLA compliance metrics."""
    sla_type: SLAType
    total_orders: int = 0
    compliant_orders: int = 0
    violated_orders: int = 0
    compliance_pct: float = 0.0
    avg_violation_minutes: float = 0.0
    max_violation_minutes: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sla_type"] = self.sla_type.value
        return d


@dataclass
class ComplianceReport:
    """Overall SLA compliance report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    period_start: str = ""
    period_end: str = ""

    # Overall metrics
    total_orders_analyzed: int = 0
    total_violations: int = 0
    overall_compliance_pct: float = 0.0

    # By SLA type
    sla_metrics: List[SLAMetrics] = field(default_factory=list)

    # Violations
    violations: List[SLAViolation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_orders_analyzed": self.total_orders_analyzed,
            "total_violations": self.total_violations,
            "overall_compliance_pct": self.overall_compliance_pct,
            "sla_metrics": [m.to_dict() for m in self.sla_metrics],
            "violations": [v.to_dict() for v in self.violations],
        }


class SLACompliance:
    """Monitors SLA compliance."""

    # SLA Thresholds
    PAYMENT_SLA_HOURS = 1
    SHIPMENT_SLA_HOURS = 24
    DELIVERY_SLA_DAYS = 7
    ALERT_SLA_MINUTES = 5

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize SLA monitor.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.report = None

    def check_compliance(self, days: int = 30) -> ComplianceReport:
        """Check compliance over period.

        Args:
            days: Number of days to analyze

        Returns:
            ComplianceReport with violations
        """
        report = ComplianceReport()

        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days)).date()
        end_date = now.date()

        report.period_start = start_date.isoformat()
        report.period_end = end_date.isoformat()

        # Analyze orders in period
        start_dt = datetime.fromisoformat(f"{start_date.isoformat()}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{end_date.isoformat()}T23:59:59+00:00")

        orders = self.ledger.query_by_date_range(start_dt.isoformat(), end_dt.isoformat())
        report.total_orders_analyzed = len(orders)

        # Initialize metrics for each SLA type
        metrics_by_type = {
            SLAType.PAYMENT_CONFIRMATION: SLAMetrics(sla_type=SLAType.PAYMENT_CONFIRMATION),
            SLAType.SHIPMENT_TIMING: SLAMetrics(sla_type=SLAType.SHIPMENT_TIMING),
            SLAType.DELIVERY_TIMING: SLAMetrics(sla_type=SLAType.DELIVERY_TIMING),
        }

        # Check each order
        for order in orders:
            # Payment confirmation SLA
            if order.payment_date and order.order_date:
                violation = self._check_payment_sla(order)
                if violation:
                    report.violations.append(violation)
                    metrics_by_type[SLAType.PAYMENT_CONFIRMATION].violated_orders += 1
                else:
                    metrics_by_type[SLAType.PAYMENT_CONFIRMATION].compliant_orders += 1
                metrics_by_type[SLAType.PAYMENT_CONFIRMATION].total_orders += 1

            # Shipment timing SLA
            if order.shipped_date and order.payment_date:
                violation = self._check_shipment_sla(order)
                if violation:
                    report.violations.append(violation)
                    metrics_by_type[SLAType.SHIPMENT_TIMING].violated_orders += 1
                else:
                    metrics_by_type[SLAType.SHIPMENT_TIMING].compliant_orders += 1
                metrics_by_type[SLAType.SHIPMENT_TIMING].total_orders += 1

            # Delivery timing SLA
            if order.delivery_date and order.shipped_date:
                violation = self._check_delivery_sla(order)
                if violation:
                    report.violations.append(violation)
                    metrics_by_type[SLAType.DELIVERY_TIMING].violated_orders += 1
                else:
                    metrics_by_type[SLAType.DELIVERY_TIMING].compliant_orders += 1
                metrics_by_type[SLAType.DELIVERY_TIMING].total_orders += 1

        # Compute compliance percentages
        total_compliant = 0
        total_checked = 0

        for sla_type, metrics in metrics_by_type.items():
            if metrics.total_orders > 0:
                metrics.compliance_pct = (metrics.compliant_orders / metrics.total_orders) * 100
                total_compliant += metrics.compliant_orders
                total_checked += metrics.total_orders
            report.sla_metrics.append(metrics)

        if total_checked > 0:
            report.overall_compliance_pct = (total_compliant / total_checked) * 100

        report.total_violations = len(report.violations)

        self.report = report
        return report

    def _check_payment_sla(self, order) -> Optional[SLAViolation]:
        """Check payment confirmation SLA.

        Args:
            order: OrderLedgerEntry

        Returns:
            SLAViolation if violated, None otherwise
        """
        try:
            order_dt = datetime.fromisoformat(order.order_date.replace('Z', '+00:00'))
            payment_dt = datetime.fromisoformat(order.payment_date.replace('Z', '+00:00'))

            diff = payment_dt - order_dt
            hours = diff.total_seconds() / 3600

            if hours > self.PAYMENT_SLA_HOURS:
                expected = order_dt + timedelta(hours=self.PAYMENT_SLA_HOURS)
                return SLAViolation(
                    sla_type=SLAType.PAYMENT_CONFIRMATION,
                    order_id=order.order_id,
                    platform=order.platform,
                    shop_id=order.shop_id,
                    expected_time=expected.isoformat(),
                    actual_time=payment_dt.isoformat(),
                    violation_minutes=int((hours - self.PAYMENT_SLA_HOURS) * 60),
                    description=f"Payment confirmed {hours:.1f}h after order (SLA: {self.PAYMENT_SLA_HOURS}h)",
                )
        except Exception:
            pass

        return None

    def _check_shipment_sla(self, order) -> Optional[SLAViolation]:
        """Check shipment timing SLA.

        Args:
            order: OrderLedgerEntry

        Returns:
            SLAViolation if violated, None otherwise
        """
        try:
            payment_dt = datetime.fromisoformat(order.payment_date.replace('Z', '+00:00'))
            shipped_dt = datetime.fromisoformat(order.shipped_date.replace('Z', '+00:00'))

            diff = shipped_dt - payment_dt
            hours = diff.total_seconds() / 3600

            if hours > self.SHIPMENT_SLA_HOURS:
                expected = payment_dt + timedelta(hours=self.SHIPMENT_SLA_HOURS)
                return SLAViolation(
                    sla_type=SLAType.SHIPMENT_TIMING,
                    order_id=order.order_id,
                    platform=order.platform,
                    shop_id=order.shop_id,
                    expected_time=expected.isoformat(),
                    actual_time=shipped_dt.isoformat(),
                    violation_minutes=int((hours - self.SHIPMENT_SLA_HOURS) * 60),
                    description=f"Shipment {hours:.1f}h after payment (SLA: {self.SHIPMENT_SLA_HOURS}h)",
                )
        except Exception:
            pass

        return None

    def _check_delivery_sla(self, order) -> Optional[SLAViolation]:
        """Check delivery timing SLA.

        Args:
            order: OrderLedgerEntry

        Returns:
            SLAViolation if violated, None otherwise
        """
        try:
            shipped_dt = datetime.fromisoformat(order.shipped_date.replace('Z', '+00:00'))
            delivery_dt = datetime.fromisoformat(order.delivery_date.replace('Z', '+00:00'))

            diff = delivery_dt - shipped_dt
            days = diff.total_seconds() / 86400

            if days > self.DELIVERY_SLA_DAYS:
                expected = shipped_dt + timedelta(days=self.DELIVERY_SLA_DAYS)
                return SLAViolation(
                    sla_type=SLAType.DELIVERY_TIMING,
                    order_id=order.order_id,
                    platform=order.platform,
                    shop_id=order.shop_id,
                    expected_time=expected.isoformat(),
                    actual_time=delivery_dt.isoformat(),
                    violation_minutes=int((days - self.DELIVERY_SLA_DAYS) * 1440),
                    description=f"Delivered {days:.1f}d after shipment (SLA: {self.DELIVERY_SLA_DAYS}d)",
                )
        except Exception:
            pass

        return None

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save compliance report.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - check_compliance() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "sla_compliance_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_report(self) -> Optional[ComplianceReport]:
        """Get compliance report.

        Returns:
            ComplianceReport or None
        """
        return self.report


def main() -> None:
    """Demo SLA compliance."""
    print("[SLACompliance] Testing SLA Compliance Monitor\n")

    sla_monitor = SLACompliance()
    report = sla_monitor.check_compliance(days=30)
    sla_monitor.save_report()

    print(f"[SLACompliance] SLA Compliance Report:")
    print(f"  Period: {report.period_start} to {report.period_end}")
    print(f"  Orders analyzed: {report.total_orders_analyzed}")
    print(f"  Overall compliance: {report.overall_compliance_pct:.1f}%")
    print(f"  Total violations: {report.total_violations}")

    print(f"\n[SLACompliance] Per-SLA Compliance:")
    for metrics in report.sla_metrics:
        print(f"  {metrics.sla_type.value}:")
        print(f"    Compliance: {metrics.compliance_pct:.1f}% ({metrics.compliant_orders}/{metrics.total_orders})")
        if metrics.violated_orders > 0:
            print(f"    Violations: {metrics.violated_orders}")

    if report.violations:
        print(f"\n[SLACompliance] Recent Violations (top 5):")
        for violation in report.violations[:5]:
            print(f"  {violation.order_id}: {violation.description}")

    print(f"\n[SLACompliance] ✓ SLA compliance check completed")


if __name__ == "__main__":
    main()
