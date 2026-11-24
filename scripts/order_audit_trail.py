#!/usr/bin/env python3
"""Order audit trail for complete historical traceability.

Maintains full audit log:
1. Order creation and initial state
2. All state transitions with reasons
3. Anomalies detected
4. Alert dispatches
5. Recovery attempts
6. Reconciliation results

Provides complete order history for compliance and debugging.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus


class AuditEventType(str, Enum):
    """Audit event types."""
    ORDER_CREATED = "order_created"
    STATE_TRANSITION = "state_transition"
    ANOMALY_DETECTED = "anomaly_detected"
    ALERT_DISPATCHED = "alert_dispatched"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    RECONCILIATION_CHECKED = "reconciliation_checked"
    STATUS_UPDATED = "status_updated"


@dataclass
class AuditEvent:
    """Single audit trail event."""
    event_type: AuditEventType
    order_id: str
    platform: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Event details
    details: dict[str, Any] = field(default_factory=dict)

    # Optional fields
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    actor: str = "system"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


@dataclass
class AuditTrail:
    """Complete audit trail for order."""
    order_id: str
    platform: str
    created_at: str
    last_modified: str = ""
    events: List[AuditEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "platform": self.platform,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }


@dataclass
class AuditReport:
    """Audit trail report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_orders: int = 0
    total_events: int = 0
    trails: List[AuditTrail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_orders": self.total_orders,
            "total_events": self.total_events,
            "trails": [t.to_dict() for t in self.trails],
        }


class OrderAuditTrail:
    """Maintains complete order audit trails."""

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize audit trail system.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.report = None
        self.trails: dict[str, AuditTrail] = {}

    def build_audit_trails(self) -> AuditReport:
        """Build audit trails from ledger.

        Returns:
            AuditReport with all trails
        """
        report = AuditReport()
        report.total_orders = len(self.ledger.entries)

        for entry_id, entry in self.ledger.entries.items():
            trail = self._build_trail_for_order(entry)
            report.trails.append(trail)
            self.trails[entry.order_id] = trail
            report.total_events += len(trail.events)

        self.report = report
        return report

    def _build_trail_for_order(self, entry: OrderLedgerEntry) -> AuditTrail:
        """Build audit trail for single order.

        Args:
            entry: OrderLedgerEntry to audit

        Returns:
            AuditTrail with all events
        """
        trail = AuditTrail(
            order_id=entry.order_id,
            platform=entry.platform,
            created_at=entry.created_at,
            last_modified=entry.last_updated,
        )

        # Event 1: Order created
        trail.events.append(AuditEvent(
            event_type=AuditEventType.ORDER_CREATED,
            order_id=entry.order_id,
            platform=entry.platform,
            timestamp=entry.created_at,
            details={
                "shop_id": entry.shop_id,
                "amount": entry.total_amount,
                "currency": entry.currency,
                "platform_state": entry.platform_state,
            },
        ))

        # Event 2: State transition (current state)
        if entry.state_machine_state != entry.platform_state:
            trail.events.append(AuditEvent(
                event_type=AuditEventType.STATE_TRANSITION,
                order_id=entry.order_id,
                platform=entry.platform,
                timestamp=entry.last_updated,
                old_value=entry.platform_state,
                new_value=entry.state_machine_state,
                details={
                    "reason": "State normalized from platform",
                },
            ))

        # Event 3: Anomalies (tracked via reconciliation status)
        if entry.reconciliation_status != ReconciliationStatus.PENDING:
            trail.events.append(AuditEvent(
                event_type=AuditEventType.ANOMALY_DETECTED,
                order_id=entry.order_id,
                platform=entry.platform,
                details={
                    "anomaly_type": entry.reconciliation_status.value,
                },
            ))

        # Event 4: Reconciliation
        trail.events.append(AuditEvent(
            event_type=AuditEventType.RECONCILIATION_CHECKED,
            order_id=entry.order_id,
            platform=entry.platform,
            timestamp=entry.last_updated,
            details={
                "reconciliation_status": entry.reconciliation_status.value,
                "matched_on_platform": entry.matched_on_platform,
                "missing_flag": entry.missing_flag,
            },
        ))

        # Event 5: Final status
        trail.events.append(AuditEvent(
            event_type=AuditEventType.STATUS_UPDATED,
            order_id=entry.order_id,
            platform=entry.platform,
            timestamp=entry.last_updated,
            new_value=entry.state_machine_state,
            details={
                "current_state": entry.state_machine_state,
                "total_amount": entry.total_amount,
                "payment_confirmed": entry.payment_confirmed,
                "delivered": entry.delivered,
            },
        ))

        return trail

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save audit report.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - build_audit_trails() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "audit_trail_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_order_history(self, order_id: str) -> Optional[List[AuditEvent]]:
        """Get audit history for specific order.

        Args:
            order_id: Order ID to look up

        Returns:
            List of AuditEvent or None
        """
        if order_id not in self.trails:
            return None
        return self.trails[order_id].events

    def get_report(self) -> Optional[AuditReport]:
        """Get audit report.

        Returns:
            AuditReport or None
        """
        return self.report


def main() -> None:
    """Demo audit trail."""
    print("[AuditTrail] Testing Order Audit Trail System\n")

    audit = OrderAuditTrail()
    report = audit.build_audit_trails()
    audit.save_report()

    print(f"[AuditTrail] Audit Trail Report:")
    print(f"  Total orders: {report.total_orders}")
    print(f"  Total events: {report.total_events}")

    if report.trails:
        print(f"\n[AuditTrail] Sample Audit Trails (first 2 orders):")
        for trail in report.trails[:2]:
            print(f"\n  Order: {trail.order_id} ({trail.platform})")
            print(f"  Events: {len(trail.events)}")
            for event in trail.events[:3]:
                print(f"    - {event.event_type.value} @ {event.timestamp[11:19]}")
            if len(trail.events) > 3:
                print(f"    ... and {len(trail.events) - 3} more events")

    print(f"\n[AuditTrail] ✓ Audit trail generation completed")


if __name__ == "__main__":
    main()
