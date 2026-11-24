#!/usr/bin/env python3
"""Order processing dashboard for real-time monitoring.

Displays:
1. Order pipeline status (tracked/anomalies/dispatched/reconciled)
2. Shop performance metrics
3. Alert status by severity
4. Reconciliation health
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger
from order_anomaly_detector import OrderAnomalyDetector
from reconciliation_engine import ReconciliationEngine
from billing_aggregator import BillingAggregator, BillingPeriod


def render_dashboard():
    """Render order processing dashboard."""
    print("\n" + "=" * 80)
    print("ORDER PROCESSING DASHBOARD".center(80))
    print("=" * 80)

    ledger = OrderLedger()
    detector = OrderAnomalyDetector(ledger=ledger)
    reconciler = ReconciliationEngine(ledger=ledger)
    aggregator = BillingAggregator(ledger=ledger)

    # Analyze data
    anomalies = detector.detect_anomalies()
    reconciliation = reconciler.reconcile()
    billing = aggregator.aggregate_daily()

    print(f"\n📊 OVERVIEW")
    print(f"  Generated: {datetime.now(timezone.utc).isoformat()[:19]}Z")
    print(f"  Orders in Ledger: {len(ledger.entries)}")
    print(f"  Anomalies Detected: {anomalies.total_anomalies_detected}")
    print(f"  Discrepancies: {reconciliation.total_discrepancies}")

    print(f"\n🎯 ANOMALY SEVERITY")
    print(f"  P0 (Immediate): {anomalies.p0_immediate:>3} ⚠️  Critical")
    print(f"  P1 (Hourly):    {anomalies.p1_hourly:>3} 🔔 Warning")
    print(f"  P2 (Daily):     {anomalies.p2_daily:>3} ℹ️  Info")

    print(f"\n📈 ANOMALY CATEGORIES")
    print(f"  Timing:        {anomalies.timing_anomalies:>3}")
    print(f"  State Mismatch: {anomalies.state_transition_anomalies:>3}")
    print(f"  Data Quality:   {anomalies.data_quality_anomalies:>3}")
    print(f"  Reconciliation: {anomalies.reconciliation_anomalies:>3}")

    print(f"\n💰 BILLING (Today)")
    print(f"  Total Orders: {billing.total_orders}")
    print(f"  Total Amount: {billing.total_amount:>10.2f} RUB")
    print(f"  Confirmed:    {billing.confirmed_total:>10.2f} RUB")
    print(f"  Pending:      {billing.pending_total:>10.2f} RUB")

    print(f"\n🔄 RECONCILIATION STATUS")
    print(f"  Ledger Orders:     {reconciliation.ledger_total_orders:>3}")
    print(f"  Platform Orders:   {reconciliation.platform_total_orders:>3}")
    print(f"  Matched:           {reconciliation.matched_orders:>3}")
    print(f"  Discrepancies:     {reconciliation.total_discrepancies:>3}")
    print(f"    - Missing on Platform: {reconciliation.missing_on_platform:>3}")
    print(f"    - Missing in Ledger:   {reconciliation.missing_in_ledger:>3}")
    print(f"    - Amount Mismatch:     {reconciliation.amount_mismatches:>3}")

    print(f"\n🏪 SHOP BREAKDOWN")
    if billing.shop_stats:
        for shop in billing.shop_stats[:5]:
            print(f"  {shop.shop_id} ({shop.platform:>6}): {shop.total_orders:>3} orders, {shop.total_amount:>10.2f} RUB")
    else:
        print(f"  No orders today")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    render_dashboard()
