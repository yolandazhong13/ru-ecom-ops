#!/usr/bin/env python3
"""Order processing workflow orchestrator.

Automated daily workflow:
1. Track orders from all platforms
2. Detect anomalies
3. Dispatch alerts
4. Generate billing reports
5. Reconcile with platforms
6. Update dashboard

Runs complete pipeline with error handling and reporting.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_tracker import OrderTracker
from order_anomaly_detector import OrderAnomalyDetector
from order_alert_dispatcher import OrderAlertDispatcher
from billing_aggregator import BillingAggregator
from reconciliation_engine import ReconciliationEngine


def run_daily_workflow():
    """Execute daily order processing workflow."""
    workflow_start = datetime.now(timezone.utc)

    print("\n" + "=" * 70)
    print("DAILY ORDER PROCESSING WORKFLOW".center(70))
    print("=" * 70)

    workflow_log = {
        "timestamp": workflow_start.isoformat(),
        "steps": [],
    }

    try:
        # Step 1: Track orders
        print("\n[Workflow] Step 1: Tracking orders from platforms...")
        tracker = OrderTracker()
        track_result = tracker.sync_orders_from_platform()
        tracker.persist_ledger()

        step1 = {
            "step": "order_tracking",
            "status": "completed",
            "fetched": track_result.total_fetched,
            "processed": track_result.total_processed,
            "failed": track_result.total_failed,
            "new_orders": track_result.total_new,
            "updated_orders": track_result.total_updated,
            "anomalies": track_result.total_anomalies,
        }
        workflow_log["steps"].append(step1)
        print(f"  ✓ Fetched: {track_result.total_fetched}, Processed: {track_result.total_processed}")

        # Step 2: Detect anomalies
        print("\n[Workflow] Step 2: Detecting anomalies...")
        detector = OrderAnomalyDetector(ledger=tracker.ledger)
        anomaly_result = detector.detect_anomalies()
        detector.save_result()

        step2 = {
            "step": "anomaly_detection",
            "status": "completed",
            "total_analyzed": anomaly_result.total_orders_analyzed,
            "anomalies_found": anomaly_result.total_anomalies_detected,
            "p0_count": anomaly_result.p0_immediate,
            "p1_count": anomaly_result.p1_hourly,
            "p2_count": anomaly_result.p2_daily,
        }
        workflow_log["steps"].append(step2)
        print(f"  ✓ Found {anomaly_result.total_anomalies_detected} anomalies (P0: {anomaly_result.p0_immediate}, P1: {anomaly_result.p1_hourly})")

        # Step 3: Dispatch alerts
        print("\n[Workflow] Step 3: Dispatching alerts...")
        dispatcher = OrderAlertDispatcher()
        dispatch_result = dispatcher.dispatch_alerts()
        dispatcher.save_result()

        step3 = {
            "step": "alert_dispatch",
            "status": "completed",
            "alerts_dispatched": dispatch_result.alerts_dispatched,
            "alerts_failed": dispatch_result.alerts_failed,
        }
        workflow_log["steps"].append(step3)
        print(f"  ✓ Dispatched {dispatch_result.alerts_dispatched} alerts")

        # Step 4: Generate billing
        print("\n[Workflow] Step 4: Generating billing reports...")
        aggregator = BillingAggregator(ledger=tracker.ledger)
        billing_result = aggregator.aggregate_daily()
        aggregator.save_report()

        step4 = {
            "step": "billing_aggregation",
            "status": "completed",
            "total_orders": billing_result.total_orders,
            "total_amount": billing_result.total_amount,
            "shops_included": len(billing_result.shop_stats),
        }
        workflow_log["steps"].append(step4)
        print(f"  ✓ Aggregated {billing_result.total_orders} orders, {billing_result.total_amount:.2f} RUB")

        # Step 5: Reconcile
        print("\n[Workflow] Step 5: Reconciling with platforms...")
        reconciler = ReconciliationEngine(ledger=tracker.ledger)
        reconciliation_result = reconciler.reconcile()
        reconciler.save_report()

        step5 = {
            "step": "reconciliation",
            "status": "completed",
            "ledger_orders": reconciliation_result.ledger_total_orders,
            "platform_orders": reconciliation_result.platform_total_orders,
            "discrepancies": reconciliation_result.total_discrepancies,
            "matched": reconciliation_result.matched_orders,
        }
        workflow_log["steps"].append(step5)
        print(f"  ✓ Reconciled {reconciliation_result.matched_orders} matches, {reconciliation_result.total_discrepancies} discrepancies")

        workflow_duration = (datetime.now(timezone.utc) - workflow_start).total_seconds()

        # Summary
        print("\n" + "=" * 70)
        print("WORKFLOW SUMMARY".center(70))
        print("=" * 70)
        print(f"Status: ✅ COMPLETED")
        print(f"Duration: {workflow_duration:.2f}s")
        print(f"Orders Processed: {track_result.total_processed}")
        print(f"Anomalies Detected: {anomaly_result.total_anomalies_detected}")
        print(f"Alerts Dispatched: {dispatch_result.alerts_dispatched}")
        print(f"Reconciliation Discrepancies: {reconciliation_result.total_discrepancies}")
        print("=" * 70 + "\n")

        # Save workflow log
        workflow_log["status"] = "success"
        workflow_log["duration_seconds"] = workflow_duration

        log_path = ROOT / "outputs" / "workflow_log_daily.json"
        log_path.write_text(json.dumps(workflow_log, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Workflow log saved to: {log_path}")

        return workflow_log

    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        workflow_log["status"] = "failed"
        workflow_log["error"] = str(e)

        log_path = ROOT / "outputs" / "workflow_log_daily.json"
        log_path.write_text(json.dumps(workflow_log, indent=2, ensure_ascii=False), encoding="utf-8")
        raise


if __name__ == "__main__":
    run_daily_workflow()
