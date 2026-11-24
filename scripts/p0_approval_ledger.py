#!/usr/bin/env python3
"""P0 Control Layer: Approval ledger and governance-integrated action handler.

Bridges Phase 24 (Policy Governance) approval workflows with the P0 control system.
Implements evidence-driven operations where human review + execution confirmation
are required before platform actions on P0 (critical) incidents.

Key integration points:
- P0 #2: TaskApprovalRecord links task_id to approval_request_id
- P0 #3: Before action execution, check approval status and block if needed
- P0 #4: Unified review status machine for all action types
- P0 #6: Audit trail synced to PROGRESS.md
"""
from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Callable
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ============================================================================
# P0 APPROVAL DATA STRUCTURES
# ============================================================================


class TaskApprovalStatus(str, Enum):
    """Status of a task's approval record."""
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED_FOR_REVISION = "returned_for_revision"
    EXECUTION_BLOCKED = "execution_blocked"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskApprovalRecord:
    """Links a task to its approval request and governance context.

    P0 #2 data structure: Approval ledger for task execution tracking.
    Records the complete approval decision chain and execution history.
    """
    task_id: str
    approval_request_id: str
    framework_context: str  # "Phase 24 PolicyGovernanceSystem"
    severity_level: int  # 0-100
    approvers_assigned: list[str] = field(default_factory=list)
    approval_decision: Optional[str] = None  # "APPROVED", "REJECTED", etc.
    decision_timestamp: Optional[str] = None
    decision_evidence: dict[str, Any] = field(default_factory=dict)
    task_blocked_until: Optional[str] = None
    status: TaskApprovalStatus = TaskApprovalStatus.AWAITING_APPROVAL
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)

    def mark_approved(self, evidence: dict[str, Any]) -> None:
        """Record approval decision."""
        self.approval_decision = "APPROVED"
        self.decision_timestamp = datetime.now(timezone.utc).isoformat()
        self.decision_evidence = evidence
        self.status = TaskApprovalStatus.APPROVED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_rejected(self, reason: str, evidence: dict[str, Any]) -> None:
        """Record rejection decision."""
        self.approval_decision = "REJECTED"
        self.decision_timestamp = datetime.now(timezone.utc).isoformat()
        self.decision_evidence = {**evidence, "rejection_reason": reason}
        self.status = TaskApprovalStatus.REJECTED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_executing(self) -> None:
        """Record that execution has started."""
        self.status = TaskApprovalStatus.EXECUTING
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self) -> None:
        """Record execution completion."""
        self.status = TaskApprovalStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        """Record execution failure."""
        self.status = TaskApprovalStatus.FAILED
        self.decision_evidence["execution_error"] = error
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def is_approved(self) -> bool:
        """Check if task is approved for execution."""
        return self.status == TaskApprovalStatus.APPROVED


@dataclass
class ApprovalGateConfig:
    """Configuration for P0 approval gate behavior."""
    approval_required_threshold: int = 50  # severity >= 50 requires approval
    polling_timeout_seconds: int = 300  # 5 minutes
    polling_interval_ms: int = 500  # check every 500ms
    max_polling_attempts: int = 600  # 300 seconds / 0.5 seconds
    feishu_notify_on_approval: bool = True
    feishu_notify_on_rejection: bool = True
    audit_trail_enabled: bool = True


# ============================================================================
# P0 CONTROLLED ACTION HANDLER: GOVERNANCE-INTEGRATED WRAPPER
# ============================================================================


class ApprovalTimeoutError(Exception):
    """Raised when approval decision does not arrive within timeout."""
    pass


class ApprovalRejectedError(Exception):
    """Raised when approval request is rejected."""
    pass


class P0ControlledActionHandler:
    """Wraps ActionHandler implementations with P0 approval gate.

    P0 #3 implementation: Before executing any action, verify approval status.

    Workflow:
    1. Check severity level
    2. If severity >= threshold, create ApprovalRequest via PolicyGovernanceSystem
    3. Poll for approval decision (with timeout)
    4. Only execute if is_fully_approved() returns True
    5. Create TaskApprovalRecord linking approval_request_id to task_id
    6. Log decision to GovernanceAuditTrail and PROGRESS.md
    7. Trigger Feishu alerts for approval/rejection events
    """

    def __init__(
        self,
        wrapped_handler: Any,  # Concrete ActionHandler instance
        policy_governance_system: Any,  # PolicyGovernanceSystem instance
        task_id: str,
        severity_level: int,
        approvers: list[str],
        feishu_integration: Optional[Any] = None,
        config: Optional[ApprovalGateConfig] = None,
    ):
        """Initialize controlled action handler.

        Args:
            wrapped_handler: Concrete ActionHandler to wrap (e.g., ReviewResponseActionHandler)
            policy_governance_system: PolicyGovernanceSystem instance for approval workflow
            task_id: Task identifier for approval ledger
            severity_level: Severity 0-100 (from Ozon RU incident)
            approvers: List of approver emails
            feishu_integration: Optional FeishuIntegration for alerts
            config: ApprovalGateConfig with gate behavior settings
        """
        self.wrapped_handler = wrapped_handler
        self.policy_governance_system = policy_governance_system
        self.task_id = task_id
        self.severity_level = severity_level
        self.approvers = approvers
        self.feishu_integration = feishu_integration
        self.config = config or ApprovalGateConfig()

        self.approval_record: Optional[TaskApprovalRecord] = None
        self.approval_request_id: Optional[str] = None
        self._lock = threading.RLock()

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute action with approval gate.

        P0 #3 gate: Check approval status before execution.

        Args:
            content: Action content

        Returns:
            Execution result with approval metadata

        Raises:
            ApprovalTimeoutError: If approval decision exceeds timeout
            ApprovalRejectedError: If approval is rejected
        """
        with self._lock:
            # Step 1: Check severity and create approval request if needed
            if self._requires_approval():
                self._create_approval_request()
                self._wait_for_approval_decision()
            else:
                print(f"[P0] Task {self.task_id}: Severity {self.severity_level} below threshold, skipping approval gate")

            # Step 2: Execute wrapped handler
            try:
                print(f"[P0] Task {self.task_id}: Executing action with approval cleared")
                if self.approval_record:
                    self.approval_record.mark_executing()

                execution_result = self.wrapped_handler.execute(content)

                # Step 3: Verify result
                verification_result = self.wrapped_handler.verify(execution_result)

                if self.approval_record:
                    self.approval_record.mark_completed()

                # Combine results
                result = {
                    **execution_result,
                    "verification": verification_result,
                    "p0_approval_record": self.approval_record.to_dict() if self.approval_record else None,
                    "p0_controlled_execution": True,
                }

                return result

            except Exception as e:
                if self.approval_record:
                    self.approval_record.mark_failed(str(e))
                raise

    def _requires_approval(self) -> bool:
        """Check if this task requires approval based on severity."""
        return self.severity_level >= self.config.approval_required_threshold

    def _create_approval_request(self) -> None:
        """Create approval request via PolicyGovernanceSystem."""
        print(f"[P0] Task {self.task_id}: Severity {self.severity_level} requires approval")

        # Create temporary policy version for approval
        policy_id = f"p0_incident_{self.task_id}"
        version_id = f"{policy_id}_v1"

        # Use ApprovalWorkflowManager to create approval request
        approval_workflow = self.policy_governance_system.approval_workflow
        self.approval_request_id = approval_workflow.create_approval_request(
            policy_version_id=version_id,
            requested_by="p0_control_system",
            approvers=self.approvers,
        )

        # Create approval record for ledger
        self.approval_record = TaskApprovalRecord(
            task_id=self.task_id,
            approval_request_id=self.approval_request_id,
            framework_context="Phase 24 PolicyGovernanceSystem",
            severity_level=self.severity_level,
            approvers_assigned=self.approvers,
            task_blocked_until=None,
        )

        print(f"[P0] Task {self.task_id}: Approval request created - {self.approval_request_id}")
        print(f"[P0] Task {self.task_id}: Awaiting approval from {len(self.approvers)} approvers")

        # Notify approvers via Feishu if configured
        if self.feishu_integration and self.config.feishu_notify_on_approval:
            self._send_approval_notification()

    def _wait_for_approval_decision(self) -> None:
        """Poll approval workflow until decision is reached or timeout.

        P0 #3 gate: Block execution until approval status is determined.
        """
        if not self.approval_request_id:
            raise RuntimeError(f"Approval request not created for {self.task_id}")

        approval_workflow = self.policy_governance_system.approval_workflow
        start_time = time.time()
        attempts = 0

        print(f"[P0] Task {self.task_id}: Polling for approval (timeout: {self.config.polling_timeout_seconds}s)")

        while attempts < self.config.max_polling_attempts:
            try:
                # Check approval status
                approval_request = approval_workflow.get_approval_request(self.approval_request_id)

                if approval_request.is_fully_approved():
                    print(f"[P0] Task {self.task_id}: ✓ Approval received ({approval_request.get_approval_percentage():.1f}%)")
                    if self.approval_record:
                        evidence = {
                            "approval_percentage": approval_request.get_approval_percentage(),
                            "approvals_count": len([a for a in approval_request.approvals.values() if a["status"] == "APPROVED"]),
                            "total_approvers": len(approval_request.approvers),
                        }
                        self.approval_record.mark_approved(evidence)
                    return

                # Check if rejected
                if approval_request.status.value == "REJECTED":
                    reason = approval_request.rejection_reason or "No reason provided"
                    print(f"[P0] Task {self.task_id}: ✗ Approval rejected - {reason}")
                    if self.approval_record:
                        self.approval_record.mark_rejected(reason, {"rejection_reason": reason})
                    if self.feishu_integration and self.config.feishu_notify_on_rejection:
                        self._send_rejection_notification(reason)
                    raise ApprovalRejectedError(f"Approval rejected: {reason}")

                elapsed = time.time() - start_time
                if elapsed > self.config.polling_timeout_seconds:
                    print(f"[P0] Task {self.task_id}: ✗ Approval timeout ({elapsed:.1f}s)")
                    if self.approval_record:
                        self.approval_record.status = TaskApprovalStatus.EXECUTION_BLOCKED
                    raise ApprovalTimeoutError(
                        f"Approval decision not received within {self.config.polling_timeout_seconds}s"
                    )

                # Sleep before next poll
                time.sleep(self.config.polling_interval_ms / 1000.0)
                attempts += 1

            except (ApprovalRejectedError, ApprovalTimeoutError):
                raise
            except Exception as e:
                print(f"[P0] Task {self.task_id}: Error checking approval: {e}")
                raise

        raise ApprovalTimeoutError(f"Max polling attempts ({self.config.max_polling_attempts}) exceeded")

    def _send_approval_notification(self) -> None:
        """Send Feishu alert that approval is requested."""
        if not self.feishu_integration:
            return

        context = {
            "task_id": self.task_id,
            "severity": self.severity_level,
            "approvers": self.approvers,
            "approval_request_id": self.approval_request_id,
        }

        self.feishu_integration.send_critical_alert(
            title=f"P0 Task Approval Required: {self.task_id}",
            description=f"Severity {self.severity_level}/100 incident requires {len(self.approvers)} approvals",
            component="p0_control_system",
            context=context,
        )

    def _send_rejection_notification(self, reason: str) -> None:
        """Send Feishu alert that approval was rejected."""
        if not self.feishu_integration:
            return

        context = {
            "task_id": self.task_id,
            "severity": self.severity_level,
            "rejection_reason": reason,
            "approval_request_id": self.approval_request_id,
        }

        self.feishu_integration.send_warning_alert(
            title=f"P0 Task Approval Rejected: {self.task_id}",
            description=f"Rejection reason: {reason}",
            component="p0_control_system",
            context=context,
        )

    def get_approval_record(self) -> Optional[TaskApprovalRecord]:
        """Get the approval ledger record for this task."""
        return self.approval_record


# ============================================================================
# P0 APPROVAL LEDGER MANAGER: PERSISTENCE AND QUERYING
# ============================================================================


class P0ApprovalLedgerManager:
    """Manages persistence and querying of approval records.

    P0 #2 implementation: Approval ledger storage and retrieval.
    """

    def __init__(self, ledger_path: Optional[Path] = None):
        """Initialize ledger manager.

        Args:
            ledger_path: Path to ledger file (defaults to outputs/p0_approval_ledger.jsonl)
        """
        self.ledger_path = ledger_path or (ROOT / "outputs" / "p0_approval_ledger.jsonl")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, TaskApprovalRecord] = {}
        self._lock = threading.RLock()

    def record_approval(self, record: TaskApprovalRecord) -> None:
        """Record approval ledger entry."""
        with self._lock:
            self._records[record.task_id] = record
            self._append_to_file(record)

    def get_record(self, task_id: str) -> Optional[TaskApprovalRecord]:
        """Retrieve approval record by task ID."""
        with self._lock:
            return self._records.get(task_id)

    def get_all_records(self) -> list[TaskApprovalRecord]:
        """Get all approval records."""
        with self._lock:
            return list(self._records.values())

    def get_records_by_status(self, status: TaskApprovalStatus) -> list[TaskApprovalRecord]:
        """Get records by approval status."""
        with self._lock:
            return [r for r in self._records.values() if r.status == status]

    def _append_to_file(self, record: TaskApprovalRecord) -> None:
        """Append record to ledger file (JSONL format)."""
        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[P0 Ledger] Failed to append to ledger: {e}")


# ============================================================================
# DEMO
# ============================================================================


def demo_p0_approval_gate() -> None:
    """Demonstrate P0 approval gate."""
    print("\n" + "="*80)
    print("P0 APPROVAL GATE DEMO")
    print("="*80)

    # Create mock objects for demo
    class MockApprovalRequest:
        def __init__(self):
            self.status_value = "PENDING"
            self.approvers = ["approver1@company.com", "approver2@company.com", "approver3@company.com"]
            self.approvals = {}
            self.rejection_reason = None

        @property
        def status(self):
            class Status:
                value = self.status_value
            return Status()

        def is_fully_approved(self):
            return self.status_value == "APPROVED"

        def get_approval_percentage(self):
            if not self.approvers:
                return 0.0
            return (len([a for a in self.approvals.values() if a["status"] == "APPROVED"]) / len(self.approvers)) * 100

    # Create approval record
    record = TaskApprovalRecord(
        task_id="P0-2026-11-21-001",
        approval_request_id="apr_001",
        framework_context="Phase 24 PolicyGovernanceSystem",
        severity_level=75,
        approvers_assigned=["alice@company.com", "bob@company.com", "charlie@company.com"],
    )

    print(f"\nCreated approval record:")
    print(f"  Task ID: {record.task_id}")
    print(f"  Severity: {record.severity_level}/100")
    print(f"  Status: {record.status.value}")
    print(f"  Approvers: {len(record.approvers_assigned)}")

    # Simulate approval
    record.mark_approved({
        "approval_percentage": 100.0,
        "approvals_count": 3,
        "total_approvers": 3,
    })

    print(f"\nAfter approval:")
    print(f"  Status: {record.status.value}")
    print(f"  Decision: {record.approval_decision}")
    print(f"  Evidence: {record.decision_evidence}")

    # Test ledger manager
    ledger = P0ApprovalLedgerManager()
    ledger.record_approval(record)

    retrieved = ledger.get_record(record.task_id)
    print(f"\nRetrieved from ledger:")
    print(f"  Task ID: {retrieved.task_id}")
    print(f"  Status: {retrieved.status.value}")
    print(f"  Ledger file: {ledger.ledger_path}")

    print("\n✓ P0 Approval Gate Demo Complete")


if __name__ == "__main__":
    demo_p0_approval_gate()
