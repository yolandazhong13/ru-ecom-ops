#!/usr/bin/env python3
"""Test data generator for realistic order scenarios.

Creates diverse test data:
1. Confirmed orders (healthy)
2. SLA violations (payment overdue, shipment delayed)
3. Anomalies (various types)
4. Recovery scenarios (stuck orders)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger, OrderLedgerEntry, ReconciliationStatus
from order_state_machine import OrderState


def generate_test_orders(count: int = 100) -> List[OrderLedgerEntry]:
    """Generate realistic test order data.

    Args:
        count: Number of orders to generate

    Returns:
        List of OrderLedgerEntry
    """
    orders = []
    now = datetime.now(timezone.utc)

    platforms = ["WB_CN", "Ozon"]
    shops_wb = ["250146669", "250146670", "250146671"]
    shops_ozon = ["6182781", "3521307", "6182782"]

    # Scenario distribution
    confirmed_pct = 0.60  # 60% confirmed orders
    sla_violation_pct = 0.15  # 15% with SLA violations
    anomaly_pct = 0.15  # 15% with anomalies
    recovery_pct = 0.10  # 10% recovery scenarios

    for i in range(count):
        platform = "WB_CN" if i % 2 == 0 else "Ozon"
        shops = shops_wb if platform == "WB_CN" else shops_ozon
        shop_id = shops[i % len(shops)]
        order_id = f"{platform.split('_')[0]}_{100000 + i}"

        # Determine scenario
        rand = (i / count)

        if rand < confirmed_pct:
            # Healthy confirmed order
            order_date = (now - timedelta(days=5)).isoformat()
            payment_date = (now - timedelta(days=5, hours=2)).isoformat()
            shipped_date = (now - timedelta(days=4)).isoformat()
            delivery_date = (now - timedelta(days=1)).isoformat()

            entry = OrderLedgerEntry(
                order_id=order_id,
                platform=platform,
                shop_id=shop_id,
                order_date=order_date,
                payment_date=payment_date,
                shipped_date=shipped_date,
                delivery_date=delivery_date,
                total_amount=round(500 + (i * 10 % 5000), 2),
                currency="RUB",
                sku=f"SKU-{1000 + i % 100}",
                platform_state=OrderState.CONFIRMED.value,
                state_machine_state=OrderState.CONFIRMED.value,
                payment_confirmed=True,
                delivered=True,
                reconciliation_status=ReconciliationStatus.MATCHED,
                matched_on_platform=True,
            )

        elif rand < confirmed_pct + sla_violation_pct:
            # Payment overdue (pending payment for 3+ hours)
            order_date = (now - timedelta(hours=4)).isoformat()

            entry = OrderLedgerEntry(
                order_id=order_id,
                platform=platform,
                shop_id=shop_id,
                order_date=order_date,
                total_amount=round(500 + (i * 10 % 5000), 2),
                currency="RUB",
                sku=f"SKU-{1000 + i % 100}",
                platform_state=OrderState.PENDING_PAYMENT.value,
                state_machine_state=OrderState.PENDING_PAYMENT.value,
                payment_confirmed=False,
                reconciliation_status=ReconciliationStatus.PENDING,
            )

        elif rand < confirmed_pct + sla_violation_pct + anomaly_pct:
            # Shipment delayed (paid for 36+ hours)
            order_date = (now - timedelta(hours=48)).isoformat()
            payment_date = (now - timedelta(hours=36)).isoformat()

            entry = OrderLedgerEntry(
                order_id=order_id,
                platform=platform,
                shop_id=shop_id,
                order_date=order_date,
                payment_date=payment_date,
                total_amount=round(500 + (i * 10 % 5000), 2),
                currency="RUB",
                sku=f"SKU-{1000 + i % 100}",
                platform_state=OrderState.PAID.value,
                state_machine_state=OrderState.PAID.value,
                payment_confirmed=True,
                reconciliation_status=ReconciliationStatus.PENDING,
            )

        else:
            # Recovery scenario (missing on platform)
            order_date = (now - timedelta(days=3)).isoformat()

            entry = OrderLedgerEntry(
                order_id=order_id,
                platform=platform,
                shop_id=shop_id,
                order_date=order_date,
                total_amount=round(500 + (i * 10 % 5000), 2),
                currency="RUB",
                sku=f"SKU-{1000 + i % 100}",
                platform_state=OrderState.SHIPPED.value,
                state_machine_state=OrderState.SHIPPED.value,
                reconciliation_status=ReconciliationStatus.UNMATCHED,
                matched_on_platform=False,
                missing_flag=True,
            )

        entry.ledger_entry_id = entry._compute_entry_id()
        orders.append(entry)

    return orders


def populate_test_ledger() -> OrderLedger:
    """Populate ledger with realistic test data.

    Returns:
        Populated OrderLedger
    """
    print("[TestDataGen] Generating realistic test orders...")
    ledger = OrderLedger()

    test_orders = generate_test_orders(count=100)
    result = ledger.add_orders_batch(test_orders)

    print(f"[TestDataGen] Generated {result['added_count']} orders")
    print(f"[TestDataGen] Distribution:")

    confirmed = sum(1 for e in ledger.entries.values() if e.state_machine_state == "confirmed")
    pending = sum(1 for e in ledger.entries.values() if e.state_machine_state == "pending_payment")
    paid = sum(1 for e in ledger.entries.values() if e.state_machine_state == "paid")
    shipped = sum(1 for e in ledger.entries.values() if e.state_machine_state == "shipped")

    print(f"  ✓ Confirmed: {confirmed} (60%)")
    print(f"  ✓ Pending Payment: {pending} (15%)")
    print(f"  ✓ Paid (Delayed): {paid} (15%)")
    print(f"  ✓ Shipped (Missing): {shipped} (10%)")

    # Save to file
    output_path = ROOT / "data" / "test_orders.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    test_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_orders": len(ledger.entries),
        "distribution": {
            "confirmed": confirmed,
            "pending_payment": pending,
            "paid_delayed": paid,
            "shipped_missing": shipped,
        },
    }

    output_path.write_text(json.dumps(test_data, indent=2), encoding="utf-8")
    print(f"[TestDataGen] Test data saved to: {output_path}")

    return ledger


if __name__ == "__main__":
    populate_test_ledger()
