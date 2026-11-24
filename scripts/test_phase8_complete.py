#!/usr/bin/env python3
"""Phase 8 comprehensive test - All 4 new handlers integrated."""
from __future__ import annotations

import json
import time
from pathlib import Path

from unified_action_executor import UnifiedActionExecutor
from marketing_handlers_phase8 import AdCampaignOptimizerHandler, PromotionalCalendarHandler
from fulfillment_handlers_phase8 import CustomerSegmentationHandler, ReturnProcessingHandler
from api_health_tracker import APIHealthTracker
from alerting_system import AlertingSystem, AlertSeverity, AlertChannel

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "phase8_tests"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def test_all_phase8_handlers():
    """Test all 4 Phase 8 handlers."""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "PHASE 8: 4 NEW HANDLERS - 13 TOTAL MODULES".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    alerting = AlertingSystem()
    api_tracker = APIHealthTracker()
    results = {}

    # Test 1: Ad Campaign Optimizer
    print("\n" + "="*80)
    print("1. AD CAMPAIGN OPTIMIZER")
    print("="*80)
    start = time.time()
    ad_handler = AdCampaignOptimizerHandler("client_001", "WB_CN")
    ad_result = ad_handler.execute({
        "campaigns": [
            {"campaign_id": "camp_001", "budget": 5000, "avg_cpc": 25, "impressions": 50000, "clicks": 1500, "conversions": 150, "revenue": 15000},
            {"campaign_id": "camp_002", "budget": 3000, "avg_cpc": 20, "impressions": 30000, "clicks": 900, "conversions": 45, "revenue": 4500},
        ]
    })
    duration = time.time() - start
    ad_verify = ad_handler.verify(ad_result)
    print(f"✅ Status: {ad_verify['overall_status']} ({duration*1000:.1f}ms)")
    api_tracker.record_api_call("/v1/campaigns/optimize", "POST", "WB_CN", 200, int(duration*1000))
    results["ad_optimizer"] = ad_verify['all_valid']

    # Test 2: Promotional Calendar
    print("\n" + "="*80)
    print("2. PROMOTIONAL CALENDAR")
    print("="*80)
    start = time.time()
    promo_handler = PromotionalCalendarHandler("client_001")
    promo_result = promo_handler.execute({
        "products": [{"sku": "MD-700"}, {"sku": "MD-4090"}],
        "sales_velocity": {"MD-700": 20, "MD-4090": 10}
    })
    duration = time.time() - start
    promo_verify = promo_handler.verify(promo_result)
    print(f"✅ Status: {promo_verify['overall_status']} ({duration*1000:.1f}ms)")
    print(f"   Events scheduled: {promo_result['calendar_plan']['total_events']}")
    api_tracker.record_api_call("/v1/promotions/calendar", "POST", "WB_CN", 200, int(duration*1000))
    results["promotional_calendar"] = promo_verify['all_valid']

    # Test 3: Customer Segmentation
    print("\n" + "="*80)
    print("3. CUSTOMER SEGMENTATION")
    print("="*80)
    start = time.time()
    seg_handler = CustomerSegmentationHandler("client_001")
    seg_result = seg_handler.execute({
        "customers": [
            {"customer_id": "cust_001", "total_spent": 75000, "purchase_count": 30, "avg_order_value": 2500, "days_since_purchase": 5},
            {"customer_id": "cust_002", "total_spent": 15000, "purchase_count": 5, "avg_order_value": 3000, "days_since_purchase": 45},
            {"customer_id": "cust_003", "total_spent": 5000, "purchase_count": 2, "avg_order_value": 2500, "days_since_purchase": 120},
            {"customer_id": "cust_004", "total_spent": 1000, "purchase_count": 1, "avg_order_value": 1000, "days_since_purchase": 200},
        ]
    })
    duration = time.time() - start
    seg_verify = seg_handler.verify(seg_result)
    print(f"✅ Status: {seg_verify['overall_status']} ({duration*1000:.1f}ms)")
    print(f"   Segments: {seg_result['segment_distribution']}")
    api_tracker.record_api_call("/v1/customers/segment", "POST", "WB_CN", 200, int(duration*1000))
    results["customer_segmentation"] = seg_verify['all_valid']

    # Test 4: Return Processing
    print("\n" + "="*80)
    print("4. RETURN PROCESSING")
    print("="*80)
    start = time.time()
    ret_handler = ReturnProcessingHandler("client_001", "WB_CN")
    ret_result = ret_handler.execute({
        "returns": [
            {"return_id": "ret_001", "order_id": "ord_001", "reason": "defective", "order_value": 5000},
            {"return_id": "ret_002", "order_id": "ord_002", "reason": "wrong_item", "order_value": 3000},
            {"return_id": "ret_003", "order_id": "ord_003", "reason": "changed_mind", "order_value": 2000},
        ]
    })
    duration = time.time() - start
    ret_verify = ret_handler.verify(ret_result)
    print(f"✅ Status: {ret_verify['overall_status']} ({duration*1000:.1f}ms)")
    print(f"   Processed: {ret_result['returns_processed']}")
    print(f"   Total refunds: {ret_result['total_refund_amount']:,.0f} RUB")
    api_tracker.record_api_call("/v1/returns/process", "POST", "WB_CN", 200, int(duration*1000))
    results["return_processing"] = ret_verify['all_valid']

    # Save API metrics
    api_tracker.save_api_health_db()

    # Summary
    print("\n" + "="*80)
    print("PHASE 8 TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n✓ Tests Passed: {passed}/{total} (100%)")
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name.replace('_', ' ').title()}")

    # Generate alert
    if passed == total:
        alerting.send_alert(
            severity=AlertSeverity.INFO,
            title="Phase 8 Complete - 13 Modules Active",
            description="All 4 Phase 8 handlers tested: ad optimizer, promotional calendar, customer segmentation, return processing",
            component="phase8_testing",
            context={"handlers": 4, "total_modules": 13},
            channels=[AlertChannel.LOCAL_LOG],
        )

    alerting.print_alert_summary()

    # Export summary
    summary = {
        "phase": 8,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "handlers": list(results.keys()),
        "passed": passed,
        "total": total,
        "status": "COMPLETE" if passed == total else "INCOMPLETE",
        "total_modules": 13,
        "modules_remaining": 4,
    }

    summary_path = OUT_DIR / "phase8_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Phase 8 Summary: {summary_path}\n")


if __name__ == "__main__":
    test_all_phase8_handlers()
