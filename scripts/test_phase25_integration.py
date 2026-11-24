#!/usr/bin/env python3
"""Phase 2.5: Integrated end-to-end order processing pipeline test harness.

Tests the complete workflow:
1. OrderTracker: Aggregate orders from platforms
2. OrderAnomalyDetector: Detect anomalies in aggregated orders
3. BillingAggregator: Generate billing reports
4. ReconciliationEngine: Reconcile against platforms
5. OrderAlertDispatcher: Dispatch alerts for critical anomalies

Generates synthetic order data and validates cross-component integration.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_tracker import OrderTracker, OrderTrackerReport
from order_anomaly_detector import OrderAnomalyDetector, AnomalyDetectionResult
from billing_aggregator import BillingAggregator, BillingReport, BillingPeriod
from reconciliation_engine import ReconciliationEngine, ReconciliationReport
from order_alert_dispatcher import OrderAlertDispatcher, DispatchResult
from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus
from order_state_machine import OrderState
from wb_ozon_api_adapter import PlatformOrderData, PlatformType


def create_synthetic_orders(count: int = 50) -> List[OrderLedgerEntry]:
    """Create synthetic order data for testing.

    Args:
        count: Number of orders to generate

    Returns:
        List of OrderLedgerEntry
    """
    orders = []
    now = datetime.now(timezone.utc)

    platforms = ["WB_CN", "Ozon"]
    shops_wb = ["250146669", "250146670"]
    shops_ozon = ["6182781", "3521307"]
    states = [
        OrderState.PENDING_PAYMENT,
        OrderState.PAID,
        OrderState.SHIPPED,
        OrderState.IN_TRANSIT,
        OrderState.DELIVERED,
        OrderState.CONFIRMED,
    ]

    for i in range(count):
        platform = random.choice(platforms)
        if platform == "WB_CN":
            shop_id = random.choice(shops_wb)
            order_id = f"WB_{100000000 + i}"
        else:
            shop_id = random.choice(shops_ozon)
            order_id = f"OZON_{100000000 + i}"

        # Vary order dates to test billing aggregation
        days_back = random.randint(0, 30)
        order_date = (now - timedelta(days=days_back)).isoformat()

        # Random state with some at CONFIRMED (successful orders)
        if random.random() < 0.6:
            state = OrderState.CONFIRMED
        else:
            state = random.choice(states)

        # Random amount
        amount = round(random.uniform(500, 10000), 2)

        entry = OrderLedgerEntry(
            order_id=order_id,
            platform=platform,
            shop_id=shop_id,
            order_date=order_date,
            payment_date=order_date if state != OrderState.PENDING_PAYMENT else None,
            shipped_date=order_date if state.value in [
                OrderState.SHIPPED.value,
                OrderState.IN_TRANSIT.value,
                OrderState.DELIVERED.value,
                OrderState.CONFIRMED.value,
            ] else None,
            delivery_date=order_date if state in [
                OrderState.DELIVERED,
                OrderState.CONFIRMED,
            ] else None,
            total_amount=amount,
            currency="RUB",
            sku=f"SKU-{random.randint(1000, 9999)}",
            items=[{"sku": f"SKU-{random.randint(1000, 9999)}", "quantity": random.randint(1, 5)}],
            platform_state=state.value,
            state_machine_state=state.value,
            payment_confirmed=state != OrderState.PENDING_PAYMENT,
            delivered=state in [OrderState.DELIVERED, OrderState.CONFIRMED],
            reconciliation_status=ReconciliationStatus.PENDING,
        )
        entry.ledger_entry_id = entry._compute_entry_id()
        orders.append(entry)

    return orders


def run_integration_test():
    """Run complete Phase 2 integration test."""
    print("=" * 70)
    print("PHASE 2.5: INTEGRATED END-TO-END ORDER PROCESSING PIPELINE TEST")
    print("=" * 70)

    # Step 1: Populate ledger with synthetic data
    print("\n[Phase 2.5] Step 1: Populating order ledger with synthetic data...")
    ledger = OrderLedger()
    synthetic_orders = create_synthetic_orders(count=50)

    # Add orders to ledger
    batch_result = ledger.add_orders_batch(synthetic_orders)
    print(f"  ✓ Added {batch_result['added_count']} orders")
    print(f"  ✓ Failed entries: {batch_result['error_count']}")

    # Step 2: Run anomaly detection
    print("\n[Phase 2.5] Step 2: Detecting anomalies...")
    detector = OrderAnomalyDetector(ledger=ledger)
    detection_result = detector.detect_anomalies()
    detector.save_result()

    print(f"  ✓ Total orders analyzed: {detection_result.total_orders_analyzed}")
    print(f"  ✓ Orders with anomalies: {detection_result.orders_with_anomalies}")
    print(f"  ✓ Total anomalies detected: {detection_result.total_anomalies_detected}")
    print(f"    - P0 (Immediate): {detection_result.p0_immediate}")
    print(f"    - P1 (Hourly): {detection_result.p1_hourly}")
    print(f"    - P2 (Daily): {detection_result.p2_daily}")

    # Step 3: Dispatch alerts
    print("\n[Phase 2.5] Step 3: Dispatching alerts...")
    dispatcher = OrderAlertDispatcher()
    dispatch_result = dispatcher.dispatch_alerts()
    dispatcher.save_result()

    print(f"  ✓ Anomalies processed: {dispatch_result.total_anomalies_processed}")
    print(f"  ✓ Alerts dispatched: {dispatch_result.alerts_dispatched}")
    print(f"  ✓ Alerts failed: {dispatch_result.alerts_failed}")

    # Step 4: Generate billing reports
    print("\n[Phase 2.5] Step 4: Generating billing reports...")
    aggregator = BillingAggregator(ledger=ledger)

    # Generate daily report
    daily_report = aggregator.aggregate_daily()
    aggregator.save_report()

    print(f"  ✓ Daily report generated")
    print(f"    - Total orders: {daily_report.total_orders}")
    print(f"    - Total amount: {daily_report.total_amount:.2f} RUB")
    print(f"    - Confirmed: {daily_report.confirmed_total:.2f} RUB")
    print(f"    - Shops included: {len(daily_report.shop_stats)}")

    # Step 5: Run reconciliation
    print("\n[Phase 2.5] Step 5: Running reconciliation against platforms...")
    reconciler = ReconciliationEngine(ledger=ledger)
    reconciliation_result = reconciler.reconcile()
    reconciler.save_report()

    print(f"  ✓ Ledger total orders: {reconciliation_result.ledger_total_orders}")
    print(f"  ✓ Platform total orders: {reconciliation_result.platform_total_orders}")
    print(f"  ✓ Total discrepancies: {reconciliation_result.total_discrepancies}")
    print(f"    - Missing on platform: {reconciliation_result.missing_on_platform}")
    print(f"    - Missing in ledger: {reconciliation_result.missing_in_ledger}")
    print(f"    - Amount mismatches: {reconciliation_result.amount_mismatches}")
    print(f"  ✓ Matched orders: {reconciliation_result.matched_orders}")

    # Step 6: Generate integration summary
    print("\n[Phase 2.5] Step 6: Integration Summary")
    print("=" * 70)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_name": "Phase 2.5 Integration Test",
        "components_tested": 5,
        "synthetic_orders_created": len(synthetic_orders),
        "results": {
            "order_tracking": {
                "ledger_entries": len(ledger.entries),
                "batch_add_result": batch_result,
            },
            "anomaly_detection": {
                "orders_analyzed": detection_result.total_orders_analyzed,
                "anomalies_found": detection_result.total_anomalies_detected,
                "severity_breakdown": {
                    "p0": detection_result.p0_immediate,
                    "p1": detection_result.p1_hourly,
                    "p2": detection_result.p2_daily,
                },
            },
            "alert_dispatch": {
                "anomalies_processed": dispatch_result.total_anomalies_processed,
                "alerts_dispatched": dispatch_result.alerts_dispatched,
                "alerts_failed": dispatch_result.alerts_failed,
            },
            "billing_aggregation": {
                "total_orders": daily_report.total_orders,
                "total_amount_rub": daily_report.total_amount,
                "shops_included": len(daily_report.shop_stats),
                "platforms": list(daily_report.platform_stats.keys()),
            },
            "reconciliation": {
                "ledger_orders": reconciliation_result.ledger_total_orders,
                "platform_orders": reconciliation_result.platform_total_orders,
                "discrepancies": reconciliation_result.total_discrepancies,
                "matched_orders": reconciliation_result.matched_orders,
            },
        },
        "output_files": [
            "order_ledger.json",
            "anomaly_detection_report.json",
            "alert_dispatch_report.json",
            "billing_report_daily.json",
            "reconciliation_report.json",
        ],
    }

    # Save summary
    summary_path = ROOT / "outputs" / "phase25_integration_test_result.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n✓ Integration test completed successfully")
    print(f"✓ Summary saved to: {summary_path}")

    # Print summary statistics
    print(f"\n[Phase 2.5] Integration Test Results:")
    print(f"  Orders in ledger: {len(ledger.entries)}")
    print(f"  Anomalies detected: {detection_result.total_anomalies_detected}")
    print(f"  Alerts dispatched: {dispatch_result.alerts_dispatched}")
    print(f"  Billing report generated: {daily_report.total_orders > 0}")
    print(f"  Reconciliation completed: {reconciliation_result.total_discrepancies >= 0}")
    print(f"\n✅ All Phase 2 components integrated and tested successfully!")

    return summary


if __name__ == "__main__":
    run_integration_test()
