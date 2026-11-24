#!/usr/bin/env python3
"""Order tracker for unified order data aggregation and sync.

Retrieves orders via UnifiedAPIGateway, maps platform states to OrderState enum,
executes state transitions via OrderStateMachine, and persists to order_ledger.

Workflow:
1. Authenticate with platform APIs
2. Fetch active orders from all platforms
3. For each order:
   - Map platform_state → OrderState (via state mapping)
   - Create/update OrderStateContext
   - Execute state transition via OrderStateMachine
   - Detect anomalies based on timing and state rules
   - Add to OrderLedger
4. Generate sync report with counts and anomalies
5. Persist ledger to JSON/CSV
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List
import sys

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wb_ozon_api_adapter import UnifiedAPIGateway, PlatformOrderData, PlatformType
from order_state_machine import OrderState, OrderStateMachine, OrderStateContext, AnomalyType
from order_ledger import OrderLedger, ReconciliationStatus


# Platform state to OrderState mapping
PLATFORM_STATE_MAPPING = {
    # WB states
    "new": OrderState.PENDING_PAYMENT,
    "awaiting_approval": OrderState.PENDING_PAYMENT,
    "confirmed": OrderState.PAID,
    "shipped": OrderState.SHIPPED,
    "in_transit": OrderState.IN_TRANSIT,
    "delivered": OrderState.DELIVERED,
    "completed": OrderState.CONFIRMED,

    # Ozon states
    "awaiting_payment": OrderState.PENDING_PAYMENT,
    "awaiting_approval": OrderState.PENDING_PAYMENT,
    "processing": OrderState.PAID,
    "awaiting_shipment": OrderState.SHIPPED,
    "shipment_in_transit": OrderState.IN_TRANSIT,
    "delivered_to_customer": OrderState.DELIVERED,
    "awaiting_customer_confirmation": OrderState.DELIVERED,

    # Terminal states
    "cancelled": OrderState.CANCELLED,
    "refused": OrderState.REFUSED_PRE_DELIVERY,
    "returned": OrderState.RETURNED,
}


@dataclass
class OrderSyncResult:
    """Result of order sync operation."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    platform: str = ""
    shop_id: str = ""
    orders_fetched: int = 0
    orders_processed: int = 0
    orders_failed: int = 0
    new_orders: int = 0
    updated_orders: int = 0
    anomalies_detected: int = 0
    anomaly_details: List[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class OrderTrackerReport:
    """Report from order tracker run."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_duration_ms: int = 0
    sync_results: List[OrderSyncResult] = field(default_factory=list)

    # Aggregated statistics
    total_fetched: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_new: int = 0
    total_updated: int = 0
    total_anomalies: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


class OrderTracker:
    """Unified order tracker managing aggregation, sync, and state machine."""

    def __init__(self, json_path: Optional[Path] = None, csv_path: Optional[Path] = None):
        """Initialize order tracker.

        Args:
            json_path: Path to JSON ledger file (default: outputs/order_ledger.json)
            csv_path: Path to CSV ledger file (default: data/orders_ledger.csv)
        """
        self.gateway = UnifiedAPIGateway()

        # Use provided paths or defaults
        if json_path is None:
            json_path = ROOT / "outputs" / "order_ledger.json"
        if csv_path is None:
            csv_path = ROOT / "data" / "orders_ledger.csv"

        self.ledger = OrderLedger(json_path=json_path, csv_path=csv_path)
        self.report = None
        self.sync_results: List[OrderSyncResult] = []

    def map_platform_state(self, platform_state: str, platform: str) -> Optional[OrderState]:
        """Map platform state to OrderState enum.

        Args:
            platform_state: State from platform API
            platform: Platform name ("WB_CN" or "Ozon")

        Returns:
            OrderState or None if mapping not found
        """
        normalized_state = platform_state.lower().strip()
        return PLATFORM_STATE_MAPPING.get(normalized_state)

    def detect_anomalies(
        self,
        order_data: PlatformOrderData,
        mapped_state: OrderState,
        existing_context: Optional[OrderStateContext] = None,
    ) -> List[AnomalyType]:
        """Detect anomalies in order data and transitions.

        Args:
            order_data: Platform order data
            mapped_state: Mapped OrderState
            existing_context: Existing state context if order exists

        Returns:
            List of detected anomalies
        """
        anomalies: List[AnomalyType] = []
        now = datetime.now(timezone.utc)

        # Parse order date
        try:
            order_date = datetime.fromisoformat(order_data.order_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return anomalies

        # Timing anomalies
        time_diff = now - order_date

        if mapped_state == OrderState.PENDING_PAYMENT and time_diff.total_seconds() > 3600:  # 1 hour
            anomalies.append(AnomalyType.PAYMENT_OVERDUE)

        if mapped_state == OrderState.PAID and time_diff.total_seconds() > 86400:  # 24 hours
            anomalies.append(AnomalyType.SHIPMENT_DELAYED)

        if mapped_state == OrderState.IN_TRANSIT and time_diff.total_seconds() > 604800:  # 7 days
            anomalies.append(AnomalyType.DELIVERY_DELAYED)

        # State transition anomalies
        if existing_context:
            current_state = existing_context.current_state

            # Check for unexpected cancellation
            if mapped_state == OrderState.CANCELLED and current_state not in [
                OrderState.PENDING_PAYMENT,
                OrderState.PAID,
                OrderState.SHIPPED,
            ]:
                anomalies.append(AnomalyType.UNEXPECTED_CANCELLATION)

            # Check for unexpected refusal
            if mapped_state in [OrderState.REFUSED_PRE_DELIVERY, OrderState.REFUSED_POST_DELIVERY]:
                if mapped_state == OrderState.REFUSED_PRE_DELIVERY and current_state != OrderState.IN_TRANSIT:
                    anomalies.append(AnomalyType.UNEXPECTED_REFUSAL)
                elif mapped_state == OrderState.REFUSED_POST_DELIVERY and current_state != OrderState.DELIVERED:
                    anomalies.append(AnomalyType.UNEXPECTED_REFUSAL)

            # Check for unexpected return
            if mapped_state == OrderState.RETURNED and current_state not in [
                OrderState.DELIVERED,
                OrderState.CONFIRMED,
            ]:
                anomalies.append(AnomalyType.UNEXPECTED_RETURN)

        # Data anomalies
        if not order_data.order_id:
            anomalies.append(AnomalyType.MISSING_ORDER)

        if order_data.total_amount <= 0:
            anomalies.append(AnomalyType.AMOUNT_MISMATCH)

        if not order_data.sku and not order_data.items:
            anomalies.append(AnomalyType.SKU_MISMATCH)

        return anomalies

    def sync_orders_from_platform(self) -> OrderTrackerReport:
        """Synchronize orders from all platforms.

        Returns:
            OrderTrackerReport with sync results
        """
        start_time = time.time()
        self.sync_results = []

        # Authenticate
        print("[OrderTracker] Authenticating with platform APIs...")
        auth_results = self.gateway.authenticate_all()
        for adapter_name, authenticated in auth_results.items():
            status = "✓" if authenticated else "✗"
            print(f"  {status} {adapter_name}")

        # Fetch orders from all platforms
        print(f"\n[OrderTracker] Fetching orders from all platforms...")
        all_orders = self.gateway.fetch_all_orders()

        total_fetched = 0
        for adapter_name, orders in all_orders.items():
            platform, shop_id = self.gateway._parse_adapter_name(adapter_name)
            sync_result = self._process_platform_orders(platform, shop_id, orders)
            self.sync_results.append(sync_result)
            total_fetched += sync_result.orders_fetched

        # Generate report
        duration_ms = int((time.time() - start_time) * 1000)
        report = OrderTrackerReport(total_duration_ms=duration_ms)
        report.sync_results = self.sync_results

        # Aggregate statistics
        for result in self.sync_results:
            report.total_fetched += result.orders_fetched
            report.total_processed += result.orders_processed
            report.total_failed += result.orders_failed
            report.total_new += result.new_orders
            report.total_updated += result.updated_orders
            report.total_anomalies += result.anomalies_detected

        self.report = report
        return report

    def _process_platform_orders(
        self,
        platform: str,
        shop_id: str,
        orders: List[PlatformOrderData],
    ) -> OrderSyncResult:
        """Process orders from a single platform.

        Args:
            platform: Platform name
            shop_id: Shop ID
            orders: List of orders from platform

        Returns:
            OrderSyncResult with processing details
        """
        result = OrderSyncResult(platform=platform, shop_id=shop_id)
        result.orders_fetched = len(orders)

        from order_ledger import OrderLedgerEntry, ReconciliationStatus

        orders_to_add = []

        for order_data in orders:
            try:
                # Map platform state to OrderState
                mapped_state = self.map_platform_state(order_data.platform_state, platform)
                if not mapped_state:
                    result.errors.append(
                        f"Unknown platform state '{order_data.platform_state}' for order {order_data.order_id}"
                    )
                    result.orders_failed += 1
                    continue

                # Check if order already exists
                existing_entry = self.ledger.query_by_platform_and_order_id(
                    order_data.platform,
                    order_data.order_id,
                )

                # Create or update state context
                if existing_entry:
                    # Update existing order
                    state_context = OrderStateContext(
                        order_id=order_data.order_id,
                        platform=order_data.platform,
                        shop_id=order_data.shop_id,
                        current_state=mapped_state,
                        order_date=order_data.order_date,
                        payment_date=order_data.payment_date,
                        sku=order_data.sku,
                        amount=order_data.total_amount,
                        currency=order_data.currency,
                    )
                    result.updated_orders += 1
                else:
                    # New order
                    state_context = OrderStateContext(
                        order_id=order_data.order_id,
                        platform=order_data.platform,
                        shop_id=order_data.shop_id,
                        current_state=OrderState.PENDING_PAYMENT,  # Initial state
                        order_date=order_data.order_date,
                        payment_date=order_data.payment_date,
                        sku=order_data.sku,
                        amount=order_data.total_amount,
                        currency=order_data.currency,
                    )
                    result.new_orders += 1

                # Detect anomalies
                anomalies = self.detect_anomalies(
                    order_data,
                    mapped_state,
                    state_context,
                )
                state_context.detected_anomalies = anomalies

                if anomalies:
                    result.anomalies_detected += len(anomalies)
                    for anomaly in anomalies:
                        result.anomaly_details.append({
                            "order_id": order_data.order_id,
                            "anomaly_type": anomaly.value,
                        })

                # Execute state transition if needed
                if state_context.current_state != mapped_state:
                    success, error = OrderStateMachine.transition(
                        state_context,
                        mapped_state,
                        reason=f"Platform state update: {order_data.platform_state}",
                        metadata={
                            "platform": platform,
                            "shop_id": shop_id,
                            "platform_state": order_data.platform_state,
                            "tracking_number": order_data.tracking_number,
                        },
                    )
                    if not success:
                        result.errors.append(f"Transition failed for {order_data.order_id}: {error}")
                        result.orders_failed += 1
                        continue

                # Create OrderLedgerEntry for persistence
                ledger_entry = OrderLedgerEntry(
                    order_id=order_data.order_id,
                    platform=order_data.platform,
                    shop_id=order_data.shop_id,
                    order_date=order_data.order_date,
                    payment_date=order_data.payment_date,
                    shipped_date=state_context.shipped_date,
                    delivery_date=state_context.delivery_date,
                    total_amount=order_data.total_amount,
                    currency=order_data.currency,
                    sku=order_data.sku,
                    items=order_data.items,
                    platform_state=order_data.platform_state,
                    state_machine_state=mapped_state.value,
                    tracking_number=order_data.tracking_number,
                    shipping_provider=order_data.shipping_provider,
                    payment_confirmed=order_data.payment_confirmed,
                    delivered=order_data.delivered,
                    signature_confirmed=order_data.signature_confirmed,
                    api_response_hash=order_data.api_response_hash,
                    reconciliation_status=ReconciliationStatus.PENDING,
                )
                orders_to_add.append(ledger_entry)
                result.orders_processed += 1

            except Exception as e:
                result.errors.append(f"Error processing order {order_data.order_id}: {str(e)}")
                result.orders_failed += 1
                continue

        # Batch add orders to ledger
        if orders_to_add:
            batch_result = self.ledger.add_orders_batch(orders_to_add)
            if batch_result.get("error_count", 0) > 0:
                result.errors.append(
                    f"Failed to add {batch_result['error_count']} orders to ledger"
                )

        return result

    def get_report(self) -> Optional[OrderTrackerReport]:
        """Get the last sync report.

        Returns:
            OrderTrackerReport or None if no sync performed
        """
        return self.report

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save tracker report to JSON file.

        Args:
            output_path: Output file path (default: outputs/order_tracker_report.json)

        Returns:
            Path to saved report
        """
        if not self.report:
            raise ValueError("No report to save - sync_orders_from_platform() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "order_tracker_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def persist_ledger(self) -> tuple[Path, Path]:
        """Persist order ledger to JSON and CSV.

        Returns:
            Tuple of (json_path, csv_path)
        """
        json_path = self.ledger.persist_to_json()
        csv_path = self.ledger.persist_to_csv()
        return json_path, csv_path


def main() -> None:
    """Demo order tracker functionality."""
    print("[OrderTracker] Testing Order Tracker\n")

    tracker = OrderTracker()

    # Sync orders from all platforms
    print("[OrderTracker] Starting order sync...\n")
    report = tracker.sync_orders_from_platform()

    # Display report
    print(f"\n[OrderTracker] Sync Report:")
    print(f"  Total fetched: {report.total_fetched}")
    print(f"  Total processed: {report.total_processed}")
    print(f"  Total failed: {report.total_failed}")
    print(f"  New orders: {report.total_new}")
    print(f"  Updated orders: {report.total_updated}")
    print(f"  Anomalies detected: {report.total_anomalies}")
    print(f"  Duration: {report.total_duration_ms}ms")

    # Display per-platform results
    print(f"\n[OrderTracker] Per-Platform Results:")
    for sync_result in report.sync_results:
        print(f"\n  {sync_result.platform} ({sync_result.shop_id}):")
        print(f"    Fetched: {sync_result.orders_fetched}")
        print(f"    Processed: {sync_result.orders_processed}")
        print(f"    Failed: {sync_result.orders_failed}")
        if sync_result.errors:
            print(f"    Errors:")
            for error in sync_result.errors:
                print(f"      - {error}")

    # Display anomalies
    if report.total_anomalies > 0:
        print(f"\n[OrderTracker] Detected Anomalies:")
        for sync_result in report.sync_results:
            if sync_result.anomaly_details:
                for anomaly in sync_result.anomaly_details:
                    print(f"  - {anomaly['order_id']}: {anomaly['anomaly_type']}")

    # Save report and ledger
    report_path = tracker.save_report()
    json_path, csv_path = tracker.persist_ledger()

    print(f"\n[OrderTracker] Files saved:")
    print(f"  Report: {report_path}")
    print(f"  Ledger (JSON): {json_path}")
    print(f"  Ledger (CSV): {csv_path}")

    print(f"\n[OrderTracker] ✓ Order tracker initialized successfully")


if __name__ == "__main__":
    main()
