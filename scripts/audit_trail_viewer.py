#!/usr/bin/env python3
"""Audit trail viewer for exploring order history.

Provides:
1. Order history lookup
2. Event timeline visualization
3. State transition tracking
4. Recovery action history
5. Full traceability export
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_audit_trail import OrderAuditTrail, AuditEventType
from order_ledger import OrderLedger


class AuditTrailViewer:
    """Explores and displays audit trails."""

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize audit trail viewer.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.audit = OrderAuditTrail(self.ledger)
        self.trails = None

    def build_trails(self) -> None:
        """Build audit trails from ledger."""
        report = self.audit.build_audit_trails()
        self.trails = self.audit.trails

    def display_order_history(self, order_id: str) -> str:
        """Display history for specific order.

        Args:
            order_id: Order ID to look up

        Returns:
            Formatted history display
        """
        if not self.trails:
            self.build_trails()

        if order_id not in self.trails:
            return f"Order {order_id} not found in audit trails"

        trail = self.trails[order_id]
        output = []

        output.append(f"\n{'=' * 90}")
        output.append(f"ORDER HISTORY: {order_id}".center(90))
        output.append(f"{'=' * 90}")
        output.append(f"Created: {trail.created_at}")
        output.append(f"Last Modified: {trail.last_modified}")
        output.append(f"Total Events: {len(trail.events)}\n")

        output.append(f"{'Time':<20} {'Event Type':<25} {'Details':<45}")
        output.append("-" * 90)

        for event in trail.events:
            time_str = event.timestamp[11:19] if len(event.timestamp) > 10 else "N/A"
            event_type = event.event_type.value.replace("_", " ").title()

            # Format details
            if event.old_value and event.new_value:
                details = f"{event.old_value} → {event.new_value}"
            elif event.new_value:
                details = f"→ {event.new_value}"
            else:
                details = event.description[:40] if event.description else ""

            output.append(f"{time_str:<20} {event_type:<25} {details:<45}")

        output.append(f"{'=' * 90}\n")

        return "\n".join(output)

    def display_all_orders_summary(self) -> str:
        """Display summary for all orders.

        Returns:
            Formatted summary
        """
        if not self.trails:
            self.build_trails()

        output = []
        output.append(f"\n{'=' * 90}")
        output.append(f"ORDER AUDIT SUMMARY".center(90))
        output.append(f"{'=' * 90}\n")

        output.append(f"{'Order ID':<20} {'Platform':<12} {'Events':<10} {'Last Modified':<20}")
        output.append("-" * 90)

        for order_id, trail in sorted(self.trails.items()):
            last_mod = trail.last_modified[11:19] if len(trail.last_modified) > 10 else "N/A"
            output.append(
                f"{order_id:<20} {trail.platform:<12} {len(trail.events):<10} {last_mod:<20}"
            )

        output.append(f"{'=' * 90}\n")
        return "\n".join(output)

    def display_event_timeline(self) -> str:
        """Display timeline of all events across all orders.

        Returns:
            Formatted timeline
        """
        if not self.trails:
            self.build_trails()

        output = []
        output.append(f"\n{'=' * 90}")
        output.append(f"EVENT TIMELINE".center(90))
        output.append(f"{'=' * 90}\n")

        # Collect all events with order context
        all_events = []
        for order_id, trail in self.trails.items():
            for event in trail.events:
                all_events.append((order_id, event))

        # Sort by timestamp
        all_events.sort(key=lambda x: x[1].timestamp, reverse=True)

        output.append(f"{'Time':<20} {'Order ID':<20} {'Event Type':<25} {'Details':<25}")
        output.append("-" * 90)

        for order_id, event in all_events[:50]:  # Last 50 events
            time_str = event.timestamp[11:19] if len(event.timestamp) > 10 else "N/A"
            event_type = event.event_type.value.replace("_", " ").title()
            details = (event.description[:25] if event.description else "")

            output.append(
                f"{time_str:<20} {order_id:<20} {event_type:<25} {details:<25}"
            )

        output.append(f"{'=' * 90}\n")
        return "\n".join(output)

    def export_audit_trail(self, order_id: str, output_path: Optional[Path] = None) -> Path:
        """Export audit trail for order.

        Args:
            order_id: Order ID to export
            output_path: Output file path

        Returns:
            Path to exported file
        """
        if not self.trails:
            self.build_trails()

        if order_id not in self.trails:
            raise ValueError(f"Order {order_id} not found")

        trail = self.trails[order_id]

        if not output_path:
            output_path = ROOT / "outputs" / f"audit_trail_export_{order_id}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(trail.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_event_statistics(self) -> dict:
        """Get statistics about audit events.

        Returns:
            Dict with event statistics
        """
        if not self.trails:
            self.build_trails()

        stats = {
            "total_orders": len(self.trails),
            "total_events": 0,
            "events_by_type": {},
        }

        for trail in self.trails.values():
            stats["total_events"] += len(trail.events)
            for event in trail.events:
                event_type = event.event_type.value
                stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1

        return stats


def main() -> None:
    """Demo audit trail viewer."""
    print("[AuditViewer] Testing Audit Trail Viewer\n")

    viewer = AuditTrailViewer()
    viewer.build_trails()

    # Display summary
    print(viewer.display_all_orders_summary())

    # Display timeline
    print(viewer.display_event_timeline())

    # Display individual order history
    if viewer.trails:
        first_order = list(viewer.trails.keys())[0]
        print(viewer.display_order_history(first_order))

    # Statistics
    stats = viewer.get_event_statistics()
    print(f"[AuditViewer] Event Statistics:")
    print(f"  Total orders: {stats['total_orders']}")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Events by type:")
    for event_type, count in sorted(stats['events_by_type'].items()):
        print(f"    {event_type}: {count}")

    print(f"\n[AuditViewer] ✓ Audit viewer completed")


if __name__ == "__main__":
    main()
