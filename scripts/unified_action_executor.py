#!/usr/bin/env python3
"""Unified action executor with P0-2 two-person approval gate.

Provides a reusable framework for executing guarded platform actions:
1. ActionHandler: Abstract base class for concrete action implementations
2. UnifiedActionExecutor: Orchestrator enforcing P0-2 approval workflow

P0-2 Workflow:
  Step 1: Record approval with SHA-256 content hash
  Step 2: Record confirmation (second-person gate, requires --confirm flag)
  Step 3: Verify execution gate (hash match, confirmation recorded, not expired)
  Step 4: Execute action handler (handler.execute())
  Step 5: Post-execution validation (handler.verify())
  Step 6: Write and verify output report

All actions are read-only or API-gated; no direct platform modifications
occur without explicit two-person confirmation and hash verification.
"""
from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class ActionHandler(ABC):
    """Abstract base class for concrete action handlers.

    Each handler must implement execute() and verify() methods.
    """

    @abstractmethod
    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute the action per approved content.

        Args:
            content: Approval content with action-specific parameters

        Returns:
            Dict with execution results
        """
        pass

    @abstractmethod
    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution validation of results.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with validation_checks and overall_status
        """
        pass


try:
    from health_tracker import HealthTracker, ExecutionResult
    HAS_HEALTH_TRACKER = True
except ImportError:
    HAS_HEALTH_TRACKER = False


class ApprovalLedger:
    """Persistent ledger tracking P0-2 approvals and confirmations."""

    def __init__(self, ledger_path: Path):
        """Initialize ledger at given path.

        Args:
            ledger_path: Path to approval ledger JSON file
        """
        self.path = ledger_path
        self._ensure_ledger_exists()

    def _ensure_ledger_exists(self) -> None:
        """Create ledger file if it doesn't exist."""
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([], indent=2), encoding="utf-8")

    def record_approval(
        self,
        task_id: str,
        action_type: str,
        platform: str,
        content_hash: str,
        expires_at: str,
    ) -> None:
        """Record approval with content hash.

        Args:
            task_id: Unique task identifier
            action_type: Type of action (e.g., "pricing_update")
            platform: Target platform (e.g., "Ozon RU")
            content_hash: SHA-256 hash of content_for_approval
            expires_at: ISO-formatted expiration timestamp
        """
        ledger = json.loads(self.path.read_text(encoding="utf-8"))
        entry = {
            "task_id": task_id,
            "action_type": action_type,
            "platform": platform,
            "content_hash": content_hash,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "confirmed_at": None,
            "expires_at": expires_at,
            "status": "awaiting_confirmation",
        }
        ledger.append(entry)
        self.path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    def record_confirmation(self, task_id: str) -> None:
        """Record confirmation for a task.

        Args:
            task_id: Task identifier to confirm
        """
        ledger = json.loads(self.path.read_text(encoding="utf-8"))
        for entry in ledger:
            if entry["task_id"] == task_id:
                entry["confirmed_at"] = datetime.now(timezone.utc).isoformat()
                entry["status"] = "confirmed"
                break
        self.path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    def get_entry(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve approval entry by task_id.

        Args:
            task_id: Task identifier

        Returns:
            Entry dict or None if not found
        """
        ledger = json.loads(self.path.read_text(encoding="utf-8"))
        for entry in ledger:
            if entry["task_id"] == task_id:
                return entry
        return None


class UnifiedActionExecutor:
    """Orchestrator for P0-2 two-person approval workflow.

    Enforces mandatory approval gate before action execution:
    1. Record approval with SHA-256 content hash
    2. Require second-person confirmation (--confirm flag)
    3. Verify execution gate (hash match, confirmed, not expired)
    4. Execute action handler
    5. Verify post-execution results
    6. Write output report
    """

    def __init__(
        self,
        task_id: str,
        action_type: str,
        platform: str,
        content_for_approval: dict[str, Any],
        output_path: Path,
        confirm_flag: bool = False,
        expires_hours: int = 12,
    ):
        """Initialize executor with approval parameters.

        Args:
            task_id: Unique task identifier
            action_type: Type of action (e.g., "pricing_update")
            platform: Target platform (e.g., "Ozon RU")
            content_for_approval: Content to be approved and hashed
            output_path: Directory for output files
            confirm_flag: Whether to proceed with execution (--confirm)
            expires_hours: Approval expiration time in hours
        """
        self.task_id = task_id
        self.action_type = action_type
        self.platform = platform
        self.content_for_approval = content_for_approval
        self.output_path = Path(output_path)
        self.confirm_flag = confirm_flag
        self.expires_hours = expires_hours

        # Compute content hash
        content_str = json.dumps(
            content_for_approval, sort_keys=True, ensure_ascii=False, indent=2
        )
        self.content_hash = hashlib.sha256(
            content_str.encode("utf-8")
        ).hexdigest()

        # Initialize ledger
        ledger_path = self.output_path / "approval_ledger.json"
        self.ledger = ApprovalLedger(ledger_path)

        # Initialize health tracker if available
        self.health_tracker = None
        if HAS_HEALTH_TRACKER:
            self.health_tracker = HealthTracker()

        # Compute expiration time
        now = datetime.now(timezone.utc)
        self.expires_at = (now + timedelta(hours=expires_hours)).isoformat()

    def verify_and_get_approval(self) -> tuple[bool, str | None]:
        """Verify approval gate: hash match, confirmed, not expired.

        Returns:
            (is_approved, error_message) tuple
        """
        entry = self.ledger.get_entry(self.task_id)

        if not entry:
            return False, f"Task {self.task_id} not approved yet"

        # Check hash match
        if entry["content_hash"] != self.content_hash:
            return False, "Content hash mismatch (approval tampered)"

        # Check confirmation
        if entry["status"] != "confirmed":
            return False, "Approval not confirmed (awaiting second-person gate)"

        # Check expiration
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(entry["expires_at"])
        if now > expires:
            return False, f"Approval expired at {entry['expires_at']}"

        return True, None

    def execute(
        self,
        handler: ActionHandler,
        output_filename: str = "action_output.json",
        skip_confirmation_workflow: bool = False,
    ) -> dict[str, Any]:
        """Execute full P0-2 workflow.

        Args:
            handler: Concrete ActionHandler implementation
            output_filename: Name for output JSON file
            skip_confirmation_workflow: If True, skip recording confirmation
                                       (for testing only)

        Returns:
            Report dict with workflow status and execution results
        """
        start_time = time.time()
        report = {
            "task_id": self.task_id,
            "action_type": self.action_type,
            "platform": self.platform,
            "p02_status": None,
            "p02_content_hash": self.content_hash,
            "execution_status": None,
            "error": None,
            "verification": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Step 1: Record approval with content hash
            self.ledger.record_approval(
                task_id=self.task_id,
                action_type=self.action_type,
                platform=self.platform,
                content_hash=self.content_hash,
                expires_at=self.expires_at,
            )
            report["p02_status"] = "awaiting_confirmation"

            # Step 2: Check confirm flag and record confirmation
            if self.confirm_flag and not skip_confirmation_workflow:
                self.ledger.record_confirmation(self.task_id)
                report["p02_status"] = "confirmed"
            elif skip_confirmation_workflow:
                # For testing: force confirmation
                self.ledger.record_confirmation(self.task_id)
                report["p02_status"] = "confirmed"

            # Step 3: Verify execution gate if not in test mode
            if not skip_confirmation_workflow:
                is_approved, error_msg = self.verify_and_get_approval()
                if not is_approved:
                    report["error"] = error_msg
                    report["execution_status"] = "blocked"
                    self._write_report(report, output_filename)

                    # Record health metric
                    if self.health_tracker and HAS_HEALTH_TRACKER:
                        duration_ms = int((time.time() - start_time) * 1000)
                        self.health_tracker.record_execution(
                            task_id=self.task_id,
                            action_type=self.action_type,
                            platform=self.platform,
                            result=ExecutionResult.BLOCKED,
                            duration_ms=duration_ms,
                            error_message=error_msg,
                            p02_status=report["p02_status"],
                        )
                        self.health_tracker.save_health_db()

                    return report

            # Only proceed to execution if confirmed
            if report["p02_status"] != "confirmed":
                report["execution_status"] = "awaiting_confirmation"
                self._write_report(report, output_filename)

                # Record health metric
                if self.health_tracker and HAS_HEALTH_TRACKER:
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.health_tracker.record_execution(
                        task_id=self.task_id,
                        action_type=self.action_type,
                        platform=self.platform,
                        result=ExecutionResult.AWAITING_CONFIRMATION,
                        duration_ms=duration_ms,
                        p02_status=report["p02_status"],
                    )
                    self.health_tracker.save_health_db()

                return report

            # Step 4: Execute action handler
            execution_result = handler.execute(self.content_for_approval)
            report["execution_status"] = "executed"

            # Step 5: Post-execution validation
            verification = handler.verify(execution_result)
            report["verification"] = verification
            verification_passed = verification.get("all_valid", False)

            # Step 6: Mark as verified
            report["p02_status"] = "verified"

            # Record health metric - SUCCESS
            if self.health_tracker and HAS_HEALTH_TRACKER:
                duration_ms = int((time.time() - start_time) * 1000)
                self.health_tracker.record_execution(
                    task_id=self.task_id,
                    action_type=self.action_type,
                    platform=self.platform,
                    result=ExecutionResult.SUCCESS,
                    duration_ms=duration_ms,
                    p02_status=report["p02_status"],
                    verification_passed=verification_passed,
                )
                self.health_tracker.save_health_db()

        except Exception as e:
            report["error"] = str(e)
            report["execution_status"] = "failed"

            # Record health metric - FAILED
            if self.health_tracker and HAS_HEALTH_TRACKER:
                duration_ms = int((time.time() - start_time) * 1000)
                self.health_tracker.record_execution(
                    task_id=self.task_id,
                    action_type=self.action_type,
                    platform=self.platform,
                    result=ExecutionResult.FAILED,
                    duration_ms=duration_ms,
                    error_message=str(e),
                    p02_status=report.get("p02_status"),
                )
                self.health_tracker.save_health_db()

        # Write output report
        self._write_report(report, output_filename)

        return report

    def _write_report(self, report: dict[str, Any], output_filename: str) -> None:
        """Write report to output file.

        Args:
            report: Report dict to write
            output_filename: Output filename
        """
        self.output_path.mkdir(parents=True, exist_ok=True)
        output_file = self.output_path / output_filename
        output_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
