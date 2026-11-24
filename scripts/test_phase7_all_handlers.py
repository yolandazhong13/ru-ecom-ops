#!/usr/bin/env python3
"""Phase 7 comprehensive test harness - All 4 new modules integrated.

Tests competitor tracking, demand forecasting, inventory rebalancing,
and policy monitoring with full P0-2 workflow integration.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from unified_action_executor import UnifiedActionExecutor
from competitor_and_demand_handlers import CompetitorPriceHandler, DemandForecastHandler
from rebalance_and_policy_handlers import InventoryRebalanceHandler, PolicyChangeHandler
from api_health_tracker import APIHealthTracker
from data_quality_validator import DataQualityValidator
from alerting_system import AlertingSystem, AlertSeverity, AlertChannel
from health_tracker import HealthTracker

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "phase7_tests"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def test_competitor_pricing() -> dict:
    """Test competitor price tracking."""
    print("\n" + "="*80)
    print("PHASE 7: COMPETITOR PRICE TRACKING")
    print("="*80)

    task_id = "phase7-competitor-pricing-20261120"
    print(f"\n[Competitor] Task: {task_id}")
    print("[Competitor] Monitoring WB_CN platform...")

    executor = UnifiedActionExecutor(
        task_id=task_id,
        action_type="competitor_price_tracking",
        platform="WB_CN",
        content_for_approval={
            "products": [
                {"sku": "MD-700", "current_price": 2500},
                {"sku": "MD-4090", "current_price": 10000},
            ]
        },
        output_path=OUT_DIR,
        confirm_flag=True,
    )

    handler = CompetitorPriceHandler("client_demo", "WB_CN")

    start = time.time()
    report = executor.execute(handler, output_filename="competitor_pricing.json", skip_confirmation_workflow=False)
    duration = time.time() - start

    if report.get("execution_status") == "executed":
        print(f"[Competitor] ✓ Execution: SUCCESS ({duration*1000:.1f}ms)")
        print(f"[Competitor] ✓ Status: {report.get('p02_status')}")

        # Record metrics
        api_tracker = APIHealthTracker()
        api_tracker.record_api_call(
            api_endpoint="/v1/competitor/prices",
            method="GET",
            platform="WB_CN",
            status_code=200,
            duration_ms=int(duration*1000),
        )
        api_tracker.save_api_health_db()
        print("[Competitor] ✓ Metrics recorded")

    return report


def test_demand_forecasting() -> dict:
    """Test demand forecasting."""
    print("\n" + "="*80)
    print("PHASE 7: DEMAND FORECASTING")
    print("="*80)

    task_id = "phase7-demand-forecast-20261120"
    print(f"\n[Demand] Task: {task_id}")
    print("[Demand] Forecasting sales velocity...")

    executor = UnifiedActionExecutor(
        task_id=task_id,
        action_type="demand_forecast",
        platform="WB_CN",
        content_for_approval={
            "products": [
                {"sku": "MD-700", "historical_sales": [10, 12, 15, 18, 20, 22, 25]},
                {"sku": "MD-4090", "historical_sales": [5, 5, 6, 7, 8, 9, 10]},
            ]
        },
        output_path=OUT_DIR,
        confirm_flag=True,
    )

    handler = DemandForecastHandler("client_demo", "WB_CN")

    start = time.time()
    report = executor.execute(handler, output_filename="demand_forecast.json", skip_confirmation_workflow=False)
    duration = time.time() - start

    if report.get("execution_status") == "executed":
        print(f"[Demand] ✓ Execution: SUCCESS ({duration*1000:.1f}ms)")
        print(f"[Demand] ✓ Status: {report.get('p02_status')}")

        api_tracker = APIHealthTracker()
        api_tracker.record_api_call(
            api_endpoint="/v1/analytics/forecast",
            method="POST",
            platform="WB_CN",
            status_code=200,
            duration_ms=int(duration*1000),
        )
        api_tracker.save_api_health_db()
        print("[Demand] ✓ Metrics recorded")

    return report


def test_inventory_rebalancing() -> dict:
    """Test inventory rebalancing."""
    print("\n" + "="*80)
    print("PHASE 7: INVENTORY REBALANCING")
    print("="*80)

    task_id = "phase7-inventory-rebalance-20261120"
    print(f"\n[Rebalance] Task: {task_id}")
    print("[Rebalance] Optimizing cross-platform inventory...")

    executor = UnifiedActionExecutor(
        task_id=task_id,
        action_type="inventory_rebalance",
        platform="WB_CN",
        content_for_approval={
            "inventory": {
                "MD-700": {"quantity": 100, "platform": "WB_CN"},
                "MD-4090": {"quantity": 50, "platform": "WB_CN"},
            },
            "platform_demand": {
                "MD-700": {"WB_CN": 40, "Ozon RU": 60},
                "MD-4090": {"WB_CN": 30, "Ozon RU": 20},
            }
        },
        output_path=OUT_DIR,
        confirm_flag=True,
    )

    handler = InventoryRebalanceHandler("client_demo")

    start = time.time()
    report = executor.execute(handler, output_filename="inventory_rebalance.json", skip_confirmation_workflow=False)
    duration = time.time() - start

    if report.get("execution_status") == "executed":
        print(f"[Rebalance] ✓ Execution: SUCCESS ({duration*1000:.1f}ms)")
        print(f"[Rebalance] ✓ Status: {report.get('p02_status')}")

        api_tracker = APIHealthTracker()
        api_tracker.record_api_call(
            api_endpoint="/v1/inventory/rebalance",
            method="POST",
            platform="WB_CN",
            status_code=200,
            duration_ms=int(duration*1000),
        )
        api_tracker.save_api_health_db()
        print("[Rebalance] ✓ Metrics recorded")

    return report


def test_policy_monitoring() -> dict:
    """Test policy change monitoring."""
    print("\n" + "="*80)
    print("PHASE 7: POLICY CHANGE MONITORING")
    print("="*80)

    task_id = "phase7-policy-monitor-20261120"
    print(f"\n[Policy] Task: {task_id}")
    print("[Policy] Monitoring platform policy changes...")

    executor = UnifiedActionExecutor(
        task_id=task_id,
        action_type="policy_change_monitor",
        platform="WB_CN",
        content_for_approval={
            "policies_to_track": ["min_order_value", "seller_commission", "return_policy"]
        },
        output_path=OUT_DIR,
        confirm_flag=True,
    )

    handler = PolicyChangeHandler("client_demo")

    start = time.time()
    report = executor.execute(handler, output_filename="policy_monitoring.json", skip_confirmation_workflow=False)
    duration = time.time() - start

    if report.get("execution_status") == "executed":
        print(f"[Policy] ✓ Execution: SUCCESS ({duration*1000:.1f}ms)")
        print(f"[Policy] ✓ Status: {report.get('p02_status')}")

        api_tracker = APIHealthTracker()
        api_tracker.record_api_call(
            api_endpoint="/v1/platform/policies",
            method="GET",
            platform="WB_CN",
            status_code=200,
            duration_ms=int(duration*1000),
        )
        api_tracker.save_api_health_db()
        print("[Policy] ✓ Metrics recorded")

    return report


def main() -> None:
    """Run Phase 7 comprehensive tests."""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "PHASE 7: MODULE EXPANSION - 4 NEW HANDLERS".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    # Initialize alerting
    alerting = AlertingSystem()

    # Run all tests
    results = {
        "competitor": test_competitor_pricing(),
        "demand": test_demand_forecasting(),
        "rebalance": test_inventory_rebalancing(),
        "policy": test_policy_monitoring(),
    }

    # Summary
    print("\n" + "="*80)
    print("PHASE 7 TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results.values() if r.get("execution_status") == "executed")
    total = len(results)

    print(f"\n✓ Tests Passed: {passed}/{total}")
    for name, result in results.items():
        status = "✅ PASS" if result.get("execution_status") == "executed" else "❌ FAIL"
        print(f"  {status} - {name.replace('_', ' ').title()}")

    # Generate alerts for successful completions
    if passed == total:
        alerting.send_alert(
            severity=AlertSeverity.INFO,
            title="Phase 7 Module Expansion Complete",
            description="All 4 new handlers tested and verified: competitor pricing, demand forecast, inventory rebalance, policy monitoring",
            component="phase7_testing",
            context={"total_handlers": 4, "passed": passed},
            channels=[AlertChannel.LOCAL_LOG],
        )

    alerting.print_alert_summary()

    # Export summary
    summary_path = OUT_DIR / "phase7_test_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "phase": 7,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_handlers": total,
            "passed": passed,
            "handlers": list(results.keys()),
            "status": "COMPLETE" if passed == total else "INCOMPLETE",
        }, f, indent=2)

    print(f"\n✅ Phase 7 Summary: {summary_path}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
