#!/usr/bin/env python3
"""Order anomaly detection and analysis engine.

Analyzes orders in the ledger for:
1. Timing anomalies (payment overdue, shipment delayed, delivery delayed)
2. State transition anomalies (unexpected cancellation/refusal/return)
3. Data anomalies (missing order ID, invalid amount, missing SKU)
4. Reconciliation anomalies (missing orders, amount mismatches)

Generates detailed anomaly reports with severity classification.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, List
from enum import Enum

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_state_machine import AnomalyType, SeverityLevel, OrderState, VALID_TRANSITIONS
from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus


class AnomalyCategory(str, Enum):
    """Anomaly categories for classification."""
    TIMING = "timing"
    STATE_TRANSITION = "state_transition"
    DATA_QUALITY = "data_quality"
    RECONCILIATION = "reconciliation"


@dataclass
class AnomalyRecord:
    """Record of a detected anomaly."""
    ledger_entry_id: str
    order_id: str
    platform: str
    shop_id: str
    anomaly_type: AnomalyType
    category: AnomalyCategory
    severity: SeverityLevel
    description: str
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    order_date: Optional[str] = None
    current_state: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        d = asdict(self)
        d["anomaly_type"] = self.anomaly_type.value
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        return d


@dataclass
class AnomalyDetectionResult:
    """Result of anomaly detection run."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_orders_analyzed: int = 0
    orders_with_anomalies: int = 0
    total_anomalies_detected: int = 0
    anomalies: List[AnomalyRecord] = field(default_factory=list)

    # Breakdown by severity
    p0_immediate: int = 0
    p1_hourly: int = 0
    p2_daily: int = 0

    # Breakdown by category
    timing_anomalies: int = 0
    state_transition_anomalies: int = 0
    data_quality_anomalies: int = 0
    reconciliation_anomalies: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "total_orders_analyzed": self.total_orders_analyzed,
            "orders_with_anomalies": self.orders_with_anomalies,
            "total_anomalies_detected": self.total_anomalies_detected,
            "severity_breakdown": {
                "p0_immediate": self.p0_immediate,
                "p1_hourly": self.p1_hourly,
                "p2_daily": self.p2_daily,
            },
            "category_breakdown": {
                "timing_anomalies": self.timing_anomalies,
                "state_transition_anomalies": self.state_transition_anomalies,
                "data_quality_anomalies": self.data_quality_anomalies,
                "reconciliation_anomalies": self.reconciliation_anomalies,
            },
            "anomalies": [a.to_dict() for a in self.anomalies],
        }


class OrderAnomalyDetector:
    """Detects and classifies anomalies in order ledger."""

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize anomaly detector.

        Args:
            ledger: OrderLedger instance (creates new if not provided)
        """
        self.ledger = ledger or OrderLedger()
        self.result = None

    def detect_anomalies(self) -> AnomalyDetectionResult:
        """Analyze all orders in ledger for anomalies.

        Returns:
            AnomalyDetectionResult with detailed anomaly records
        """
        result = AnomalyDetectionResult()
        result.total_orders_analyzed = len(self.ledger.entries)

        anomalies_by_order = {}

        # Analyze each order
        for entry_id, entry in self.ledger.entries.items():
            detected = self._analyze_order(entry)

            if detected:
                anomalies_by_order[entry_id] = detected
                result.orders_with_anomalies += 1

                for anomaly_record in detected:
                    result.anomalies.append(anomaly_record)
                    result.total_anomalies_detected += 1

                    # Increment severity counters
                    if anomaly_record.severity == SeverityLevel.P0_IMMEDIATE:
                        result.p0_immediate += 1
                    elif anomaly_record.severity == SeverityLevel.P1_HOURLY:
                        result.p1_hourly += 1
                    elif anomaly_record.severity == SeverityLevel.P2_DAILY:
                        result.p2_daily += 1

                    # Increment category counters
                    if anomaly_record.category == AnomalyCategory.TIMING:
                        result.timing_anomalies += 1
                    elif anomaly_record.category == AnomalyCategory.STATE_TRANSITION:
                        result.state_transition_anomalies += 1
                    elif anomaly_record.category == AnomalyCategory.DATA_QUALITY:
                        result.data_quality_anomalies += 1
                    elif anomaly_record.category == AnomalyCategory.RECONCILIATION:
                        result.reconciliation_anomalies += 1

        # Sort anomalies by severity
        result.anomalies.sort(
            key=lambda a: (
                0 if a.severity == SeverityLevel.P0_IMMEDIATE else
                1 if a.severity == SeverityLevel.P1_HOURLY else 2
            )
        )

        self.result = result
        return result

    def _analyze_order(self, entry: OrderLedgerEntry) -> Optional[List[AnomalyRecord]]:
        """Analyze single order for anomalies.

        Args:
            entry: OrderLedgerEntry to analyze

        Returns:
            List of AnomalyRecord if anomalies found, None otherwise
        """
        anomalies = []
        now = datetime.now(timezone.utc)

        # 1. Data Quality Anomalies
        if not entry.order_id or not entry.order_id.strip():
            anomalies.append(self._create_anomaly_record(
                entry=entry,
                anomaly_type=AnomalyType.MISSING_ORDER,
                category=AnomalyCategory.DATA_QUALITY,
                severity=SeverityLevel.P0_IMMEDIATE,
                description="Order ID is missing or empty",
            ))

        if entry.total_amount <= 0:
            anomalies.append(self._create_anomaly_record(
                entry=entry,
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                category=AnomalyCategory.DATA_QUALITY,
                severity=SeverityLevel.P1_HOURLY,
                description=f"Invalid total amount: {entry.total_amount}",
            ))

        if not entry.sku and not entry.items:
            anomalies.append(self._create_anomaly_record(
                entry=entry,
                anomaly_type=AnomalyType.SKU_MISMATCH,
                category=AnomalyCategory.DATA_QUALITY,
                severity=SeverityLevel.P1_HOURLY,
                description="Missing both SKU and items",
            ))

        # 2. Timing Anomalies
        if entry.order_date:
            try:
                order_date = datetime.fromisoformat(entry.order_date.replace('Z', '+00:00'))
                time_diff = now - order_date

                # Payment overdue (pending payment for >1 hour)
                if entry.state_machine_state == OrderState.PENDING_PAYMENT.value:
                    if time_diff.total_seconds() > 3600:
                        anomalies.append(self._create_anomaly_record(
                            entry=entry,
                            anomaly_type=AnomalyType.PAYMENT_OVERDUE,
                            category=AnomalyCategory.TIMING,
                            severity=SeverityLevel.P0_IMMEDIATE,
                            description=f"Payment pending for {time_diff.total_seconds() / 3600:.1f} hours",
                        ))

                # Shipment delayed (paid for >24 hours)
                if entry.state_machine_state == OrderState.PAID.value:
                    if time_diff.total_seconds() > 86400:
                        anomalies.append(self._create_anomaly_record(
                            entry=entry,
                            anomaly_type=AnomalyType.SHIPMENT_DELAYED,
                            category=AnomalyCategory.TIMING,
                            severity=SeverityLevel.P1_HOURLY,
                            description=f"Order paid but not shipped for {time_diff.total_seconds() / 86400:.1f} days",
                        ))

                # Delivery delayed (in transit for >7 days)
                if entry.state_machine_state == OrderState.IN_TRANSIT.value:
                    if time_diff.total_seconds() > 604800:
                        anomalies.append(self._create_anomaly_record(
                            entry=entry,
                            anomaly_type=AnomalyType.DELIVERY_DELAYED,
                            category=AnomalyCategory.TIMING,
                            severity=SeverityLevel.P1_HOURLY,
                            description=f"Order in transit for {time_diff.total_seconds() / 604800:.1f} days",
                        ))
            except (ValueError, AttributeError):
                pass

        # 3. State Transition Anomalies
        if entry.state_machine_state:
            current_state_str = entry.state_machine_state
            try:
                current_state = OrderState(current_state_str)

                # Check if current state has valid transitions
                if current_state not in VALID_TRANSITIONS:
                    anomalies.append(self._create_anomaly_record(
                        entry=entry,
                        anomaly_type=AnomalyType.UNEXPECTED_CANCELLATION,
                        category=AnomalyCategory.STATE_TRANSITION,
                        severity=SeverityLevel.P1_HOURLY,
                        description=f"Invalid state: {current_state_str}",
                    ))
            except ValueError:
                pass

        # 4. Reconciliation Anomalies
        if entry.reconciliation_status == ReconciliationStatus.UNMATCHED:
            anomalies.append(self._create_anomaly_record(
                entry=entry,
                anomaly_type=AnomalyType.MISSING_ORDER,
                category=AnomalyCategory.RECONCILIATION,
                severity=SeverityLevel.P0_IMMEDIATE,
                description="Order not found during platform reconciliation",
            ))

        if entry.missing_flag:
            anomalies.append(self._create_anomaly_record(
                entry=entry,
                anomaly_type=AnomalyType.MISSING_ORDER,
                category=AnomalyCategory.RECONCILIATION,
                severity=SeverityLevel.P0_IMMEDIATE,
                description="Order flagged as missing",
            ))

        return anomalies if anomalies else None

    def _create_anomaly_record(
        self,
        entry: OrderLedgerEntry,
        anomaly_type: AnomalyType,
        category: AnomalyCategory,
        severity: SeverityLevel,
        description: str,
    ) -> AnomalyRecord:
        """Create anomaly record.

        Args:
            entry: OrderLedgerEntry
            anomaly_type: Type of anomaly
            category: Anomaly category
            severity: Severity level
            description: Description of anomaly

        Returns:
            AnomalyRecord
        """
        return AnomalyRecord(
            ledger_entry_id=entry.ledger_entry_id,
            order_id=entry.order_id,
            platform=entry.platform,
            shop_id=entry.shop_id,
            anomaly_type=anomaly_type,
            category=category,
            severity=severity,
            description=description,
            order_date=entry.order_date,
            current_state=entry.state_machine_state,
            metadata={
                "platform_state": entry.platform_state,
                "total_amount": entry.total_amount,
                "currency": entry.currency,
                "reconciliation_status": entry.reconciliation_status.value,
            },
        )

    def get_result(self) -> Optional[AnomalyDetectionResult]:
        """Get the last detection result.

        Returns:
            AnomalyDetectionResult or None
        """
        return self.result

    def save_result(self, output_path: Optional[Path] = None) -> Path:
        """Save detection result to JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.result:
            raise ValueError("No result to save - detect_anomalies() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "anomaly_detection_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_critical_anomalies(self) -> List[AnomalyRecord]:
        """Get all P0 (critical) anomalies.

        Returns:
            List of critical AnomalyRecords
        """
        if not self.result:
            return []
        return [a for a in self.result.anomalies if a.severity == SeverityLevel.P0_IMMEDIATE]

    def get_anomalies_by_shop(self, shop_id: str) -> List[AnomalyRecord]:
        """Get anomalies for specific shop.

        Args:
            shop_id: Shop ID to filter

        Returns:
            List of AnomalyRecords for shop
        """
        if not self.result:
            return []
        return [a for a in self.result.anomalies if a.shop_id == shop_id]

    def get_anomalies_by_severity(self, severity: SeverityLevel) -> List[AnomalyRecord]:
        """Get anomalies by severity level.

        Args:
            severity: SeverityLevel to filter

        Returns:
            List of AnomalyRecords with matching severity
        """
        if not self.result:
            return []
        return [a for a in self.result.anomalies if a.severity == severity]


def main() -> None:
    """Demo anomaly detection."""
    print("[AnomalyDetector] Testing Order Anomaly Detection\n")

    detector = OrderAnomalyDetector()

    # Analyze orders
    print("[AnomalyDetector] Analyzing orders for anomalies...\n")
    result = detector.detect_anomalies()

    # Display summary
    print(f"[AnomalyDetector] Detection Results:")
    print(f"  Total orders analyzed: {result.total_orders_analyzed}")
    print(f"  Orders with anomalies: {result.orders_with_anomalies}")
    print(f"  Total anomalies detected: {result.total_anomalies_detected}")

    # Display severity breakdown
    print(f"\n[AnomalyDetector] Severity Breakdown:")
    print(f"  P0 (Immediate): {result.p0_immediate}")
    print(f"  P1 (Hourly): {result.p1_hourly}")
    print(f"  P2 (Daily): {result.p2_daily}")

    # Display category breakdown
    print(f"\n[AnomalyDetector] Category Breakdown:")
    print(f"  Timing anomalies: {result.timing_anomalies}")
    print(f"  State transition anomalies: {result.state_transition_anomalies}")
    print(f"  Data quality anomalies: {result.data_quality_anomalies}")
    print(f"  Reconciliation anomalies: {result.reconciliation_anomalies}")

    # Display critical anomalies
    critical = detector.get_critical_anomalies()
    if critical:
        print(f"\n[AnomalyDetector] Critical Anomalies (P0):")
        for anomaly in critical[:5]:  # Show first 5
            print(f"  - {anomaly.order_id} ({anomaly.platform}): {anomaly.description}")
        if len(critical) > 5:
            print(f"  ... and {len(critical) - 5} more")

    # Save result
    result_path = detector.save_result()
    print(f"\n[AnomalyDetector] Result saved to: {result_path}")

    print(f"\n[AnomalyDetector] ✓ Anomaly detection completed successfully")


if __name__ == "__main__":
    main()
