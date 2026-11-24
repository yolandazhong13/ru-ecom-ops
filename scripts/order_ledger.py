#!/usr/bin/env python3
"""Order ledger for persistent order tracking and reconciliation.

Provides comprehensive order storage with:
1. JSON persistence for all-orders archive with aggregated statistics
2. CSV persistence for daily reconciliation processing
3. Deduplication on (order_id, platform, shop_id) tuple
4. Query support by order_id, date range, shop_id
5. State machine integration with OrderState mapping
6. Reconciliation metadata (matched_on_platform, missing_flag)
"""
from __future__ import annotations

import json
import csv
from abc import ABC
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List
import hashlib

from order_state_machine import OrderState, OrderStateContext, OrderStateMachine
from wb_ozon_api_adapter import PlatformOrderData, PlatformType

ROOT = Path(__file__).resolve().parents[1]
ORDER_LEDGER_JSON = ROOT / "outputs" / "order_ledger.json"
ORDER_LEDGER_CSV = ROOT / "data" / "orders_ledger.csv"


class ReconciliationStatus(str, Enum):
    """Reconciliation status for orders."""
    PENDING = "pending"           # Newly added, awaiting reconciliation
    MATCHED = "matched"           # Found on platform during reconciliation
    UNMATCHED = "unmatched"       # Not found on platform (potential missing order)
    VERIFIED = "verified"         # Verified during daily reconciliation
    FLAGGED = "flagged"           # Flagged for manual review


@dataclass
class OrderLedgerEntry:
    """Order record with reconciliation metadata.

    Extends PlatformOrderData with reconciliation fields for bill matching
    and anomaly detection.
    """
    # Core order data (from PlatformOrderData)
    order_id: str
    platform: str                 # "WB_CN" or "Ozon"
    shop_id: str

    # Order timing
    order_date: str               # ISO timestamp
    payment_date: Optional[str] = None
    shipped_date: Optional[str] = None
    delivery_date: Optional[str] = None

    # Order amount and SKU
    total_amount: float = 0.0
    currency: str = "RUB"
    sku: Optional[str] = None
    items: List[dict[str, Any]] = field(default_factory=list)

    # Order state from platform
    platform_state: str = ""
    state_machine_state: str = ""  # Mapped OrderState enum value

    # Tracking info
    tracking_number: Optional[str] = None
    shipping_provider: Optional[str] = None

    # Payment and delivery confirmation
    payment_confirmed: bool = False
    delivered: bool = False
    signature_confirmed: bool = False

    # Reconciliation fields
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.PENDING
    matched_on_platform: bool = False
    missing_flag: bool = False

    # Metadata
    ledger_entry_id: str = ""     # Unique ledger ID (order_id + platform + shop_id hash)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    api_response_hash: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        d = asdict(self)
        # Convert enums to string values
        d["reconciliation_status"] = self.reconciliation_status.value
        return d

    @staticmethod
    def from_platform_order_data(
        platform_order: PlatformOrderData,
        state_machine_state: Optional[OrderState] = None,
    ) -> OrderLedgerEntry:
        """Create ledger entry from platform order data.

        Args:
            platform_order: PlatformOrderData from API adapter
            state_machine_state: Optional mapped OrderState

        Returns:
            OrderLedgerEntry
        """
        entry = OrderLedgerEntry(
            order_id=platform_order.order_id,
            platform=platform_order.platform,
            shop_id=platform_order.shop_id,
            order_date=platform_order.order_date,
            payment_date=platform_order.payment_date,
            shipped_date=platform_order.shipped_date,
            delivery_date=platform_order.delivery_date,
            total_amount=platform_order.total_amount,
            currency=platform_order.currency,
            sku=platform_order.sku,
            items=platform_order.items,
            platform_state=platform_order.platform_state,
            state_machine_state=state_machine_state.value if state_machine_state else "",
            tracking_number=platform_order.tracking_number,
            shipping_provider=platform_order.shipping_provider,
            payment_confirmed=platform_order.payment_confirmed,
            delivered=platform_order.delivered,
            signature_confirmed=platform_order.signature_confirmed,
            api_response_hash=platform_order.api_response_hash,
        )
        entry.ledger_entry_id = entry._compute_entry_id()
        return entry

    def _compute_entry_id(self) -> str:
        """Compute unique ledger entry ID.

        Uses SHA-256 hash of (order_id, platform, shop_id) tuple
        for consistent deduplication key.
        """
        key = f"{self.order_id}#{self.platform}#{self.shop_id}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


@dataclass
class OrderLedgerStats:
    """Statistics for order ledger."""
    total_orders: int = 0
    total_amount: float = 0.0
    by_platform: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_shop_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_state: dict[str, int] = field(default_factory=dict)
    reconciliation_summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


class OrderLedger:
    """Manages persistent order storage and querying."""

    def __init__(
        self,
        json_path: Path = ORDER_LEDGER_JSON,
        csv_path: Path = ORDER_LEDGER_CSV,
    ):
        """Initialize order ledger.

        Args:
            json_path: Path to JSON ledger file
            csv_path: Path to CSV ledger file
        """
        self.json_path = json_path
        self.csv_path = csv_path
        self.entries: dict[str, OrderLedgerEntry] = {}  # Keyed by ledger_entry_id
        self.stats = OrderLedgerStats()
        self._load_from_json()

    def _load_from_json(self) -> None:
        """Load existing order ledger from JSON if available."""
        if self.json_path.exists():
            try:
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "entries" in data:
                    for entry_dict in data.get("entries", []):
                        entry = self._dict_to_entry(entry_dict)
                        self.entries[entry.ledger_entry_id] = entry
                    self._recalculate_stats()
            except Exception as e:
                print(f"[OrderLedger] Failed to load JSON: {e}")

    def _dict_to_entry(self, entry_dict: dict[str, Any]) -> OrderLedgerEntry:
        """Convert dict to OrderLedgerEntry."""
        entry_dict = entry_dict.copy()
        # Convert reconciliation_status back to enum
        if isinstance(entry_dict.get("reconciliation_status"), str):
            entry_dict["reconciliation_status"] = ReconciliationStatus(
                entry_dict["reconciliation_status"]
            )
        return OrderLedgerEntry(**entry_dict)

    def add_order(self, order_data: OrderLedgerEntry) -> bool:
        """Add order to ledger with deduplication.

        Deduplicates on (order_id, platform, shop_id) tuple.
        If order already exists, updates it with new data.

        Args:
            order_data: OrderLedgerEntry to add

        Returns:
            True if order was added/updated, False if error
        """
        try:
            entry_id = order_data.ledger_entry_id
            is_new = entry_id not in self.entries

            # Update entry
            self.entries[entry_id] = order_data
            self._recalculate_stats()

            status = "added" if is_new else "updated"
            print(
                f"[OrderLedger] Order {status}: {order_data.order_id} "
                f"({order_data.platform}/{order_data.shop_id})"
            )
            return True
        except Exception as e:
            print(f"[OrderLedger] Error adding order: {e}")
            return False

    def add_orders_batch(self, orders: List[OrderLedgerEntry]) -> dict[str, Any]:
        """Add multiple orders in batch.

        Args:
            orders: List of OrderLedgerEntry to add

        Returns:
            Dict with added_count, updated_count, error_count
        """
        result = {"added_count": 0, "updated_count": 0, "error_count": 0}

        for order in orders:
            entry_id = order.ledger_entry_id
            is_new = entry_id not in self.entries

            if self.add_order(order):
                if is_new:
                    result["added_count"] += 1
                else:
                    result["updated_count"] += 1
            else:
                result["error_count"] += 1

        return result

    def query_by_order_id(self, order_id: str) -> List[OrderLedgerEntry]:
        """Query orders by order ID.

        Args:
            order_id: Order ID to search

        Returns:
            List of matching OrderLedgerEntry
        """
        return [e for e in self.entries.values() if e.order_id == order_id]

    def query_by_platform_and_order_id(
        self,
        platform: str,
        order_id: str,
    ) -> Optional[OrderLedgerEntry]:
        """Query single order by platform and order ID.

        Args:
            platform: Platform ("WB_CN" or "Ozon")
            order_id: Order ID

        Returns:
            OrderLedgerEntry if found, None otherwise
        """
        for entry in self.entries.values():
            if entry.platform == platform and entry.order_id == order_id:
                return entry
        return None

    def query_by_shop_id(self, shop_id: str) -> List[OrderLedgerEntry]:
        """Query orders by shop ID.

        Args:
            shop_id: Shop ID to search

        Returns:
            List of matching OrderLedgerEntry
        """
        return [e for e in self.entries.values() if e.shop_id == shop_id]

    def query_by_date_range(
        self,
        start_date: str,
        end_date: str,
    ) -> List[OrderLedgerEntry]:
        """Query orders by date range (order_date).

        Args:
            start_date: ISO timestamp (inclusive)
            end_date: ISO timestamp (inclusive)

        Returns:
            List of matching OrderLedgerEntry
        """
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except Exception:
            return []

        result = []
        for entry in self.entries.values():
            try:
                order_dt = datetime.fromisoformat(
                    entry.order_date.replace("Z", "+00:00")
                )
                if start_dt <= order_dt <= end_dt:
                    result.append(entry)
            except Exception:
                continue

        return result

    def query_by_state(self, state: OrderState) -> List[OrderLedgerEntry]:
        """Query orders by state machine state.

        Args:
            state: OrderState to search

        Returns:
            List of matching OrderLedgerEntry
        """
        state_value = state.value
        return [
            e for e in self.entries.values()
            if e.state_machine_state == state_value
        ]

    def get_unmatched_orders(self) -> List[OrderLedgerEntry]:
        """Get orders not yet matched on platform.

        Returns:
            List of OrderLedgerEntry with matched_on_platform=False
        """
        return [
            e for e in self.entries.values()
            if not e.matched_on_platform
        ]

    def get_missing_orders(self) -> List[OrderLedgerEntry]:
        """Get orders flagged as missing on platform.

        Returns:
            List of OrderLedgerEntry with missing_flag=True
        """
        return [e for e in self.entries.values() if e.missing_flag]

    def mark_as_matched(self, entry_id: str) -> bool:
        """Mark order as matched on platform.

        Args:
            entry_id: Ledger entry ID

        Returns:
            True if marked successfully
        """
        if entry_id in self.entries:
            self.entries[entry_id].matched_on_platform = True
            self.entries[entry_id].reconciliation_status = ReconciliationStatus.MATCHED
            self.entries[entry_id].last_updated = datetime.now(timezone.utc).isoformat()
            self._recalculate_stats()
            return True
        return False

    def mark_as_missing(self, entry_id: str) -> bool:
        """Mark order as missing on platform.

        Args:
            entry_id: Ledger entry ID

        Returns:
            True if marked successfully
        """
        if entry_id in self.entries:
            self.entries[entry_id].missing_flag = True
            self.entries[entry_id].reconciliation_status = ReconciliationStatus.FLAGGED
            self.entries[entry_id].last_updated = datetime.now(timezone.utc).isoformat()
            self._recalculate_stats()
            return True
        return False

    def _recalculate_stats(self) -> None:
        """Recalculate aggregated statistics."""
        self.stats = OrderLedgerStats(
            total_orders=len(self.entries),
            total_amount=sum(e.total_amount for e in self.entries.values()),
        )

        # By platform
        for entry in self.entries.values():
            if entry.platform not in self.stats.by_platform:
                self.stats.by_platform[entry.platform] = {
                    "count": 0,
                    "total_amount": 0.0,
                    "shops": set(),
                }
            self.stats.by_platform[entry.platform]["count"] += 1
            self.stats.by_platform[entry.platform]["total_amount"] += entry.total_amount
            self.stats.by_platform[entry.platform]["shops"].add(entry.shop_id)

        # Convert sets to lists for JSON serialization
        for platform in self.stats.by_platform:
            self.stats.by_platform[platform]["shops"] = list(
                self.stats.by_platform[platform]["shops"]
            )

        # By shop_id
        for entry in self.entries.values():
            if entry.shop_id not in self.stats.by_shop_id:
                self.stats.by_shop_id[entry.shop_id] = {
                    "count": 0,
                    "total_amount": 0.0,
                    "platforms": set(),
                }
            self.stats.by_shop_id[entry.shop_id]["count"] += 1
            self.stats.by_shop_id[entry.shop_id]["total_amount"] += entry.total_amount
            self.stats.by_shop_id[entry.shop_id]["platforms"].add(entry.platform)

        # Convert sets to lists
        for shop_id in self.stats.by_shop_id:
            self.stats.by_shop_id[shop_id]["platforms"] = list(
                self.stats.by_shop_id[shop_id]["platforms"]
            )

        # By state
        for entry in self.entries.values():
            state = entry.state_machine_state or "unknown"
            self.stats.by_state[state] = self.stats.by_state.get(state, 0) + 1

        # Reconciliation summary
        self.stats.reconciliation_summary = {
            status.value: sum(
                1 for e in self.entries.values()
                if e.reconciliation_status == status
            )
            for status in ReconciliationStatus
        }

    def persist_to_json(self) -> bool:
        """Persist ledger to JSON file.

        Returns:
            True if persisted successfully
        """
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_entries": len(self.entries),
                "entries": [e.to_dict() for e in self.entries.values()],
                "statistics": self.stats.to_dict(),
            }

            self.json_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"[OrderLedger] ✓ JSON persisted: {self.json_path}")
            return True
        except Exception as e:
            print(f"[OrderLedger] Error persisting JSON: {e}")
            return False

    def persist_to_csv(self) -> bool:
        """Persist ledger to CSV file for reconciliation processing.

        Returns:
            True if persisted successfully
        """
        try:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)

            csv_headers = [
                "order_id",
                "platform",
                "shop_id",
                "order_date",
                "payment_date",
                "shipped_date",
                "delivery_date",
                "total_amount",
                "currency",
                "sku",
                "platform_state",
                "state_machine_state",
                "reconciliation_status",
                "matched_on_platform",
                "missing_flag",
                "tracking_number",
                "created_at",
            ]

            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csv_headers)
                writer.writeheader()

                for entry in sorted(
                    self.entries.values(),
                    key=lambda e: e.order_date,
                    reverse=True,
                ):
                    row = {
                        "order_id": entry.order_id,
                        "platform": entry.platform,
                        "shop_id": entry.shop_id,
                        "order_date": entry.order_date,
                        "payment_date": entry.payment_date or "",
                        "shipped_date": entry.shipped_date or "",
                        "delivery_date": entry.delivery_date or "",
                        "total_amount": entry.total_amount,
                        "currency": entry.currency,
                        "sku": entry.sku or "",
                        "platform_state": entry.platform_state,
                        "state_machine_state": entry.state_machine_state,
                        "reconciliation_status": entry.reconciliation_status.value,
                        "matched_on_platform": entry.matched_on_platform,
                        "missing_flag": entry.missing_flag,
                        "tracking_number": entry.tracking_number or "",
                        "created_at": entry.created_at,
                    }
                    writer.writerow(row)

            print(f"[OrderLedger] ✓ CSV persisted: {self.csv_path}")
            return True
        except Exception as e:
            print(f"[OrderLedger] Error persisting CSV: {e}")
            return False

    def get_daily_summary(self, date_str: Optional[str] = None) -> dict[str, Any]:
        """Generate daily reconciliation summary.

        Args:
            date_str: ISO date string (default: today)

        Returns:
            Dict with daily summary statistics
        """
        if date_str is None:
            date_str = datetime.now(timezone.utc).date().isoformat()

        # Parse date
        try:
            target_date = datetime.fromisoformat(date_str)
        except Exception:
            return {}

        # Get orders for the date
        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        orders = self.query_by_date_range(start.isoformat(), end.isoformat())

        # Calculate summary
        summary = {
            "date": date_str,
            "total_orders": len(orders),
            "total_amount": sum(o.total_amount for o in orders),
            "by_platform": {},
            "by_shop": {},
            "by_state": {},
        }

        for order in orders:
            # By platform
            if order.platform not in summary["by_platform"]:
                summary["by_platform"][order.platform] = {
                    "count": 0,
                    "amount": 0.0,
                }
            summary["by_platform"][order.platform]["count"] += 1
            summary["by_platform"][order.platform]["amount"] += order.total_amount

            # By shop
            if order.shop_id not in summary["by_shop"]:
                summary["by_shop"][order.shop_id] = {
                    "count": 0,
                    "amount": 0.0,
                }
            summary["by_shop"][order.shop_id]["count"] += 1
            summary["by_shop"][order.shop_id]["amount"] += order.total_amount

            # By state
            state = order.state_machine_state or "unknown"
            summary["by_state"][state] = summary["by_state"].get(state, 0) + 1

        return summary


def main() -> None:
    """Demo order ledger usage."""
    print("[OrderLedger] Testing Order Ledger\n")

    ledger = OrderLedger()
    print(f"[OrderLedger] Loaded {len(ledger.entries)} existing entries\n")

    # Create sample entries
    sample_entries = [
        OrderLedgerEntry(
            order_id="WB_12345678",
            platform="WB_CN",
            shop_id="250146669",
            order_date="2026-11-23T10:30:00+00:00",
            payment_date="2026-11-23T10:35:00+00:00",
            total_amount=1500.0,
            currency="RUB",
            sku="SKU-001",
            platform_state="pending",
            state_machine_state="paid",
            payment_confirmed=True,
        ),
        OrderLedgerEntry(
            order_id="OZ_87654321",
            platform="Ozon",
            shop_id="6182781",
            order_date="2026-11-22T14:20:00+00:00",
            payment_date="2026-11-22T14:25:00+00:00",
            shipped_date="2026-11-23T08:00:00+00:00",
            total_amount=2500.0,
            currency="RUB",
            sku="SKU-002",
            platform_state="shipped",
            state_machine_state="shipped",
            payment_confirmed=True,
        ),
    ]

    # Add sample entries
    print("[OrderLedger] Adding sample entries...")
    for entry in sample_entries:
        entry.ledger_entry_id = entry._compute_entry_id()
        ledger.add_order(entry)

    print(f"\n[OrderLedger] Ledger statistics:")
    print(f"  Total orders: {ledger.stats.total_orders}")
    print(f"  Total amount: {ledger.stats.total_amount} {sample_entries[0].currency}")

    if ledger.stats.by_platform:
        print(f"\n[OrderLedger] By platform:")
        for platform, info in ledger.stats.by_platform.items():
            print(f"  {platform}: {info['count']} orders, {info['total_amount']} RUB")

    # Test queries
    print(f"\n[OrderLedger] Testing queries:")
    wb_order = ledger.query_by_platform_and_order_id("WB_CN", "WB_12345678")
    print(f"  WB order WB_12345678: {wb_order.order_id if wb_order else 'Not found'}")

    shop_orders = ledger.query_by_shop_id("250146669")
    print(f"  Orders for shop 250146669: {len(shop_orders)}")

    # Persist
    print(f"\n[OrderLedger] Persisting ledger...")
    ledger.persist_to_json()
    ledger.persist_to_csv()

    # Daily summary
    daily = ledger.get_daily_summary("2026-11-23")
    print(f"\n[OrderLedger] Daily summary (2026-11-23):")
    print(f"  Total orders: {daily['total_orders']}")
    print(f"  Total amount: {daily['total_amount']} RUB")

    print(f"\n[OrderLedger] ✓ Order ledger initialized successfully")


if __name__ == "__main__":
    main()
