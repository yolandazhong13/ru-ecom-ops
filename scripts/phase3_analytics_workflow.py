#!/usr/bin/env python3
"""Phase 3 workflow: Analytics, SLA monitoring, and predictive alerting.

Extends Phase 2 with advanced monitoring:
1. Historical trend analysis
2. SLA compliance checking
3. Predictive risk assessment
4. Advanced dashboard rendering
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_analytics import OrderAnalytics
from sla_compliance import SLACompliance
from predictive_alerting import PredictiveAlerting


def run_phase3_workflow():
    """Execute Phase 3 analytics workflow."""
    print("\n" + "=" * 70)
    print("PHASE 3: ANALYTICS & MONITORING WORKFLOW".center(70))
    print("=" * 70)

    workflow_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    try:
        # Step 1: Trend Analysis
        print("\n[Phase 3] Step 1: Analyzing trends (30 days)...")
        analytics = OrderAnalytics()
        trend_report = analytics.analyze_trends(days=30)
        analytics.save_report()

        step1 = {
            "step": "trend_analysis",
            "status": "completed",
            "period_days": trend_report.period_days,
            "total_orders": trend_report.total_orders,
            "total_anomalies": trend_report.total_anomalies,
            "anomaly_rate_pct": trend_report.anomaly_rate_pct,
            "orders_per_day_avg": trend_report.orders_per_day_avg,
        }
        workflow_log["steps"].append(step1)
        print(f"  ✓ Orders/day avg: {trend_report.orders_per_day_avg:.1f}")
        print(f"  ✓ Anomaly rate: {trend_report.anomaly_rate_pct:.1f}%")

        # Step 2: SLA Compliance
        print("\n[Phase 3] Step 2: Checking SLA compliance...")
        sla_monitor = SLACompliance()
        compliance_report = sla_monitor.check_compliance(days=30)
        sla_monitor.save_report()

        step2 = {
            "step": "sla_compliance",
            "status": "completed",
            "orders_analyzed": compliance_report.total_orders_analyzed,
            "overall_compliance_pct": compliance_report.overall_compliance_pct,
            "total_violations": compliance_report.total_violations,
            "sla_metrics_count": len(compliance_report.sla_metrics),
        }
        workflow_log["steps"].append(step2)
        print(f"  ✓ Overall compliance: {compliance_report.overall_compliance_pct:.1f}%")
        print(f"  ✓ Violations: {compliance_report.total_violations}")

        # Step 3: Predictive Analysis
        print("\n[Phase 3] Step 3: Analyzing predictive risks...")
        predictor = PredictiveAlerting()
        prediction_report = predictor.analyze_predictions()
        predictor.save_report()

        step3 = {
            "step": "predictive_analysis",
            "status": "completed",
            "total_predictions": prediction_report.total_predictions,
            "high_risk_count": prediction_report.high_risk_count,
            "medium_risk_count": prediction_report.medium_risk_count,
            "low_risk_count": prediction_report.low_risk_count,
        }
        workflow_log["steps"].append(step3)
        print(f"  ✓ Total predictions: {prediction_report.total_predictions}")
        print(f"  ✓ High risk: {prediction_report.high_risk_count}")

        # Step 4: Dispatch predictive alerts if needed
        if prediction_report.high_risk_count > 0:
            print("\n[Phase 3] Step 4: Dispatching predictive alerts...")
            success = predictor.dispatch_predictions()
            step4 = {
                "step": "predictive_dispatch",
                "status": "completed",
                "alerts_sent": success,
            }
            workflow_log["steps"].append(step4)
            print(f"  ✓ Predictive alerts dispatched")

        # Summary
        print("\n" + "=" * 70)
        print("PHASE 3 SUMMARY".center(70))
        print("=" * 70)
        print(f"Status: ✅ COMPLETED")
        print(f"\nTrend Analysis:")
        print(f"  Avg orders/day: {trend_report.orders_per_day_avg:.1f}")
        print(f"  Anomaly rate: {trend_report.anomaly_rate_pct:.1f}%")
        print(f"\nSLA Compliance:")
        print(f"  Overall: {compliance_report.overall_compliance_pct:.1f}%")
        print(f"  Violations: {compliance_report.total_violations}")
        print(f"\nPredictive Risks:")
        print(f"  High risk: {prediction_report.high_risk_count}")
        print(f"  Medium risk: {prediction_report.medium_risk_count}")
        print(f"\nOutput Files:")
        print(f"  ✓ trend_analysis_report.json")
        print(f"  ✓ sla_compliance_report.json")
        print(f"  ✓ predictive_analysis_report.json")
        print("=" * 70 + "\n")

        # Save workflow log
        workflow_log["status"] = "success"
        log_path = ROOT / "outputs" / "phase3_workflow_log.json"
        log_path.write_text(json.dumps(workflow_log, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Phase 3 workflow log: {log_path}")

        return workflow_log

    except Exception as e:
        print(f"\n❌ Phase 3 workflow failed: {e}")
        workflow_log["status"] = "failed"
        workflow_log["error"] = str(e)
        raise


if __name__ == "__main__":
    run_phase3_workflow()
