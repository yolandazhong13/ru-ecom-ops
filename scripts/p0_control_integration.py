#!/usr/bin/env python3
"""P0 Control System Integration: Bridge between Phase 24 governance and task execution.

Integrates PolicyGovernanceSystem (Phase 24) with OrchestrationEngine (Phase 20)
to implement evidence-driven operations on P0 (critical) tasks.

Integration points:
- P0 #2: TaskApprovalRecord links task to approval request
- P0 #3: Approval gate blocks execution until approval received
- P0 #4: Unified review status machine for all action types
- P0 #6: Audit trail synced to PROGRESS.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from p0_approval_ledger import (
    P0ControlledActionHandler,
    P0ApprovalLedgerManager,
    ApprovalGateConfig,
    TaskApprovalStatus,
)

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_FILE = ROOT / "PROGRESS.md"


class P0ControlIntegration:
    """Orchestrates integration between governance and execution.

    Bridges Phase 24 PolicyGovernanceSystem with OrchestrationEngine
    to enforce approval gates on P0 critical incidents.
    """

    def __init__(
        self,
        policy_governance_system: Any,  # PolicyGovernanceSystem instance
        feishu_integration: Optional[Any] = None,
        approval_gate_config: Optional[ApprovalGateConfig] = None,
    ):
        """Initialize P0 control integration.

        Args:
            policy_governance_system: PolicyGovernanceSystem for approvals
            feishu_integration: Optional FeishuIntegration for alerts
            approval_gate_config: Configuration for approval gate
        """
        self.policy_governance_system = policy_governance_system
        self.feishu_integration = feishu_integration
        self.approval_gate_config = approval_gate_config or ApprovalGateConfig()
        self.ledger = P0ApprovalLedgerManager()

    def wrap_action_handler(
        self,
        handler: Any,  # Concrete ActionHandler
        task_id: str,
        severity_level: int,
        approvers: list[str],
    ) -> P0ControlledActionHandler:
        """Wrap action handler with approval gate.

        P0 #3: Create controlled handler that enforces approval gate.

        Args:
            handler: Concrete ActionHandler to wrap
            task_id: Task identifier
            severity_level: Severity 0-100
            approvers: List of approver emails

        Returns:
            P0ControlledActionHandler wrapping the original handler
        """
        controlled = P0ControlledActionHandler(
            wrapped_handler=handler,
            policy_governance_system=self.policy_governance_system,
            task_id=task_id,
            severity_level=severity_level,
            approvers=approvers,
            feishu_integration=self.feishu_integration,
            config=self.approval_gate_config,
        )
        return controlled

    def record_approval_decision(self, task_id: str, handler: P0ControlledActionHandler) -> None:
        """Record approval decision to ledger.

        P0 #2: Persist approval record for audit trail.

        Args:
            task_id: Task identifier
            handler: P0ControlledActionHandler with approval record
        """
        record = handler.get_approval_record()
        if record:
            self.ledger.record_approval(record)
            self._sync_to_progress_md(record)

    def _sync_to_progress_md(self, record: Any) -> None:
        """Sync approval decision to PROGRESS.md audit trail.

        P0 #6: Append governance audit trail to PROGRESS.md.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            # Format: [timestamp] {policy_id} | {actor} | {action} | {resource_id} | {status}
            policy_id = f"p0_incident_{record.task_id}"
            actor = "p0_control_system"
            action = "approval_decision"
            status = record.status.value

            log_line = f"[{timestamp}] {policy_id} | {actor} | {action} | {record.task_id} | {status}\n"

            PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
                f.write(log_line)

            print(f"[P0 Sync] Recorded to PROGRESS.md: {record.task_id} -> {status}")

        except Exception as e:
            print(f"[P0 Sync] Failed to sync to PROGRESS.md: {e}")

    def get_approval_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get approval status for a task.

        Args:
            task_id: Task identifier

        Returns:
            Approval record dict or None if not found
        """
        record = self.ledger.get_record(task_id)
        if record:
            return record.to_dict()
        return None

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get all tasks awaiting approval.

        Returns:
            List of pending approval records
        """
        records = self.ledger.get_records_by_status(TaskApprovalStatus.AWAITING_APPROVAL)
        return [r.to_dict() for r in records]


# ============================================================================
# USAGE EXAMPLE: Integrated Workflow Execution
# ============================================================================


def example_integrated_workflow_execution() -> None:
    """Example showing integrated P0 workflow with approval gate.

    This demonstrates how to use P0ControlIntegration with an action handler:

    1. Receive incident (severity 75)
    2. Wrap action handler with P0ControlledActionHandler
    3. On execute(), gate checks approval status
    4. Block until 2/3 approvers approve
    5. Execute action once approved
    6. Record decision to approval ledger and PROGRESS.md
    """

    # Import actual classes (in practice)
    # from policy_governance_phase24 import PolicyGovernanceSystem
    # from review_response_handler import ReviewResponseActionHandler
    # from feishu_integration import FeishuIntegration

    print("\n" + "="*80)
    print("P0 CONTROL INTEGRATION: EXAMPLE WORKFLOW")
    print("="*80)

    # In production:
    # policy_sys = PolicyGovernanceSystem()
    # feishu = FeishuIntegration()
    # p0_control = P0ControlIntegration(
    #     policy_governance_system=policy_sys,
    #     feishu_integration=feishu,
    # )

    # # Wrap handler with approval gate
    # handler = ReviewResponseActionHandler(client_id="ozon_demo")
    # controlled = p0_control.wrap_action_handler(
    #     handler=handler,
    #     task_id="workflow-001",
    #     severity_level=75,  # >= 50 requires approval
    #     approvers=["alice@company.com", "bob@company.com", "charlie@company.com"],
    # )

    # # Execute with gate (blocks until approval or timeout)
    # try:
    #     result = controlled.execute({
    #         "reviews": [
    #             {"review_id": "r1", "rating": 5, "text": "Great!"},
    #             {"review_id": "r2", "rating": 3, "text": "OK"},
    #         ]
    #     })
    #
    #     # Record decision
    #     p0_control.record_approval_decision("workflow-001", controlled)
    #
    #     print(f"✓ Action executed after approval")
    #     print(f"  Result: {result['execution_status']}")
    #     print(f"  Approval: {result['p0_approval_record']['status']}")

    # except ApprovalRejectedError as e:
    #     print(f"✗ Action rejected: {e}")
    # except ApprovalTimeoutError as e:
    #     print(f"✗ Action timeout: {e}")

    print("\nExample workflow:")
    print("  1. Incident received (severity 75)")
    print("  2. Action handler wrapped with P0ControlledActionHandler")
    print("  3. execute() called → gate checks severity")
    print("  4. Severity >= 50 → creates ApprovalRequest")
    print("  5. Polls for approval (timeout: 300s)")
    print("  6. Approvers submit decisions → status updates")
    print("  7. 2/3 approvals → is_fully_approved() = True")
    print("  8. Execution unblocked → handler.execute() runs")
    print("  9. Result returned with approval metadata")
    print(" 10. TaskApprovalRecord persisted to ledger")
    print(" 11. Audit trail synced to PROGRESS.md")

    print("\n✓ See p0_approval_ledger.py for implementation details")


# ============================================================================
# P0 ORCHESTRATION PATTERN: How to modify OrchestrationEngine
# ============================================================================


class P0OrchestrationPattern:
    """Pattern for integrating P0 control into OrchestrationEngine.

    This shows the pattern for modifying the existing orchestration engine
    to use P0ControlledActionHandler when severity >= 50.
    """

    @staticmethod
    def execute_workflow_with_p0_gate(
        workflow: Any,  # Workflow dataclass from orchestration_master_phase20_24.py
        action_handler: Any,  # Concrete ActionHandler implementation
        p0_control: P0ControlIntegration,  # P0 control system
        task_id: str,
    ) -> dict[str, Any]:
        """Execute workflow action with P0 approval gate.

        Pattern for modifying OrchestrationEngine.execute_workflow():

        Current code (before integration):
            for action in workflow.actions:
                result = action_handler.execute(action.parameters)

        New code (after integration):
            for action in workflow.actions:
                if workflow.severity_level >= 50:
                    handler = p0_control.wrap_action_handler(
                        action_handler,
                        task_id=task_id,
                        severity_level=workflow.severity_level,
                        approvers=["approver1@company.com", ...],
                    )
                    result = handler.execute(action.parameters)
                    p0_control.record_approval_decision(task_id, handler)
                else:
                    result = action_handler.execute(action.parameters)
        """
        pass


# ============================================================================
# DEMO
# ============================================================================


def demo() -> None:
    """Demo P0 control integration."""
    example_integrated_workflow_execution()


if __name__ == "__main__":
    demo()
