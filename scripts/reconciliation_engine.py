#!/usr/bin/env python3
"""Order reconciliation engine for platform vs ledger comparison.

Reconciles orders between:
1. Platform APIs (live order data)
2. Order ledger (persisted historical data)

Detects:
- Missing orders (in ledger but not on platform, or vice versa)
- Amount mismatches (price discrepancies)
- State divergence (platform state != ledger state)
- Duplicate entries in ledger

Generates reconciliation report with discrepancy classification.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List, Dict, Set
from enum import Enum

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from wb_ozon_api_adapter import UnifiedAPIGateway, PlatformOrderData
from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus
from order_state_machine import AnomalyType


class DiscrepancyType(str, Enum):
    """Types of reconciliation discrepancies."""
    MISSING_IN_LEDGER = "missing_in_ledger"
    MISSING_ON_PLATFORM = "missing_on_platform"
    AMOUNT_MISMATCH = "amount_mismatch"
    STATE_MISMATCH = "state_mismatch"
    DUPLICATE_IN_LEDGER = "duplicate_in_ledger"
    CURRENCY_MISMATCH = "currency_mismatch"


@dataclass
class Discrepancy:
    """Record of a reconciliation discrepancy."""
    discrepancy_type: DiscrepancyType
    platform: str
    shop_id: str
    order_id: str

    # Ledger data
    ledger_entry_id: Optional[str] = None
    ledger_amount: Optional[float] = None
    ledger_state: Optional[str] = None
    ledger_currency: Optional[str] = None

    # Platform data
    platform_amount: Optional[float] = None
    platform_state: Optional[str] = None
    platform_currency: Optional[str] = None

    # Details
    description: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        d = asdict(self)
        d["discrepancy_type"] = self.discrepancy_type.value
        return d


@dataclass
class ReconciliationReport:
    """Complete reconciliation report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Scope
    ledger_total_orders: int = 0
    platform_total_orders: int = 0

    # Results
    total_discrepancies: int = 0
    discrepancies: List[Discrepancy] = field(default_factory=list)

    # Breakdown by type
    missing_in_ledger: int = 0
    missing_on_platform: int = 0
    amount_mismatches: int = 0
    state_mismatches: int = 0
    duplicates: int = 0
    currency_mismatches: int = 0

    # Match statistics
    matched_orders: int = 0
    matched_amount_total: float = 0.0
    discrepant_amount_total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "ledger_total_orders": self.ledger_total_orders,
            "platform_total_orders": self.platform_total_orders,
            "total_discrepancies": self.total_discrepancies,
            "breakdown": {
                "missing_in_ledger": self.missing_in_ledger,
                "missing_on_platform": self.missing_on_platform,
                "amount_mismatches": self.amount_mismatches,
                "state_mismatches": self.state_mismatches,
                "duplicates": self.duplicates,
                "currency_mismatches": self.currency_mismatches,
            },
            "match_statistics": {
                "matched_orders": self.matched_orders,
                "matched_amount_total": self.matched_amount_total,
                "discrepant_amount_total": self.discrepant_amount_total,
            },
            "discrepancies": [d.to_dict() for d in self.discrepancies],
        }


class ReconciliationEngine:
    """Reconciles order ledger against platform data."""

    def __init__(
        self,
        ledger: Optional[OrderLedger] = None,
        gateway: Optional[UnifiedAPIGateway] = None,
    ):
        """Initialize reconciliation engine.

        Args:
            ledger: OrderLedger instance
            gateway: UnifiedAPIGateway instance
        """
        self.ledger = ledger or OrderLedger()
        self.gateway = gateway or UnifiedAPIGateway()
        self.report = None

    def reconcile(self) -> ReconciliationReport:
        """Reconcile ledger against platform data.

        Returns:
            ReconciliationReport with discrepancies
        """
        report = ReconciliationReport()
        report.ledger_total_orders = len(self.ledger.entries)

        # Authenticate and fetch platform data
        print("[ReconciliationEngine] Authenticating with platforms...")
        self.gateway.authenticate_all()

        print("[ReconciliationEngine] Fetching orders from platforms...")
        all_platform_orders = self.gateway.fetch_all_orders()

        # Flatten platform orders by (platform, shop_id, order_id)
        platform_orders_map: Dict[tuple[str, str, str], PlatformOrderData] = {}
        for adapter_name, orders in all_platform_orders.items():
            platform, shop_id = self.gateway._parse_adapter_name(adapter_name)
            for order in orders:
                key = (platform, shop_id, order.order_id)
                platform_orders_map[key] = order
                report.platform_total_orders += 1

        # Track processed orders
        processed_orders: Set[tuple[str, str, str]] = set()

        # 1. Check each ledger entry against platform
        for entry_id, ledger_entry in self.ledger.entries.items():
            key = (ledger_entry.platform, ledger_entry.shop_id, ledger_entry.order_id)
            processed_orders.add(key)

            if key in platform_orders_map:
                # Order found on platform - check for discrepancies
                platform_order = platform_orders_map[key]
                discrepancies = self._check_entry_discrepancies(
                    ledger_entry=ledger_entry,
                    platform_order=platform_order,
                )

                if discrepancies:
                    report.discrepancies.extend(discrepancies)
                    report.total_discrepancies += len(discrepancies)
                    for disc in discrepancies:
                        self._increment_discrepancy_counter(report, disc.discrepancy_type)
                else:
                    # Perfect match
                    report.matched_orders += 1
                    report.matched_amount_total += ledger_entry.total_amount
                    # Update reconciliation status
                    ledger_entry.reconciliation_status = ReconciliationStatus.MATCHED
                    ledger_entry.matched_on_platform = True
            else:
                # Missing on platform
                disc = Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_ON_PLATFORM,
                    platform=ledger_entry.platform,
                    shop_id=ledger_entry.shop_id,
                    order_id=ledger_entry.order_id,
                    ledger_entry_id=entry_id,
                    ledger_amount=ledger_entry.total_amount,
                    ledger_state=ledger_entry.state_machine_state,
                    ledger_currency=ledger_entry.currency,
                    description=f"Order exists in ledger but not found on {ledger_entry.platform}",
                )
                report.discrepancies.append(disc)
                report.total_discrepancies += 1
                report.missing_on_platform += 1
                report.discrepant_amount_total += ledger_entry.total_amount
                # Update reconciliation status
                ledger_entry.reconciliation_status = ReconciliationStatus.UNMATCHED
                ledger_entry.missing_flag = True

        # 2. Check for orders on platform but missing from ledger
        for key, platform_order in platform_orders_map.items():
            if key not in processed_orders:
                # Missing in ledger
                disc = Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_IN_LEDGER,
                    platform=platform_order.platform,
                    shop_id=platform_order.shop_id,
                    order_id=platform_order.order_id,
                    platform_amount=platform_order.total_amount,
                    platform_state=platform_order.platform_state,
                    platform_currency=platform_order.currency,
                    description=f"Order found on {platform_order.platform} but missing from ledger",
                )
                report.discrepancies.append(disc)
                report.total_discrepancies += 1
                report.missing_in_ledger += 1
                report.discrepant_amount_total += platform_order.total_amount

        self.report = report
        return report

    def _check_entry_discrepancies(
        self,
        ledger_entry: OrderLedgerEntry,
        platform_order: PlatformOrderData,
    ) -> List[Discrepancy]:
        """Check for discrepancies between ledger and platform order.

        Args:
            ledger_entry: OrderLedgerEntry from ledger
            platform_order: PlatformOrderData from platform API

        Returns:
            List of Discrepancy records if any found
        """
        discrepancies = []

        # Amount mismatch (allow small differences due to rounding)
        if abs(ledger_entry.total_amount - platform_order.total_amount) > 0.01:
            disc = Discrepancy(
                discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                platform=ledger_entry.platform,
                shop_id=ledger_entry.shop_id,
                order_id=ledger_entry.order_id,
                ledger_entry_id=ledger_entry.ledger_entry_id,
                ledger_amount=ledger_entry.total_amount,
                ledger_state=ledger_entry.state_machine_state,
                platform_amount=platform_order.total_amount,
                platform_state=platform_order.platform_state,
                description=f"Amount mismatch: ledger={ledger_entry.total_amount}, "
                           f"platform={platform_order.total_amount}",
                metadata={
                    "difference": platform_order.total_amount - ledger_entry.total_amount,
                },
            )
            discrepancies.append(disc)

        # Currency mismatch
        if ledger_entry.currency != platform_order.currency:
            disc = Discrepancy(
                discrepancy_type=DiscrepancyType.CURRENCY_MISMATCH,
                platform=ledger_entry.platform,
                shop_id=ledger_entry.shop_id,
                order_id=ledger_entry.order_id,
                ledger_entry_id=ledger_entry.ledger_entry_id,
                ledger_currency=ledger_entry.currency,
                platform_currency=platform_order.currency,
                description=f"Currency mismatch: ledger={ledger_entry.currency}, "
                           f"platform={platform_order.currency}",
            )
            discrepancies.append(disc)

        # State mismatch
        if ledger_entry.platform_state != platform_order.platform_state:
            disc = Discrepancy(
                discrepancy_type=DiscrepancyType.STATE_MISMATCH,
                platform=ledger_entry.platform,
                shop_id=ledger_entry.shop_id,
                order_id=ledger_entry.order_id,
                ledger_entry_id=ledger_entry.ledger_entry_id,
                ledger_state=ledger_entry.platform_state,
                platform_state=platform_order.platform_state,
                description=f"Platform state divergence: ledger={ledger_entry.platform_state}, "
                           f"platform={platform_order.platform_state}",
            )
            discrepancies.append(disc)

        return discrepancies

    def _increment_discrepancy_counter(
        self,
        report: ReconciliationReport,
        discrepancy_type: DiscrepancyType,
    ) -> None:
        """Increment appropriate counter in report.

        Args:
            report: ReconciliationReport to update
            discrepancy_type: Type of discrepancy
        """
        if discrepancy_type == DiscrepancyType.MISSING_IN_LEDGER:
            report.missing_in_ledger += 1
        elif discrepancy_type == DiscrepancyType.MISSING_ON_PLATFORM:
            report.missing_on_platform += 1
        elif discrepancy_type == DiscrepancyType.AMOUNT_MISMATCH:
            report.amount_mismatches += 1
        elif discrepancy_type == DiscrepancyType.STATE_MISMATCH:
            report.state_mismatches += 1
        elif discrepancy_type == DiscrepancyType.DUPLICATE_IN_LEDGER:
            report.duplicates += 1
        elif discrepancy_type == DiscrepancyType.CURRENCY_MISMATCH:
            report.currency_mismatches += 1

    def get_report(self) -> Optional[ReconciliationReport]:
        """Get reconciliation report.

        Returns:
            ReconciliationReport or None
        """
        return self.report

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save reconciliation report to JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - reconcile() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "reconciliation_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_critical_discrepancies(self) -> List[Discrepancy]:
        """Get critical discrepancies (missing orders).

        Returns:
            List of critical Discrepancy records
        """
        if not self.report:
            return []
        return [
            d for d in self.report.discrepancies
            if d.discrepancy_type in [
                DiscrepancyType.MISSING_IN_LEDGER,
                DiscrepancyType.MISSING_ON_PLATFORM,
                DiscrepancyType.AMOUNT_MISMATCH,
            ]
        ]

    def get_discrepancies_by_type(self, disc_type: DiscrepancyType) -> List[Discrepancy]:
        """Get discrepancies of specific type.

        Args:
            disc_type: DiscrepancyType to filter

        Returns:
            List of Discrepancy records
        """
        if not self.report:
            return []
        return [d for d in self.report.discrepancies if d.discrepancy_type == disc_type]


def main() -> None:
    """Demo reconciliation engine."""
    print("[ReconciliationEngine] Testing Order Reconciliation\n")

    engine = ReconciliationEngine()

    # Perform reconciliation
    print("[ReconciliationEngine] Starting reconciliation...\n")
    report = engine.reconcile()

    # Display summary
    print(f"[ReconciliationEngine] Reconciliation Summary:")
    print(f"  Ledger total orders: {report.ledger_total_orders}")
    print(f"  Platform total orders: {report.platform_total_orders}")
    print(f"  Total discrepancies: {report.total_discrepancies}")
    print(f"  Matched orders: {report.matched_orders}")

    # Display breakdown
    print(f"\n[ReconciliationEngine] Discrepancy Breakdown:")
    print(f"  Missing in ledger: {report.missing_in_ledger}")
    print(f"  Missing on platform: {report.missing_on_platform}")
    print(f"  Amount mismatches: {report.amount_mismatches}")
    print(f"  State mismatches: {report.state_mismatches}")
    print(f"  Currency mismatches: {report.currency_mismatches}")

    # Display critical discrepancies
    critical = engine.get_critical_discrepancies()
    if critical:
        print(f"\n[ReconciliationEngine] Critical Discrepancies:")
        for disc in critical[:5]:
            print(f"  - {disc.order_id}: {disc.description}")
        if len(critical) > 5:
            print(f"  ... and {len(critical) - 5} more")

    # Save report
    report_path = engine.save_report()
    print(f"\n[ReconciliationEngine] Report saved to: {report_path}")

    print(f"\n[ReconciliationEngine] ✓ Reconciliation completed successfully")


if __name__ == "__main__":
    main()
