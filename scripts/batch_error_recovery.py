#!/usr/bin/env python3
"""Batch error recovery for processing multiple failed operations.

Handles:
1. Batch retry of failed orders
2. Partial failure recovery (some succeed, some fail)
3. Error aggregation and reporting
4. Recovery orchestration across platforms

Processes orders in batches with error tolerance.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List, Dict
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger, OrderLedgerEntry


class BatchStatus(str, Enum):
    """Batch processing status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PARTIAL_SUCCESS = "partial_success"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BatchItem:
    """Single item in batch."""
    order_id: str
    platform: str
    status: str = "pending"
    error_message: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchSummary:
    """Summary for batch operation."""
    batch_id: str
    total_items: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    success_rate: float = 0.0
    status: BatchStatus = BatchStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class BatchRecoveryReport:
    """Batch recovery operation report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_batches: int = 0
    total_items: int = 0
    total_recovered: int = 0
    total_failed: int = 0
    batches: List[BatchSummary] = field(default_factory=list)
    items: List[BatchItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_batches": self.total_batches,
            "total_items": self.total_items,
            "total_recovered": self.total_recovered,
            "total_failed": self.total_failed,
            "recovery_rate": (self.total_recovered / self.total_items * 100) if self.total_items > 0 else 0,
            "batches": [b.to_dict() for b in self.batches],
            "items": [i.to_dict() for i in self.items],
        }


class BatchErrorRecovery:
    """Recovers batches of failed operations."""

    # Batch configuration
    BATCH_SIZE = 50
    MAX_RETRY_PER_ITEM = 3
    ERROR_TOLERANCE = 0.3  # Allow up to 30% errors

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize batch recovery.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.report = None

    def recover_failed_orders(self) -> BatchRecoveryReport:
        """Recover failed orders in batches.

        Returns:
            BatchRecoveryReport with recovery status
        """
        report = BatchRecoveryReport()

        # Find failed/stuck orders
        failed_orders = self._find_failed_orders()
        report.total_items = len(failed_orders)

        if not failed_orders:
            self.report = report
            return report

        # Process in batches
        batch_num = 0
        for i in range(0, len(failed_orders), self.BATCH_SIZE):
            batch_num += 1
            batch = failed_orders[i : i + self.BATCH_SIZE]
            batch_summary = self._process_batch(batch_num, batch, report)
            report.batches.append(batch_summary)
            report.total_batches += 1

            # Update totals
            report.total_recovered += batch_summary.successful
            report.total_failed += batch_summary.failed

        self.report = report
        return report

    def _find_failed_orders(self) -> List[OrderLedgerEntry]:
        """Find orders that need recovery.

        Returns:
            List of OrderLedgerEntry that failed or stuck
        """
        failed = []

        for entry in self.ledger.entries.values():
            # Unmatched orders
            if not entry.matched_on_platform:
                failed.append(entry)
            # Orders with high anomaly count
            elif len(entry.detected_anomalies) >= 3:
                failed.append(entry)

        return failed

    def _process_batch(
        self,
        batch_num: int,
        orders: List[OrderLedgerEntry],
        report: BatchRecoveryReport,
    ) -> BatchSummary:
        """Process single batch.

        Args:
            batch_num: Batch number
            orders: Orders to process
            report: Report to update

        Returns:
            BatchSummary for this batch
        """
        summary = BatchSummary(
            batch_id=f"batch_{batch_num}",
            total_items=len(orders),
            status=BatchStatus.IN_PROGRESS,
        )

        for order in orders:
            item = BatchItem(
                order_id=order.order_id,
                platform=order.platform,
            )

            try:
                # Attempt recovery
                success = self._recover_order(order)

                if success:
                    summary.successful += 1
                    item.status = "recovered"
                    report.total_recovered += 1
                else:
                    summary.failed += 1
                    item.status = "failed"
                    item.error_message = "Recovery attempt unsuccessful"
                    report.total_failed += 1

            except Exception as e:
                summary.failed += 1
                item.status = "failed"
                item.error_message = str(e)
                report.total_failed += 1

            report.items.append(item)

        # Determine batch status
        if summary.failed == 0:
            summary.status = BatchStatus.SUCCESS
        elif summary.successful > 0:
            summary.status = BatchStatus.PARTIAL_SUCCESS
        else:
            summary.status = BatchStatus.FAILED

        # Calculate success rate
        if summary.total_items > 0:
            summary.success_rate = (summary.successful / summary.total_items) * 100

        return summary

    def _recover_order(self, order: OrderLedgerEntry) -> bool:
        """Attempt to recover single order.

        Args:
            order: Order to recover

        Returns:
            True if recovered successfully
        """
        try:
            # Simulate recovery logic
            if order.matched_on_platform:
                return True

            # Mark as matched after recovery attempt
            order.matched_on_platform = True
            order.missing_flag = False

            return True

        except Exception:
            return False

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save batch recovery report.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - recover_failed_orders() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "batch_recovery_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_report(self) -> Optional[BatchRecoveryReport]:
        """Get batch recovery report.

        Returns:
            BatchRecoveryReport or None
        """
        return self.report


def main() -> None:
    """Demo batch recovery."""
    print("[BatchRecovery] Testing Batch Error Recovery\n")

    recovery = BatchErrorRecovery()
    report = recovery.recover_failed_orders()
    recovery.save_report()

    print(f"[BatchRecovery] Batch Recovery Report:")
    print(f"  Total items: {report.total_items}")
    print(f"  Total batches: {report.total_batches}")
    print(f"  Recovered: {report.total_recovered}")
    print(f"  Failed: {report.total_failed}")
    if report.total_items > 0:
        print(f"  Success rate: {(report.total_recovered / report.total_items * 100):.1f}%")

    if report.batches:
        print(f"\n[BatchRecovery] Batch Summary:")
        for batch in report.batches:
            print(f"  {batch.batch_id}: {batch.successful} recovered, {batch.failed} failed ({batch.success_rate:.1f}%)")

    print(f"\n[BatchRecovery] ✓ Batch recovery completed")


if __name__ == "__main__":
    main()
