#!/usr/bin/env python3
"""Phase 9: Quality Assurance and Logistics Tracking handlers (final phase)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from datetime import datetime, timezone, timedelta

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class QualityAssuranceHandler(ActionHandler):
    """Monitors product quality and tracks QA metrics."""

    def __init__(self, client_id: str, platform: str):
        """Initialize QA handler.

        Args:
            client_id: Client identifier
            platform: Platform (WB_CN or Ozon RU)
        """
        self.client_id = str(client_id)
        self.platform = platform
        self.qa_results = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Process quality assurance data.

        Args:
            content: QA inspection data

        Returns:
            Dict with QA results
        """
        products = content.get("products", [])

        if not products:
            raise ValueError("No products provided for QA")

        time.sleep(0.07)

        for product in products:
            sku = product.get("sku")
            defect_rate = product.get("defect_rate", 0.0)
            customer_complaints = product.get("customer_complaints", 0)
            return_rate = product.get("return_rate", 0.0)
            quality_score = product.get("quality_score", 0)

            # Calculate QA metrics
            overall_quality = (quality_score * 0.4) + (
                (100 - defect_rate) * 0.3
            ) + ((100 - return_rate) * 0.3)

            status = "PASS" if overall_quality >= 85 else "WARN" if overall_quality >= 70 else "FAIL"

            self.qa_results[sku] = {
                "sku": sku,
                "quality_score": quality_score,
                "defect_rate": f"{defect_rate:.1f}%",
                "return_rate": f"{return_rate:.1f}%",
                "customer_complaints": customer_complaints,
                "overall_quality": f"{overall_quality:.1f}",
                "status": status,
                "recommendation": self._get_recommendation(overall_quality),
            }

        return {
            "platform": self.platform,
            "products_audited": len(self.qa_results),
            "qa_results": self.qa_results,
            "pass_rate": f"{(sum(1 for r in self.qa_results.values() if r['status'] == 'PASS') / len(self.qa_results) * 100):.0f}%" if self.qa_results else "0%",
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify QA processing.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        results = execution_result.get("qa_results", {})

        validation_checks = {
            "products_audited": len(results) > 0,
            "metrics_calculated": True,
            "status_assigned": True,
        }

        error_details = []

        for sku, result in results.items():
            if result.get("status") not in ["PASS", "WARN", "FAIL"]:
                validation_checks["status_assigned"] = False
                error_details.append(f"{sku}: invalid status")

            if not result.get("recommendation"):
                validation_checks["metrics_calculated"] = False
                error_details.append(f"{sku}: no recommendation")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_qa_audit" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "products_audited": len(results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _get_recommendation(self, overall_quality: float) -> str:
        """Get QA recommendation."""
        if overall_quality >= 95:
            return "Excellent - Maintain current standards"
        elif overall_quality >= 85:
            return "Good - Monitor for improvements"
        elif overall_quality >= 70:
            return "Fair - Implement corrective actions"
        else:
            return "Poor - Urgent supplier review required"


class LogisticsTrackingHandler(ActionHandler):
    """Tracks shipments and logistics metrics."""

    def __init__(self, client_id: str):
        """Initialize logistics handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.shipments = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Track logistics and shipment status.

        Args:
            content: Shipment data

        Returns:
            Dict with logistics metrics
        """
        orders = content.get("orders", [])

        if not orders:
            raise ValueError("No orders provided for logistics tracking")

        time.sleep(0.07)

        for order in orders:
            order_id = order.get("order_id")
            shipped_date = order.get("shipped_date")
            delivery_days = order.get("delivery_days", 0)
            carrier = order.get("carrier", "Unknown")
            status = order.get("status", "In Transit")

            # Parse date
            if isinstance(shipped_date, str):
                shipped_dt = datetime.fromisoformat(shipped_date)
            else:
                shipped_dt = datetime.now(timezone.utc)

            estimated_delivery = shipped_dt + timedelta(days=delivery_days)

            self.shipments[order_id] = {
                "order_id": order_id,
                "carrier": carrier,
                "shipped_date": shipped_dt.isoformat(),
                "estimated_delivery": estimated_delivery.isoformat(),
                "delivery_days": delivery_days,
                "status": status,
                "on_time": status == "Delivered" or datetime.now(timezone.utc) < estimated_delivery,
                "tracking_url": f"https://tracking.{carrier.lower()}.com/{order_id}",
            }

        return {
            "client_id": self.client_id,
            "shipments_tracked": len(self.shipments),
            "on_time_delivery_rate": f"{(sum(1 for s in self.shipments.values() if s['on_time']) / len(self.shipments) * 100):.0f}%" if self.shipments else "0%",
            "avg_delivery_days": sum(s["delivery_days"] for s in self.shipments.values()) / len(self.shipments) if self.shipments else 0,
            "shipments": self.shipments,
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify logistics tracking.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        shipments = execution_result.get("shipments", {})

        validation_checks = {
            "shipments_tracked": len(shipments) > 0,
            "tracking_urls_valid": True,
            "delivery_dates_valid": True,
        }

        error_details = []

        for order_id, shipment in shipments.items():
            if "tracking." not in shipment.get("tracking_url", ""):
                validation_checks["tracking_urls_valid"] = False
                error_details.append(f"{order_id}: invalid tracking URL")

            try:
                datetime.fromisoformat(shipment.get("estimated_delivery", ""))
            except:
                validation_checks["delivery_dates_valid"] = False
                error_details.append(f"{order_id}: invalid delivery date")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_logistics" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "shipments_tracked": len(shipments),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }


def main() -> None:
    """Demo Phase 9 QA and Logistics handlers."""
    print("[Phase 9] Testing Quality Assurance...\n")

    # Test QA
    qa_handler = QualityAssuranceHandler("client_001", "WB_CN")
    result = qa_handler.execute({
        "products": [
            {"sku": "MD-700", "quality_score": 92, "defect_rate": 2.5, "return_rate": 3.2, "customer_complaints": 5},
            {"sku": "MD-4090", "quality_score": 88, "defect_rate": 4.0, "return_rate": 5.1, "customer_complaints": 12},
        ]
    })
    verification = qa_handler.verify(result)

    print(f"✅ QA Audit: {verification['overall_status']}")
    print(f"   Pass Rate: {result['pass_rate']}")
    for sku, qa in result.get("qa_results", {}).items():
        print(f"\n  {sku}: {qa['status']}")
        print(f"    Quality: {qa['overall_quality']}/100")
        print(f"    Recommendation: {qa['recommendation']}")

    print(f"\n[Phase 9] Testing Logistics Tracking...\n")

    # Test Logistics
    logistics_handler = LogisticsTrackingHandler("client_001")
    result = logistics_handler.execute({
        "orders": [
            {"order_id": "ord_001", "shipped_date": "2026-11-20T10:00:00Z", "delivery_days": 5, "carrier": "DPD", "status": "In Transit"},
            {"order_id": "ord_002", "shipped_date": "2026-11-19T14:00:00Z", "delivery_days": 3, "carrier": "SDEK", "status": "Delivered"},
        ]
    })
    verification = logistics_handler.verify(result)

    print(f"✅ Logistics Tracking: {verification['overall_status']}")
    print(f"   On-Time Rate: {result['on_time_delivery_rate']}")
    print(f"   Avg Delivery: {result['avg_delivery_days']:.1f} days")


if __name__ == "__main__":
    main()
