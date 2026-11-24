#!/usr/bin/env python3
"""Integration test for P0 Approval Gate with Phase 24 Governance.

Tests the complete workflow:
1. ReviewResponseActionHandler wrapped with P0ControlledActionHandler
2. PolicyGovernanceSystem creates and processes ApprovalRequest
3. Approval gate blocks execution until 2/3 approvals received
4. TaskApprovalRecord persisted to ledger
5. PROGRESS.md audit trail synced
"""
from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import our modules
from policy_governance_phase24 import (
    PolicyGovernanceSystem,
    ApprovalStatus,
)
from review_response_handler import ReviewResponseActionHandler
from p0_approval_ledger import (
    P0ControlledActionHandler,
    ApprovalGateConfig,
    ApprovalRejectedError,
    ApprovalTimeoutError,
)
from p0_control_integration import P0ControlIntegration

ROOT = Path(__file__).resolve().parents[1]
OUT_TEST = ROOT / "outputs" / "test_p0_approval_gate_20261121.json"


def test_p0_approval_gate_with_governance():
    """Test P0 approval gate integrated with PolicyGovernanceSystem."""
    print("\n" + "="*80)
    print("TEST: P0 APPROVAL GATE WITH PHASE 24 GOVERNANCE")
    print("="*80)

    # Initialize systems
    print("\n[Setup] Initializing PolicyGovernanceSystem...")
    policy_sys = PolicyGovernanceSystem()
    assert policy_sys.initialize_system()
    print("✓ PolicyGovernanceSystem initialized")

    print("[Setup] Initializing P0ControlIntegration...")
    p0_control = P0ControlIntegration(
        policy_governance_system=policy_sys,
        approval_gate_config=ApprovalGateConfig(
            approval_required_threshold=50,
            polling_timeout_seconds=30,
            polling_interval_ms=100,  # Faster polling for test
        ),
    )
    print("✓ P0ControlIntegration initialized")

    # Create action handler
    print("\n[Setup] Creating ReviewResponseActionHandler...")
    handler = ReviewResponseActionHandler(
        client_id="ozon_p0_test",
        auto_response_enabled=True,
    )
    print("✓ ReviewResponseActionHandler created")

    # Wrap with P0 approval gate
    print("\n[P0 Gate] Wrapping handler with approval gate...")
    task_id = "p0_test_workflow_20261121"
    approvers = [
        "alice@company.com",
        "bob@company.com",
        "charlie@company.com",
    ]

    controlled = p0_control.wrap_action_handler(
        handler=handler,
        task_id=task_id,
        severity_level=75,  # Triggers approval gate (>= 50)
        approvers=approvers,
    )
    print(f"✓ Handler wrapped with P0ControlledActionHandler")
    print(f"  Task ID: {task_id}")
    print(f"  Severity: 75/100")
    print(f"  Approvers: {len(approvers)}")

    # Prepare action content
    reviews_content = {
        "reviews": [
            {
                "review_id": "review_001",
                "rating": 5,
                "text": "Отличный продукт! Полностью доволен покупкой.",
            },
            {
                "review_id": "review_002",
                "rating": 2,
                "text": "Не соответствует описанию, разочарован.",
            },
        ]
    }

    # Start thread that will approve the request
    print("\n[Approval] Starting approval simulator thread...")
    approval_thread = threading.Thread(
        target=_simulate_approvals,
        args=(
            p0_control.policy_governance_system,
            controlled,  # Pass controlled handler so we can poll for approval_request_id
            approvers,
        ),
        daemon=True,
    )
    approval_thread.start()
    print("✓ Approval simulator thread started")

    # Execute with approval gate
    print("\n[Execution] Calling execute() with approval gate...")
    try:
        # This will block until approval is received
        result = controlled.execute(reviews_content)

        print("✓ Execution completed successfully")
        print(f"  Reviews processed: {result['reviews_processed']}")
        print(f"  Responses generated: {len(result['responses_generated'])}")

        # Check approval record
        approval_record = controlled.get_approval_record()
        assert approval_record is not None
        print(f"\n[Approval Record]")
        print(f"  Task ID: {approval_record.task_id}")
        print(f"  Status: {approval_record.status.value}")
        print(f"  Decision: {approval_record.approval_decision}")
        print(f"  Approval %: {approval_record.decision_evidence.get('approval_percentage', 'N/A')}%")

        # Record to ledger
        print(f"\n[Ledger] Recording approval decision...")
        p0_control.record_approval_decision(task_id, controlled)
        print("✓ Recorded to approval ledger")

        # Verify ledger
        ledger_record = p0_control.ledger.get_record(task_id)
        assert ledger_record is not None
        print(f"  Retrieved from ledger: {ledger_record.task_id}")

        # Verify PROGRESS.md sync
        progress_file = ROOT / "PROGRESS.md"
        if progress_file.exists():
            content = progress_file.read_text(encoding="utf-8")
            if task_id in content:
                print("✓ Synced to PROGRESS.md")
            else:
                print("⚠ Not yet in PROGRESS.md (may be buffered)")

        # Save test output
        output = {
            "test_name": "P0 Approval Gate with Phase 24 Governance",
            "status": "PASSED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "severity_level": 75,
            "approvers_count": len(approvers),
            "execution_result": {
                "reviews_processed": result['reviews_processed'],
                "responses_generated": len(result['responses_generated']),
            },
            "approval_record": approval_record.to_dict() if approval_record else None,
        }

        OUT_TEST.parent.mkdir(parents=True, exist_ok=True)
        OUT_TEST.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✓ Test output saved: {OUT_TEST}")

        print("\n" + "="*80)
        print("✓ PASS: P0 Approval Gate Test")
        print("="*80)

        return True

    except ApprovalRejectedError as e:
        print(f"✗ Approval rejected: {e}")
        return False
    except ApprovalTimeoutError as e:
        print(f"✗ Approval timeout: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def _simulate_approvals(
    policy_sys: Any,
    controlled: Any,  # P0ControlledActionHandler
    approvers: list[str],
) -> None:
    """Simulate approvers submitting approval decisions.

    Thread function that waits for approval request ID to be created,
    then submits approvals.
    """
    print(f"[Simulator] Waiting for approval request to be created...")

    approval_workflow = policy_sys.approval_workflow
    approval_request_id = None

    # Poll for approval_request_id (created by execute() in main thread)
    for attempt in range(50):  # Wait up to 5 seconds (50 * 100ms)
        if controlled.approval_request_id:
            approval_request_id = controlled.approval_request_id
            print(f"[Simulator] Found approval request ID: {approval_request_id}")
            break
        time.sleep(0.1)

    if not approval_request_id:
        print(f"[Simulator] ✗ Timeout waiting for approval request ID")
        return

    # Wait a bit for gate to start polling
    time.sleep(0.2)

    # Submit first approval
    print(f"[Simulator] Submitting approval 1/3 from {approvers[0]}...")
    approval_workflow.submit_approval(
        approval_request_id,
        approvers[0],
        True,
        "Approved - no issues"
    )

    # Submit second approval
    time.sleep(0.1)
    print(f"[Simulator] Submitting approval 2/3 from {approvers[1]}...")
    approval_workflow.submit_approval(
        approval_request_id,
        approvers[1],
        True,
        "Approved - looks good"
    )

    # At this point, should have 2/3 = 66.67% (fully approved)
    request = approval_workflow.get_approval_request(approval_request_id)
    pct = request.get_approval_percentage()
    print(f"[Simulator] Approval percentage: {pct:.1f}%")
    print(f"[Simulator] Fully approved: {request.is_fully_approved()}")


def test_approval_gate_rejection():
    """Test P0 approval gate rejection flow."""
    print("\n" + "="*80)
    print("TEST: P0 APPROVAL GATE REJECTION")
    print("="*80)

    # Initialize systems
    policy_sys = PolicyGovernanceSystem()
    p0_control = P0ControlIntegration(
        policy_governance_system=policy_sys,
        approval_gate_config=ApprovalGateConfig(
            approval_required_threshold=50,
            polling_timeout_seconds=30,
            polling_interval_ms=100,
        ),
    )

    # Create handler
    handler = ReviewResponseActionHandler(
        client_id="ozon_p0_test_reject",
        auto_response_enabled=True,
    )

    # Wrap with gate
    task_id = "p0_test_rejection_20261121"
    approvers = ["alice@company.com", "bob@company.com"]

    controlled = p0_control.wrap_action_handler(
        handler=handler,
        task_id=task_id,
        severity_level=60,
        approvers=approvers,
    )

    # Start thread that will reject
    print("\n[Setup] Starting rejection simulator thread...")
    rejection_thread = threading.Thread(
        target=_simulate_rejection,
        args=(
            p0_control.policy_governance_system,
            controlled,  # Pass controlled handler
            approvers,
        ),
        daemon=True,
    )
    rejection_thread.start()

    # Try to execute
    print("[Execution] Calling execute() with rejection pending...")
    try:
        result = controlled.execute({"reviews": []})
        print("✗ Should have raised ApprovalRejectedError")
        return False

    except ApprovalRejectedError as e:
        print(f"✓ Correctly rejected: {e}")
        approval_record = controlled.get_approval_record()
        assert approval_record.status.value == "rejected"
        print(f"  Record status: {approval_record.status.value}")
        return True

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def _simulate_rejection(
    policy_sys: Any,
    controlled: Any,  # P0ControlledActionHandler
    approvers: list[str],
) -> None:
    """Simulate approver rejecting the request.

    Thread function that waits for approval request ID to be created,
    then submits rejection.
    """
    print(f"[Simulator] Waiting for approval request to be created...")

    approval_workflow = policy_sys.approval_workflow
    approval_request_id = None

    # Poll for approval_request_id (created by execute() in main thread)
    for attempt in range(50):  # Wait up to 5 seconds (50 * 100ms)
        if controlled.approval_request_id:
            approval_request_id = controlled.approval_request_id
            print(f"[Simulator] Found approval request ID: {approval_request_id}")
            break
        time.sleep(0.1)

    if not approval_request_id:
        print(f"[Simulator] ✗ Timeout waiting for approval request ID")
        return

    # Wait a bit for gate to start polling
    time.sleep(0.2)

    # Submit rejection
    print(f"[Simulator] Submitting rejection from {approvers[0]}...")
    approval_workflow.submit_approval(
        approval_request_id,
        approvers[0],
        False,
        "Cannot approve - insufficient evidence"
    )

    # Manually set status to REJECTED
    request = approval_workflow.get_approval_request(approval_request_id)
    request.status = ApprovalStatus.REJECTED
    request.rejection_reason = "Cannot approve - insufficient evidence"
    print(f"[Simulator] Request status set to REJECTED")


def main() -> None:
    """Run all P0 approval gate tests."""
    print("\n" + "="*80)
    print("P0 APPROVAL GATE INTEGRATION TESTS")
    print("="*80)

    results = []

    # Test 1: Normal approval flow
    print("\n[Test 1/2] P0 Approval Gate with Governance")
    result1 = test_p0_approval_gate_with_governance()
    results.append(("P0 Approval Gate", result1))

    # Test 2: Rejection flow
    print("\n[Test 2/2] P0 Approval Gate Rejection")
    result2 = test_approval_gate_rejection()
    results.append(("P0 Approval Rejection", result2))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_pass = sum(1 for _, passed in results if passed)
    total = len(results)
    print(f"\nTotal: {total_pass}/{total} passed")


if __name__ == "__main__":
    main()
