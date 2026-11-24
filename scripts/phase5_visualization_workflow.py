#!/usr/bin/env python3
"""Phase 5 workflow: Dashboards and visualization.

Orchestrates:
1. Advanced real-time dashboard
2. Performance metrics visualization
3. Audit trail viewer
4. Executive reporting
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from advanced_dashboard import AdvancedDashboard
from performance_metrics import PerformanceMetrics
from audit_trail_viewer import AuditTrailViewer


def run_phase5_workflow():
    """Execute Phase 5 visualization workflow."""
    print("\n" + "=" * 100)
    print("PHASE 5: DASHBOARDS & VISUALIZATION".center(100))
    print("=" * 100)

    workflow_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    try:
        # Step 1: Advanced Dashboard
        print("\n[Phase 5] Step 1: Building advanced real-time dashboard...")
        dashboard = AdvancedDashboard()
        dashboard_output = dashboard.render_full_dashboard()
        dashboard.save_dashboard_state()

        step1 = {
            "step": "advanced_dashboard",
            "status": "completed",
            "sections": 6,
            "metrics_included": [
                "pipeline_overview",
                "performance_metrics",
                "sla_compliance",
                "recovery_status",
                "risk_assessment",
                "shop_rankings",
            ],
        }
        workflow_log["steps"].append(step1)
        print(f"  ✓ Dashboard rendered with 6 sections")
        print(dashboard_output)

        # Step 2: Performance Metrics
        print("\n[Phase 5] Step 2: Generating performance metrics...")
        metrics = PerformanceMetrics()
        kpis = metrics.compute_kpis()
        health_card = metrics.generate_health_scorecard()
        exec_summary = metrics.generate_executive_summary()
        metrics.save_metrics()

        step2 = {
            "step": "performance_metrics",
            "status": "completed",
            "kpis_tracked": list(kpis.keys()),
            "overall_health": kpis['timestamp'],
        }
        workflow_log["steps"].append(step2)
        print(health_card)
        print(exec_summary)

        # Step 3: Audit Trail Viewer
        print("\n[Phase 5] Step 3: Generating audit trail viewer...")
        viewer = AuditTrailViewer()
        viewer.build_trails()
        viewer_output = viewer.display_all_orders_summary()

        stats = viewer.get_event_statistics()
        step3 = {
            "step": "audit_trail_viewer",
            "status": "completed",
            "total_orders": stats['total_orders'],
            "total_events": stats['total_events'],
            "event_types": len(stats['events_by_type']),
        }
        workflow_log["steps"].append(step3)
        print(viewer_output)

        # Summary
        print("\n" + "=" * 100)
        print("PHASE 5 SUMMARY".center(100))
        print("=" * 100)
        print(f"Status: ✅ COMPLETED")
        print(f"\nDashboard Components:")
        print(f"  ✓ Advanced real-time dashboard")
        print(f"  ✓ Performance metrics scorecard")
        print(f"  ✓ Health status visualization")
        print(f"  ✓ Audit trail viewer")
        print(f"  ✓ Executive reporting")
        print(f"\nOutput Files:")
        print(f"  ✓ advanced_dashboard_state.json")
        print(f"  ✓ performance_metrics.json")
        print(f"\nSystem Metrics Tracked:")
        print(f"  Order confirmation rate: {kpis['orders']['confirmation_rate']:.1f}%")
        print(f"  SLA compliance: {kpis['sla']['overall_compliance']:.1f}%")
        print(f"  Anomaly rate: {kpis['processing']['anomaly_rate']:.2f}%")
        print(f"  Critical alerts: {kpis['anomalies']['p0_critical']}")
        print(f"\nAudit Trails:")
        print(f"  Orders audited: {stats['total_orders']}")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Event types: {len(stats['events_by_type'])}")
        print("=" * 100 + "\n")

        # Save workflow log
        workflow_log["status"] = "success"
        log_path = ROOT / "outputs" / "phase5_workflow_log.json"
        log_path.write_text(json.dumps(workflow_log, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Phase 5 workflow log: {log_path}")

        return workflow_log

    except Exception as e:
        print(f"\n❌ Phase 5 workflow failed: {e}")
        import traceback
        traceback.print_exc()
        workflow_log["status"] = "failed"
        workflow_log["error"] = str(e)
        raise


if __name__ == "__main__":
    run_phase5_workflow()
