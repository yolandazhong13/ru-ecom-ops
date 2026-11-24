#!/usr/bin/env python3
"""Phase 4 workflow: Automated remediation and audit trails.

Orchestrates:
1. Batch error recovery
2. Order recovery with retry logic
3. Audit trail generation
4. Full historical traceability
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_recovery_engine import OrderRecoveryEngine
from order_audit_trail import OrderAuditTrail
from batch_error_recovery import BatchErrorRecovery


def run_phase4_workflow():
    """Execute Phase 4 remediation workflow."""
    print("\n" + "=" * 70)
    print("PHASE 4: AUTOMATED REMEDIATION & AUDIT TRAILS".center(70))
    print("=" * 70)

    workflow_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    try:
        # Step 1: Batch error recovery
        print("\n[Phase 4] Step 1: Batch error recovery...")
        batch_recovery = BatchErrorRecovery()
        batch_report = batch_recovery.recover_failed_orders()
        batch_recovery.save_report()

        step1 = {
            "step": "batch_error_recovery",
            "status": "completed",
            "total_items": batch_report.total_items,
            "recovered": batch_report.total_recovered,
            "failed": batch_report.total_failed,
            "success_rate_pct": (batch_report.total_recovered / batch_report.total_items * 100) if batch_report.total_items > 0 else 0,
        }
        workflow_log["steps"].append(step1)
        print(f"  ✓ Items processed: {batch_report.total_items}")
        print(f"  ✓ Recovered: {batch_report.total_recovered}, Failed: {batch_report.total_failed}")

        # Step 2: Order recovery with retry
        print("\n[Phase 4] Step 2: Order recovery with retry logic...")
        recovery_engine = OrderRecoveryEngine()
        recovery_report = recovery_engine.execute_recovery()
        recovery_engine.save_report()

        step2 = {
            "step": "order_recovery",
            "status": "completed",
            "candidates_found": recovery_report.metrics.total_candidates,
            "recovery_attempted": recovery_report.metrics.recovery_attempted,
            "recovery_successful": recovery_report.metrics.recovery_successful,
            "escalations": recovery_report.metrics.escalated_operations + recovery_report.metrics.escalated_customer,
        }
        workflow_log["steps"].append(step2)
        print(f"  ✓ Recovery candidates: {recovery_report.metrics.total_candidates}")
        print(f"  ✓ Successful recoveries: {recovery_report.metrics.recovery_successful}")
        print(f"  ✓ Escalations: {step2['escalations']}")

        # Step 3: Audit trail generation
        print("\n[Phase 4] Step 3: Generating audit trails...")
        audit_trail = OrderAuditTrail()
        audit_report = audit_trail.build_audit_trails()
        audit_trail.save_report()

        step3 = {
            "step": "audit_trail",
            "status": "completed",
            "total_orders": audit_report.total_orders,
            "total_events": audit_report.total_events,
            "avg_events_per_order": (audit_report.total_events / audit_report.total_orders) if audit_report.total_orders > 0 else 0,
        }
        workflow_log["steps"].append(step3)
        print(f"  ✓ Orders audited: {audit_report.total_orders}")
        print(f"  ✓ Total events: {audit_report.total_events}")
        print(f"  ✓ Avg events/order: {step3['avg_events_per_order']:.1f}")

        # Summary
        print("\n" + "=" * 70)
        print("PHASE 4 SUMMARY".center(70))
        print("=" * 70)
        print(f"Status: ✅ COMPLETED")
        print(f"\nBatch Error Recovery:")
        print(f"  Items processed: {batch_report.total_items}")
        print(f"  Recovery rate: {step1['success_rate_pct']:.1f}%")
        print(f"\nOrder Recovery Engine:")
        print(f"  Recovery candidates: {recovery_report.metrics.total_candidates}")
        print(f"  Successful recoveries: {recovery_report.metrics.recovery_successful}")
        print(f"  Escalated to operations: {recovery_report.metrics.escalated_operations}")
        print(f"  Escalated to customer: {recovery_report.metrics.escalated_customer}")
        print(f"\nAudit Trail System:")
        print(f"  Orders audited: {audit_report.total_orders}")
        print(f"  Total events logged: {audit_report.total_events}")
        print(f"\nOutput Files:")
        print(f"  ✓ batch_recovery_report.json")
        print(f"  ✓ order_recovery_report.json")
        print(f"  ✓ audit_trail_report.json")
        print("=" * 70 + "\n")

        # Save workflow log
        workflow_log["status"] = "success"
        log_path = ROOT / "outputs" / "phase4_workflow_log.json"
        log_path.write_text(json.dumps(workflow_log, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Phase 4 workflow log: {log_path}")

        return workflow_log

    except Exception as e:
        print(f"\n❌ Phase 4 workflow failed: {e}")
        workflow_log["status"] = "failed"
        workflow_log["error"] = str(e)
        raise


if __name__ == "__main__":
    run_phase4_workflow()
