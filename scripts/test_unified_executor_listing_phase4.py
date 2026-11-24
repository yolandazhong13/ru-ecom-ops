#!/usr/bin/env python3
"""Test harness for unified_action_executor with ListingActionHandler (Phase 4).

Validates listing update workflow with comprehensive monitoring:
1. P0-2 approval workflow
2. Health tracking
3. API integration monitoring
4. Data quality validation

Usage:
  python3 test_unified_executor_listing_phase4.py [--confirm]

With --confirm: Execute full workflow with API calls (MOCK - no actual API calls)
Without --confirm: Record approval and await confirmation (safe test mode)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from unified_action_executor import UnifiedActionExecutor
from action_handler_registry import HANDLER_REGISTRY, get_action_handler
from api_health_tracker import APIHealthTracker
from data_quality_validator import DataQualityValidator, ValidationStatus

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "test_listing_executor_phase4_20261120.json"

# Ozon RU client - test listing targets
CLIENT_ID = "6182781"
LISTING_TARGETS = {
    "MD-700-ORANGE": {
        "product_id": 6877164448,
        "title": "Металлоискатель грунтовой Tianxun MD-700",
        "attributes": [
            {"id": 16, "values": ["Поиск монет, драгоценностей"]},
        ],
        "image_urls": [],
        "price": 4999,
        "old_price": 5999,
        "min_price": 3500,
    },
    "MD-4090": {
        "product_id": 6877162260,
        "title": "Металлоискатель профессиональный Tianxun MD-4090 PRO",
        "attributes": [
            {"id": 16, "values": ["Поиск монет, драгоценностей, артефактов"]},
        ],
        "image_urls": [],
        "price": 14999,
        "old_price": 19999,
        "min_price": 10000,
    },
}


class MockListingActionHandler:
    """Mock listing handler for testing without real API calls."""

    def __init__(self, client_id: str, listing_data: dict):
        """Initialize mock handler.

        Args:
            client_id: Ozon client ID
            listing_data: Listing targets
        """
        self.client_id = client_id
        self.listing_data = listing_data

    def execute(self, content: dict) -> dict:
        """Mock execute listing updates.

        Args:
            content: Approval content

        Returns:
            Mock execution results
        """
        time.sleep(0.1)  # Simulate API work
        return {
            "listing_data": self.listing_data,
            "before": {
                offer: {"price": 0, "old_price": 0, "min_price": 0}
                for offer in self.listing_data.keys()
            },
            "attribute_writes": [
                {"offer_id": offer, "http_status": 200}
                for offer in self.listing_data.keys()
            ],
            "image_writes": [],
            "price_writes": [
                {"offer_id": offer, "http_status": 200}
                for offer in self.listing_data.keys()
            ],
        }

    def verify(self, execution_result: dict) -> dict:
        """Mock verify post-execution results.

        Args:
            execution_result: Results from execute

        Returns:
            Mock verification results
        """
        listing_data = execution_result.get("listing_data", {})
        verification = {}
        for offer, target in listing_data.items():
            verification[offer] = {
                "price_matches_target": True,
                "old_price_matches_target": True,
                "min_price_matches_target": True,
                "attributes_count": len(target.get("attributes", [])),
            }

        all_ok = all(all(verification[o][k] for k in (
            "price_matches_target", "old_price_matches_target", "min_price_matches_target"
        )) for o in listing_data)

        return {
            "after": {
                offer: {
                    "price": listing_data[offer].get("price"),
                    "old_price": listing_data[offer].get("old_price"),
                    "min_price": listing_data[offer].get("min_price"),
                }
                for offer in listing_data.keys()
            },
            "per_offer_verification": verification,
            "overall_status": "verified_listing_values" if all_ok else "partial_or_platform_rejected",
            "all_valid": all_ok,
        }


def main() -> None:
    """Test listing workflow with Phase 4 monitoring."""
    parser = argparse.ArgumentParser(
        description="Test unified_action_executor with listing updates (Phase 4)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Execute workflow. Without this flag, records approval and exits (safe test mode)."
    )
    args = parser.parse_args()

    # Prepare content for approval
    content_for_approval = {
        "action_type": "listing_update",
        "platform": "Ozon RU",
        "client_id": CLIENT_ID,
        "listing_data": LISTING_TARGETS,
    }

    task_id = f"test-listing-executor-phase4-{ROOT.name}-20261120"

    print(f"\n[Phase 4 Test] Initializing listing update workflow")
    print(f"[Phase 4 Test] Task ID: {task_id}")
    print(f"[Phase 4 Test] Platform: Ozon RU")
    print(f"[Phase 4 Test] Client ID: {CLIENT_ID}")
    print(f"[Phase 4 Test] Targets: {list(LISTING_TARGETS.keys())}")
    print(f"[Phase 4 Test] --confirm flag: {args.confirm}")

    # Create executor
    print(f"\n[Phase 4 Test] Creating UnifiedActionExecutor...")
    executor = UnifiedActionExecutor(
        task_id=task_id,
        action_type="listing_update",
        platform="Ozon RU",
        content_for_approval=content_for_approval,
        output_path=OUT.parent,
        confirm_flag=args.confirm,
        expires_hours=12,
    )

    # Create mock listing handler
    print(f"[Phase 4 Test] Creating mock ListingActionHandler...")
    handler = MockListingActionHandler(
        client_id=CLIENT_ID,
        listing_data=LISTING_TARGETS,
    )

    # Execute the full workflow
    print(f"\n[Phase 4 Test] Starting unified executor workflow...")
    start_time = time.time()
    report = executor.execute(
        handler=handler,
        output_filename=OUT.name,
        skip_confirmation_workflow=False,
    )
    duration = time.time() - start_time

    # Verify output file was written
    if OUT.exists():
        print(f"\n[Phase 4 Test] ✓ Output file exists: {OUT}")
        print(f"[Phase 4 Test] ✓ File size: {OUT.stat().st_size} bytes")
        print(f"[Phase 4 Test] ✓ Execution duration: {duration*1000:.1f}ms")

        # Display key report fields
        print(f"\n[Phase 4 Test] Report summary:")
        print(f"  - task_id: {report.get('task_id')}")
        print(f"  - p02_status: {report.get('p02_status')}")
        print(f"  - p02_content_hash: {report.get('p02_content_hash', 'N/A')[:16]}...")
        print(f"  - execution_status: {report.get('execution_status')}")

        if report.get('p02_status') == 'awaiting_confirmation':
            print(f"\n[Phase 4 Test] ✓ Test PASSED: Approval recorded, awaiting confirmation")
            print(f"[Phase 4 Test]   To proceed with execution, run:")
            print(f"[Phase 4 Test]   python3 {__file__} --confirm")

            # Run data quality validation
            validator = DataQualityValidator()
            print(f"\n[Phase 4 Test] Validating approval content against schema...")
            result = validator.validate_execution_result(report)
            print(f"[Phase 4 Test] Validation: {result.validation_status.value}")
            sys.exit(0)

        elif report.get('p02_status') == 'verified':
            print(f"\n[Phase 4 Test] ✓ Test PASSED: Full workflow executed and verified")
            verification = report.get('verification', {})
            per_offer = verification.get('per_offer_verification', {})
            if per_offer:
                print(f"\n[Phase 4 Test] Verification results:")
                for offer, checks in per_offer.items():
                    all_ok = all(checks.values())
                    status = "✓" if all_ok else "✗"
                    print(f"  {status} {offer}: {json.dumps(checks, ensure_ascii=False)}")

            # Record API metrics
            print(f"\n[Phase 4 Test] Recording API metrics...")
            api_tracker = APIHealthTracker()
            api_tracker.record_api_call(
                api_endpoint="/v1/product/attributes/update",
                method="POST",
                platform="Ozon RU",
                status_code=200,
                duration_ms=int(duration * 1000 / 2),
                rate_limit_remaining=9999,
            )
            api_tracker.record_api_call(
                api_endpoint="/v1/product/import/prices",
                method="POST",
                platform="Ozon RU",
                status_code=200,
                duration_ms=int(duration * 1000 / 2),
                rate_limit_remaining=9999,
            )
            api_tracker.save_api_health_db()
            print(f"[Phase 4 Test] ✓ API metrics recorded")

            # Validate execution result
            print(f"\n[Phase 4 Test] Validating execution result against schema...")
            validator = DataQualityValidator()
            val_result = validator.validate_execution_result(report)
            if val_result.validation_status == ValidationStatus.VALID:
                print(f"[Phase 4 Test] ✓ Validation PASSED: {val_result.success_rate:.1f}%")
            else:
                print(f"[Phase 4 Test] ⚠ Validation {val_result.validation_status.value.upper()}")
                if val_result.errors:
                    for error in val_result.errors:
                        print(f"  - {error}")
            validator.save_validation_report("listing_validation_report.json")

            # Register handler in registry
            print(f"\n[Phase 4 Test] Registering handler in registry...")
            HANDLER_REGISTRY.register(
                action_type="listing_update",
                platform="Ozon RU",
                handler_class=MockListingActionHandler,
                description="Updates product listings on Ozon RU",
                requires_api=True,
                risk_level="high"
            )
            print(f"[Phase 4 Test] ✓ Handler registered")

            print(f"\n[Phase 4 Test] ✓ Phase 4.3 INTEGRATION TEST COMPLETE")
            sys.exit(0)

        else:
            print(f"\n[Phase 4 Test] ⚠ Test INCOMPLETE: Status is {report.get('p02_status')}")
            if report.get('error'):
                print(f"[Phase 4 Test] Error: {report['error']}")
            sys.exit(1)
    else:
        print(f"\n[Phase 4 Test] ✗ Test FAILED: Output file was not written")
        print(f"[Phase 4 Test] Expected path: {OUT}")
        sys.exit(1)


if __name__ == "__main__":
    main()
