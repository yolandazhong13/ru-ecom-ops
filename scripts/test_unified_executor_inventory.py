#!/usr/bin/env python3
"""Test harness for unified_action_executor with InventoryActionHandler.

Validates the complete P0-2 workflow:
1. Record approval with content hash
2. Record confirmation (second-person gate)
3. Verify execution gate
4. Execute action handler (inventory aggregation)
5. Verify post-execution validation
6. Write and verify output report

Usage:
  python3 test_unified_executor_inventory.py [--confirm]

With --confirm: Executes the full workflow including data aggregation (safe, read-only)
Without --confirm: Records approval and exits (safe test mode)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from unified_action_executor import UnifiedActionExecutor
from inventory_action_handler import InventoryActionHandler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "test_inventory_executor_20261120.json"

# WB CN inventory configuration
CLIENT_ID = "wb_cn"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test unified_action_executor with inventory aggregation (P0-2 workflow)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Execute aggregation. Without this flag, records approval and exits (safe test mode)."
    )
    args = parser.parse_args()

    # Prepare content for approval
    content_for_approval = {
        "action_type": "inventory_update",
        "platform": "WB_CN",
        "client_id": CLIENT_ID,
        "mode": "sync_and_aggregate",
        "fetch_logistics": False,
    }

    task_id = f"test-inventory-executor-{ROOT.name}-20261120"

    print(f"\n[Test] Initializing UnifiedActionExecutor")
    print(f"[Test] Task ID: {task_id}")
    print(f"[Test] Platform: WB_CN")
    print(f"[Test] Client ID: {CLIENT_ID}")
    print(f"[Test] Mode: sync_and_aggregate")
    print(f"[Test] --confirm flag: {args.confirm}")

    # Create executor
    executor = UnifiedActionExecutor(
        task_id=task_id,
        action_type="inventory_update",
        platform="WB_CN",
        content_for_approval=content_for_approval,
        output_path=OUT.parent,
        confirm_flag=args.confirm,
        expires_hours=12,
    )

    # Create inventory handler
    handler = InventoryActionHandler(
        client_id=CLIENT_ID,
        mode="sync_and_aggregate",
        fetch_logistics=False,
    )

    # Execute the full workflow
    print(f"\n[Test] Starting unified executor workflow...")
    report = executor.execute(
        handler=handler,
        output_filename=OUT.name,
        skip_confirmation_workflow=False,
    )

    # Verify output file was written
    if OUT.exists():
        print(f"\n[Test] ✓ Output file exists: {OUT}")
        print(f"[Test] ✓ File size: {OUT.stat().st_size} bytes")

        # Display key report fields
        print(f"\n[Test] Report summary:")
        print(f"  - task_id: {report.get('task_id')}")
        print(f"  - p02_status: {report.get('p02_status')}")
        print(f"  - p02_content_hash: {report.get('p02_content_hash', 'N/A')[:16]}...")
        print(f"  - execution_status: {report.get('execution_status')}")

        if report.get('p02_status') == 'awaiting_confirmation':
            print(f"\n[Test] ✓ Test PASSED: Approval recorded, awaiting confirmation")
            print(f"[Test]   To proceed with execution, run:")
            print(f"[Test]   python3 {__file__} --confirm")
            sys.exit(0)

        elif report.get('p02_status') == 'verified':
            print(f"\n[Test] ✓ Test PASSED: Full workflow executed and verified")
            verification = report.get('verification', {})
            validation_checks = verification.get('validation_checks', {})
            if validation_checks:
                print(f"\n[Test] Validation results:")
                for check, passed in validation_checks.items():
                    status = "✓" if passed else "✗"
                    print(f"  {status} {check}: {passed}")
            if verification.get('error_details'):
                print(f"\n[Test] Error details:")
                for error in verification['error_details']:
                    print(f"  - {error}")
            sys.exit(0)

        else:
            print(f"\n[Test] ⚠ Test INCOMPLETE: Status is {report.get('p02_status')}")
            if report.get('error'):
                print(f"[Test] Error: {report['error']}")
            sys.exit(1)
    else:
        print(f"\n[Test] ✗ Test FAILED: Output file was not written")
        print(f"[Test] Expected path: {OUT}")
        sys.exit(1)


if __name__ == "__main__":
    main()
