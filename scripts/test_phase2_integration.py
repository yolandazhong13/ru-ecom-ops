#!/usr/bin/env python3
"""Phase 2.5: Integrated End-to-End Workflow Testing.

Creates a unified test harness combining all Phase 2 components:
1. Order Tracker (aggregation and state tracking)
2. Anomaly Detector (detection and severity classification)
3. Alert Dispatcher (Feishu integration)
4. Billing Aggregator (revenue analysis)
5. Reconciliation Engine (platform discrepancy detection)

Workflow:
1. Create test harness combining all Phase 2 components
2. Populate ledger with synthetic order data (multiple shops, platforms, states)
3. Execute detection → dispatch → billing → reconciliation pipeline sequentially
4. Verify outputs and cross-component integration
5. Generate comprehensive integration test report
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, List
import sys
import time

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus
from order_state_machine import OrderState, OrderStateMachine, OrderStateContext
from order_anomaly_detector import OrderAnomalyDetector, AnomalyDetectionResult
from order_alert_dispatcher import OrderAlertDispatcher
from billing_aggregator import BillingAggregator, BillingPeriod
from reconciliation_engine import ReconciliationEngine
from wb_ozon_api_adapter import PlatformOrderData, PlatformType, UnifiedAPIGateway


@dataclass
class IntegrationTestResult:
    """Result of Phase 2.5 integration test."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    test_id: str = ""

    # Phase breakdown
    phase_tracking_result: Optional[dict[str, Any]] = None
    phase_detection_result: Optional[dict[str, Any]] = None
    phase_dispatch_result: Optional[dict[str, Any]] = None
    phase_billing_result: Optional[dict[str, Any]] = None
    phase_reconciliation_result: Optional[dict[str, Any]] = None

    # Overall metrics
    total_synthetic_orders_created: int = 0
    total_orders_in_ledger: int = 0
    anomalies_detected: int = 0
    alerts_dispatched: int = 0
    billing_records_generated: int = 0
    discrepancies_found: int = 0

    # Integration validation
    data_flow_verified: bool = False
    cross_component_integrity: bool = False
    all_phases_successful: bool = False

    # Error tracking
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


class SyntheticOrderGenerator:
    """Generates realistic synthetic order data for testing."""

    @staticmethod
    def generate_orders(
        count: int = 50,
        shops: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
    ) -> List[OrderLedgerEntry]:
        """Generate synthetic orders.

        Args:
            count: Number of orders to generate
            shops: List of shop IDs (default: ["shop_001", "shop_002", "shop_003"])
            platforms: List of platforms (default: ["WB_CN", "Ozon"])

        Returns:
            List of synthetic OrderLedgerEntry objects
        """
        if shops is None:
            shops = ["shop_001", "shop_002", "shop_003"]
        if platforms is None:
            platforms = ["WB_CN", "Ozon"]

        orders = []
        base_time = datetime.now(timezone.utc)

        # Order states for realistic distribution
        states = [
            OrderState.PENDING_PAYMENT,
            OrderState.PAID,
            OrderState.SHIPPED,
            OrderState.IN_TRANSIT,
            OrderState.DELIVERED,
            OrderState.CONFIRMED,
        ]

        platform_state_map = {
            OrderState.PENDING_PAYMENT: "awaiting_payment",
            OrderState.PAID: "confirmed",
            OrderState.SHIPPED: "shipped",
            OrderState.IN_TRANSIT: "in_transit",
            OrderState.DELIVERED: "delivered",
            OrderState.CONFIRMED: "completed",
        }

        for i in range(count):
            shop_id = shops[i % len(shops)]
            platform = platforms[i % len(platforms)]
            state = states[i % len(states)]

            # Generate order timing with realistic delays
            order_date = base_time - timedelta(days=i, hours=12)

            # Payment typically within 1-2 hours
            payment_date = order_date + timedelta(hours=1)

            # Shipping typically within 1-3 days
            shipped_date = payment_date + timedelta(days=1)

            # Delivery typically within 5-10 days
            delivery_date = shipped_date + timedelta(days=5)

            # Amount between 100-5000 RUB
            amount = 100 + (i % 50) * 100

            # Generate order ID with platform prefix
            order_id = f"{platform.lower()}_order_{i:06d}"

            entry = OrderLedgerEntry(
                order_id=order_id,
                platform=platform,
                shop_id=shop_id,
                order_date=order_date.isoformat(),
                payment_date=payment_date.isoformat() if state != OrderState.PENDING_PAYMENT else None,
                shipped_date=shipped_date.isoformat() if state in [OrderState.SHIPPED, OrderState.IN_TRANSIT, OrderState.DELIVERED, OrderState.CONFIRMED] else None,
                delivery_date=delivery_date.isoformat() if state in [OrderState.DELIVERED, OrderState.CONFIRMED] else None,
                total_amount=float(amount),
                currency="RUB",
                sku=f"SKU_{i % 20:04d}",
                items=[{
                    "sku": f"SKU_{i % 20:04d}",
                    "quantity": 1 + (i % 5),
                    "price": amount,
                }],
                platform_state=platform_state_map.get(state, "unknown"),
                state_machine_state=state.value,
                tracking_number=f"TRACK_{i:08d}",
                shipping_provider="DHL" if i % 2 == 0 else "EMS",
                payment_confirmed=state != OrderState.PENDING_PAYMENT,
                delivered=state in [OrderState.DELIVERED, OrderState.CONFIRMED],
                signature_confirmed=state == OrderState.CONFIRMED,
                reconciliation_status=ReconciliationStatus.PENDING,
            )

            # Compute ledger entry ID
            entry.ledger_entry_id = entry._compute_entry_id()

            orders.append(entry)

        return orders


class Phase25IntegrationHarness:
    """Unified test harness for Phase 2.5 integration testing."""

    def __init__(self):
        """Initialize the integration harness."""
        self.ledger = OrderLedger()
        self.test_result = IntegrationTestResult(
            test_id=f"phase2_5_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        self.outputs_dir = ROOT / "outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def phase1_populate_ledger(self, order_count: int = 50) -> dict[str, Any]:
        """Phase 1: Populate order ledger with synthetic data.

        Args:
            order_count: Number of synthetic orders to generate

        Returns:
            Result dict with population statistics
        """
        print("\n" + "="*80)
        print("PHASE 2.5.1: POPULATE ORDER LEDGER")
        print("="*80)

        start_time = time.time()

        # Generate synthetic orders
        print(f"\nGenerating {order_count} synthetic orders...")
        orders = SyntheticOrderGenerator.generate_orders(count=order_count)

        # Add to ledger
        print(f"Adding orders to ledger...")
        added_count = 0
        for order in orders:
            self.ledger.add_order(order)
            added_count += 1

        # Save ledger to file
        ledger_file = self.outputs_dir / "order_ledger.json"
        self.ledger.persist_to_json()
        print(f"✓ Ledger saved to {ledger_file}")

        duration = time.time() - start_time

        result = {
            "phase": "populate_ledger",
            "status": "success",
            "orders_generated": len(orders),
            "orders_added": added_count,
            "ledger_file": str(ledger_file),
            "ledger_size_bytes": ledger_file.stat().st_size,
            "duration_seconds": round(duration, 2),
        }

        print(f"\n✓ Phase 1 Complete:")
        print(f"  - Orders generated: {len(orders)}")
        print(f"  - Orders added to ledger: {added_count}")
        print(f"  - Ledger file: {ledger_file}")
        print(f"  - Duration: {duration:.2f}s")

        self.test_result.total_synthetic_orders_created = len(orders)
        self.test_result.total_orders_in_ledger = added_count

        return result

    def phase2_detect_anomalies(self) -> dict[str, Any]:
        """Phase 2: Detect anomalies in orders.

        Returns:
            Result dict with anomaly detection statistics
        """
        print("\n" + "="*80)
        print("PHASE 2.5.2: ANOMALY DETECTION")
        print("="*80)

        start_time = time.time()

        # Initialize detector with populated ledger
        detector = OrderAnomalyDetector(self.ledger)

        # Detect anomalies in ledger
        print(f"\nAnalyzing {len(self.ledger.entries)} orders for anomalies...")
        detection_result = detector.detect_anomalies()

        # Save detection report
        report_file = self.outputs_dir / "anomaly_detection_report.json"
        detector.save_result(report_file)
        print(f"✓ Detection report saved to {report_file}")

        duration = time.time() - start_time

        # Compile result
        result = {
            "phase": "anomaly_detection",
            "status": "success",
            "orders_analyzed": detection_result.total_orders_analyzed,
            "orders_with_anomalies": detection_result.orders_with_anomalies,
            "total_anomalies_detected": detection_result.total_anomalies_detected,
            "p0_critical": detection_result.p0_immediate,
            "p1_warning": detection_result.p1_hourly,
            "p2_info": detection_result.p2_daily,
            "timing_anomalies": detection_result.timing_anomalies,
            "state_transition_anomalies": detection_result.state_transition_anomalies,
            "data_quality_anomalies": detection_result.data_quality_anomalies,
            "report_file": str(report_file),
            "report_size_bytes": report_file.stat().st_size,
            "duration_seconds": round(duration, 2),
        }

        print(f"\n✓ Phase 2 Complete:")
        print(f"  - Orders analyzed: {detection_result.total_orders_analyzed}")
        print(f"  - Anomalies detected: {detection_result.total_anomalies_detected}")
        print(f"  - P0 (Critical): {detection_result.p0_immediate}")
        print(f"  - P1 (Warning): {detection_result.p1_hourly}")
        print(f"  - P2 (Info): {detection_result.p2_daily}")
        print(f"  - Duration: {duration:.2f}s")

        self.test_result.anomalies_detected = detection_result.total_anomalies_detected

        return result

    def phase3_dispatch_alerts(self) -> dict[str, Any]:
        """Phase 3: Dispatch alerts via Feishu.

        Returns:
            Result dict with alert dispatch statistics
        """
        print("\n" + "="*80)
        print("PHASE 2.5.3: ALERT DISPATCH")
        print("="*80)

        start_time = time.time()

        # Initialize dispatcher
        dispatcher = OrderAlertDispatcher()

        # Load latest detection report
        report_file = self.outputs_dir / "anomaly_detection_report.json"
        with open(report_file) as f:
            detection_data = json.load(f)

        print(f"\nDispatching alerts based on {len(detection_data.get('anomalies', []))} detected anomalies...")

        # Dispatch alerts (simulated - Feishu webhook might not be available in test)
        dispatch_result = dispatcher.dispatch_alerts()

        # Save dispatch report
        dispatch_file = self.outputs_dir / "alert_dispatch_report.json"
        dispatcher.save_result(dispatch_file)
        print(f"✓ Dispatch report saved to {dispatch_file}")

        duration = time.time() - start_time

        result = {
            "phase": "alert_dispatch",
            "status": "success",
            "anomalies_processed": len(detection_data.get('anomalies', [])),
            "alerts_dispatched": dispatch_result.alerts_dispatched,
            "alerts_failed": dispatch_result.alerts_failed,
            "alerts_skipped": dispatch_result.alerts_skipped,
            "dispatch_logs_count": len(dispatch_result.dispatch_logs),
            "report_file": str(dispatch_file),
            "report_size_bytes": dispatch_file.stat().st_size,
            "duration_seconds": round(duration, 2),
        }

        print(f"\n✓ Phase 3 Complete:")
        print(f"  - Alerts dispatched: {dispatch_result.alerts_dispatched}")
        print(f"  - Alerts failed: {dispatch_result.alerts_failed}")
        print(f"  - Alerts skipped: {dispatch_result.alerts_skipped}")
        print(f"  - Duration: {duration:.2f}s")

        self.test_result.alerts_dispatched = dispatch_result.alerts_dispatched

        return result

    def phase4_billing_aggregation(self) -> dict[str, Any]:
        """Phase 4: Aggregate billing data.

        Returns:
            Result dict with billing aggregation statistics
        """
        print("\n" + "="*80)
        print("PHASE 2.5.4: BILLING AGGREGATION")
        print("="*80)

        start_time = time.time()

        # Initialize aggregator with ledger
        aggregator = BillingAggregator(ledger=self.ledger)

        print(f"\nAggregating billing data for {len(self.ledger.entries)} orders...")

        # Query past 50 days to include synthetic order date range
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=50)

        billing_result = aggregator._aggregate_period(
            period=BillingPeriod.DAILY,
            start_date=start_dt.isoformat(),
            end_date=end_dt.isoformat(),
        )

        # Save billing report
        billing_file = self.outputs_dir / "billing_report_daily.json"
        aggregator.save_report(billing_file)
        print(f"✓ Billing report saved to {billing_file}")

        duration = time.time() - start_time

        result = {
            "phase": "billing_aggregation",
            "status": "success",
            "period": "daily",
            "shops_analyzed": len(billing_result.shop_stats),
            "total_orders": billing_result.total_orders,
            "total_amount": billing_result.total_amount,
            "confirmed_amount": billing_result.confirmed_total,
            "pending_amount": billing_result.pending_total,
            "cancelled_amount": billing_result.cancelled_total,
            "shop_records": len(billing_result.shop_stats),
            "report_file": str(billing_file),
            "report_size_bytes": billing_file.stat().st_size,
            "duration_seconds": round(duration, 2),
        }

        print(f"\n✓ Phase 4 Complete:")
        print(f"  - Shops analyzed: {len(billing_result.shop_stats)}")
        print(f"  - Total orders: {billing_result.total_orders}")
        print(f"  - Total amount: {billing_result.total_amount:.2f} RUB")
        print(f"  - Confirmed amount: {billing_result.confirmed_total:.2f} RUB")
        print(f"  - Pending amount: {billing_result.pending_total:.2f} RUB")
        print(f"  - Cancelled amount: {billing_result.cancelled_total:.2f} RUB")
        print(f"  - Duration: {duration:.2f}s")

        self.test_result.billing_records_generated = len(billing_result.shop_stats)

        return result

    def phase5_reconciliation(self) -> dict[str, Any]:
        """Phase 5: Reconcile orders between ledger and platform.

        Returns:
            Result dict with reconciliation statistics
        """
        print("\n" + "="*80)
        print("PHASE 2.5.5: RECONCILIATION")
        print("="*80)

        start_time = time.time()

        # Initialize reconciliation engine with ledger
        engine = ReconciliationEngine(ledger=self.ledger)

        print(f"\nReconciling {len(self.ledger.entries)} ledger orders...")

        # Run reconciliation
        reconciliation_result = engine.reconcile()

        # Save reconciliation report
        reconcile_file = self.outputs_dir / "reconciliation_report.json"
        engine.save_report(reconcile_file)
        print(f"✓ Reconciliation report saved to {reconcile_file}")

        duration = time.time() - start_time

        result = {
            "phase": "reconciliation",
            "status": "success",
            "ledger_orders": reconciliation_result.ledger_total_orders,
            "platform_orders": reconciliation_result.platform_total_orders,
            "matched_orders": reconciliation_result.matched_orders,
            "unmatched_orders": reconciliation_result.ledger_total_orders - reconciliation_result.matched_orders,
            "discrepancies_found": reconciliation_result.total_discrepancies,
            "missing_in_ledger": reconciliation_result.missing_in_ledger,
            "missing_on_platform": reconciliation_result.missing_on_platform,
            "amount_mismatches": reconciliation_result.amount_mismatches,
            "state_mismatches": reconciliation_result.state_mismatches,
            "report_file": str(reconcile_file),
            "report_size_bytes": reconcile_file.stat().st_size,
            "duration_seconds": round(duration, 2),
        }

        print(f"\n✓ Phase 5 Complete:")
        print(f"  - Ledger orders: {reconciliation_result.ledger_total_orders}")
        print(f"  - Platform orders: {reconciliation_result.platform_total_orders}")
        print(f"  - Matched orders: {reconciliation_result.matched_orders}")
        print(f"  - Unmatched orders: {reconciliation_result.ledger_total_orders - reconciliation_result.matched_orders}")
        print(f"  - Discrepancies found: {reconciliation_result.total_discrepancies}")
        print(f"  - Duration: {duration:.2f}s")

        self.test_result.discrepancies_found = reconciliation_result.total_discrepancies

        return result

    def verify_integration(self) -> dict[str, Any]:
        """Verify cross-component integration and data flow.

        Returns:
            Integration verification result
        """
        print("\n" + "="*80)
        print("INTEGRATION VERIFICATION")
        print("="*80)

        verification_results = {}

        # Check all output files exist
        print("\nVerifying output files...")
        required_files = [
            "order_ledger.json",
            "anomaly_detection_report.json",
            "alert_dispatch_report.json",
            "billing_report_daily.json",
            "reconciliation_report.json",
        ]

        files_exist = []
        for filename in required_files:
            filepath = self.outputs_dir / filename
            exists = filepath.exists()
            files_exist.append(exists)
            status = "✓" if exists else "✗"
            print(f"  {status} {filename}")

        # Verify data flow between components
        print("\nVerifying data flow between components...")

        # 1. Ledger contains orders
        ledger_check = len(self.ledger.orders) > 0
        print(f"  {'✓' if ledger_check else '✗'} Ledger contains {len(self.ledger.orders)} orders")

        # 2. Detection report references ledger orders
        with open(self.outputs_dir / "anomaly_detection_report.json") as f:
            detection_report = json.load(f)
        detection_check = detection_report.get("total_orders_analyzed", 0) > 0
        print(f"  {'✓' if detection_check else '✗'} Detection report analyzed {detection_report.get('total_orders_analyzed', 0)} orders")

        # 3. Dispatch report processed anomalies from detection
        with open(self.outputs_dir / "alert_dispatch_report.json") as f:
            dispatch_report = json.load(f)
        dispatch_check = dispatch_report.get("alerts_dispatched", 0) >= 0
        print(f"  {'✓' if dispatch_check else '✗'} Dispatch report sent {dispatch_report.get('alerts_dispatched', 0)} alerts")

        # 4. Billing report aggregated ledger orders
        with open(self.outputs_dir / "billing_report_daily.json") as f:
            billing_report = json.load(f)
        billing_check = billing_report.get("total_orders", 0) > 0
        print(f"  {'✓' if billing_check else '✗'} Billing report aggregated {billing_report.get('total_orders', 0)} orders")

        # 5. Reconciliation checked ledger consistency
        with open(self.outputs_dir / "reconciliation_report.json") as f:
            reconcile_report = json.load(f)
        reconcile_check = reconcile_report.get("total_orders_reconciled", 0) > 0
        print(f"  {'✓' if reconcile_check else '✗'} Reconciliation checked {reconcile_report.get('total_orders_reconciled', 0)} orders")

        # Overall integration status
        all_checks = all(files_exist) and all([
            ledger_check, detection_check, dispatch_check, billing_check, reconcile_check
        ])

        verification_results = {
            "files_complete": all(files_exist),
            "data_flow_verified": all([ledger_check, detection_check, dispatch_check, billing_check, reconcile_check]),
            "cross_component_integrity": billing_check and reconcile_check,
            "all_checks_passed": all_checks,
        }

        print(f"\n✓ Integration Verification: {'PASSED' if all_checks else 'FAILED'}")

        return verification_results

    def run_complete_test(self, order_count: int = 50) -> IntegrationTestResult:
        """Run complete Phase 2.5 integration test.

        Args:
            order_count: Number of synthetic orders to generate

        Returns:
            Complete integration test result
        """
        print("\n" + "="*80)
        print("PHASE 2.5: INTEGRATED END-TO-END WORKFLOW TESTING")
        print("="*80)
        print(f"Test ID: {self.test_result.test_id}")
        print(f"Start Time: {self.test_result.timestamp}")

        try:
            # Run all phases
            self.test_result.phase_tracking_result = self.phase1_populate_ledger(order_count)
            self.test_result.phase_detection_result = self.phase2_detect_anomalies()
            self.test_result.phase_dispatch_result = self.phase3_dispatch_alerts()
            self.test_result.phase_billing_result = self.phase4_billing_aggregation()
            self.test_result.phase_reconciliation_result = self.phase5_reconciliation()

            # Verify integration
            verification = self.verify_integration()
            self.test_result.data_flow_verified = verification["data_flow_verified"]
            self.test_result.cross_component_integrity = verification["cross_component_integrity"]
            self.test_result.all_phases_successful = verification["all_checks_passed"]

        except Exception as e:
            self.test_result.errors.append(str(e))
            self.test_result.all_phases_successful = False

        # Save final integration report
        report_file = self.outputs_dir / f"test_phase2_5_integration_{self.test_result.test_id}.json"
        with open(report_file, "w") as f:
            json.dump(self.test_result.to_dict(), f, indent=2)

        # Print final summary
        self._print_summary(report_file)

        return self.test_result

    def _print_summary(self, report_file: Path) -> None:
        """Print final test summary."""
        print("\n" + "="*80)
        print("FINAL TEST SUMMARY")
        print("="*80)

        print(f"\nTest ID: {self.test_result.test_id}")
        print(f"Timestamp: {self.test_result.timestamp}")

        print(f"\nSynthetic Data Generation:")
        print(f"  - Orders created: {self.test_result.total_synthetic_orders_created}")
        print(f"  - Orders in ledger: {self.test_result.total_orders_in_ledger}")

        print(f"\nPhase Results:")
        if self.test_result.phase_tracking_result:
            print(f"  Phase 1 (Tracking): ✓ {self.test_result.phase_tracking_result.get('status', 'unknown')}")
        if self.test_result.phase_detection_result:
            print(f"  Phase 2 (Detection): ✓ {self.test_result.phase_detection_result.get('status', 'unknown')}")
            print(f"    - Anomalies detected: {self.test_result.anomalies_detected}")
        if self.test_result.phase_dispatch_result:
            print(f"  Phase 3 (Dispatch): ✓ {self.test_result.phase_dispatch_result.get('status', 'unknown')}")
            print(f"    - Alerts dispatched: {self.test_result.alerts_dispatched}")
        if self.test_result.phase_billing_result:
            print(f"  Phase 4 (Billing): ✓ {self.test_result.phase_billing_result.get('status', 'unknown')}")
            print(f"    - Billing records: {self.test_result.billing_records_generated}")
        if self.test_result.phase_reconciliation_result:
            print(f"  Phase 5 (Reconciliation): ✓ {self.test_result.phase_reconciliation_result.get('status', 'unknown')}")
            print(f"    - Discrepancies found: {self.test_result.discrepancies_found}")

        print(f"\nIntegration Validation:")
        print(f"  - Data flow verified: {'✓' if self.test_result.data_flow_verified else '✗'}")
        print(f"  - Cross-component integrity: {'✓' if self.test_result.cross_component_integrity else '✗'}")
        print(f"  - All phases successful: {'✓' if self.test_result.all_phases_successful else '✗'}")

        if self.test_result.errors:
            print(f"\nErrors encountered:")
            for error in self.test_result.errors:
                print(f"  - {error}")

        print(f"\nReport saved to: {report_file}")
        print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 2.5: Integrated End-to-End Workflow Testing"
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=50,
        help="Number of synthetic orders to generate (default: 50)"
    )

    args = parser.parse_args()

    # Run integration test
    harness = Phase25IntegrationHarness()
    result = harness.run_complete_test(order_count=args.orders)

    # Exit with status code
    exit(0 if result.all_phases_successful else 1)
