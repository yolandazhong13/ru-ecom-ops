#!/usr/bin/env python3
"""Phase 8: Customer Segmentation and Return Processing handlers."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class CustomerSegmentationHandler(ActionHandler):
    """Segments customers for targeted marketing."""

    def __init__(self, client_id: str):
        """Initialize customer segmentation handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.segments = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Segment customers based on behavior and value.

        Args:
            content: Customer data

        Returns:
            Dict with customer segments
        """
        customers = content.get("customers", [])

        if not customers:
            raise ValueError("No customers provided for segmentation")

        time.sleep(0.07)

        for customer in customers:
            customer_id = customer.get("customer_id")
            total_spent = customer.get("total_spent", 0)
            purchase_count = customer.get("purchase_count", 0)
            avg_order_value = customer.get("avg_order_value", 0)
            days_since_purchase = customer.get("days_since_purchase", 0)

            # Determine segment
            segment = self._determine_segment(
                total_spent, purchase_count, avg_order_value, days_since_purchase
            )

            self.segments[customer_id] = {
                "customer_id": customer_id,
                "segment": segment,
                "lifetime_value": total_spent,
                "purchase_frequency": purchase_count,
                "avg_order_value": avg_order_value,
                "churn_risk": self._calculate_churn_risk(days_since_purchase),
                "marketing_strategy": self._recommend_strategy(segment),
            }

        return {
            "client_id": self.client_id,
            "total_customers": len(self.segments),
            "segments": self.segments,
            "segment_distribution": self._get_distribution(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify customer segmentation.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        segments = execution_result.get("segments", {})

        validation_checks = {
            "customers_segmented": len(segments) > 0,
            "segments_valid": True,
            "strategies_assigned": True,
        }

        error_details = []

        for customer_id, seg in segments.items():
            if seg.get("segment") not in ["VIP", "Regular", "At-Risk", "Inactive"]:
                validation_checks["segments_valid"] = False
                error_details.append(f"{customer_id}: invalid segment")

            if not seg.get("marketing_strategy"):
                validation_checks["strategies_assigned"] = False
                error_details.append(f"{customer_id}: no strategy")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_segmentation" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "customers_segmented": len(segments),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _determine_segment(self, spent: float, count: int, avg: float, days: int) -> str:
        """Determine customer segment."""
        if spent > 50000 and count > 20:
            return "VIP"
        elif days > 180:
            return "Inactive"
        elif days > 90:
            return "At-Risk"
        else:
            return "Regular"

    def _calculate_churn_risk(self, days: int) -> float:
        """Calculate churn risk (0-1)."""
        return min(1.0, max(0.0, (days - 30) / 150))

    def _recommend_strategy(self, segment: str) -> str:
        """Recommend marketing strategy."""
        strategies = {
            "VIP": "Exclusive offers, personalized service, VIP tier benefits",
            "Regular": "Regular promotions, seasonal campaigns",
            "At-Risk": "Winback campaigns, special discounts",
            "Inactive": "Re-engagement campaigns, win-back offers",
        }
        return strategies.get(segment, "Standard marketing")

    def _get_distribution(self) -> dict[str, int]:
        """Get segment distribution."""
        dist = {}
        for seg in self.segments.values():
            segment_name = seg.get("segment")
            dist[segment_name] = dist.get(segment_name, 0) + 1
        return dist


class ReturnProcessingHandler(ActionHandler):
    """Processes and tracks customer returns."""

    def __init__(self, client_id: str, platform: str):
        """Initialize return processing handler.

        Args:
            client_id: Client identifier
            platform: Platform (WB_CN or Ozon RU)
        """
        self.client_id = str(client_id)
        self.platform = platform
        self.returns_processed = []

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Process customer returns.

        Args:
            content: Return requests

        Returns:
            Dict with processed returns
        """
        returns = content.get("returns", [])

        if not returns:
            raise ValueError("No returns provided for processing")

        time.sleep(0.08)

        for return_request in returns:
            return_id = return_request.get("return_id")
            order_id = return_request.get("order_id")
            reason = return_request.get("reason", "")
            order_value = return_request.get("order_value", 0)

            # Determine approval and refund
            approval = self._determine_approval(reason, order_value)
            refund_amount = order_value if approval else 0

            processed_return = {
                "return_id": return_id,
                "order_id": order_id,
                "reason": reason,
                "order_value": order_value,
                "approval_status": "approved" if approval else "rejected",
                "refund_amount": refund_amount,
                "processing_time": "3-5 business days" if approval else "N/A",
                "restocking_fee": int(order_value * 0.1) if approval else 0,
            }

            self.returns_processed.append(processed_return)

        return {
            "platform": self.platform,
            "returns_processed": len(self.returns_processed),
            "approved_count": sum(1 for r in self.returns_processed if r["approval_status"] == "approved"),
            "total_refund_amount": sum(r["refund_amount"] for r in self.returns_processed),
            "returns": self.returns_processed,
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify return processing.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        returns = execution_result.get("returns", [])

        validation_checks = {
            "returns_processed": len(returns) > 0,
            "approvals_valid": True,
            "refunds_calculated": True,
        }

        error_details = []

        for ret in returns:
            if ret.get("approval_status") not in ["approved", "rejected"]:
                validation_checks["approvals_valid"] = False
                error_details.append(f"{ret['return_id']}: invalid status")

            if ret.get("refund_amount", 0) < 0:
                validation_checks["refunds_calculated"] = False
                error_details.append(f"{ret['return_id']}: negative refund")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_return_processing" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "returns_processed": len(returns),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _determine_approval(self, reason: str, value: float) -> bool:
        """Determine return approval."""
        # Auto-approve for reasonable reasons
        approved_reasons = ["defective", "damaged", "wrong_item", "not_as_described"]

        if any(approved in reason.lower() for approved in approved_reasons):
            return True

        # Reject for no reason or suspicious
        if not reason or "no reason" in reason.lower():
            return False

        # Default: approve
        return True


def main() -> None:
    """Demo Phase 8 fulfillment handlers."""
    print("[Phase 8] Testing Customer Segmentation...\n")

    # Test customer segmentation
    seg_handler = CustomerSegmentationHandler("client_001")
    customers = [
        {"customer_id": "cust_001", "total_spent": 75000, "purchase_count": 30, "avg_order_value": 2500, "days_since_purchase": 5},
        {"customer_id": "cust_002", "total_spent": 15000, "purchase_count": 5, "avg_order_value": 3000, "days_since_purchase": 45},
        {"customer_id": "cust_003", "total_spent": 5000, "purchase_count": 2, "avg_order_value": 2500, "days_since_purchase": 120},
        {"customer_id": "cust_004", "total_spent": 1000, "purchase_count": 1, "avg_order_value": 1000, "days_since_purchase": 200},
    ]

    result = seg_handler.execute({"customers": customers})
    verification = seg_handler.verify(result)

    print(f"✅ Customer segmentation: {verification['overall_status']}")
    print(f"   Distribution: {result.get('segment_distribution')}")

    for cust_id, seg in list(result.get("segments", {}).items())[:2]:
        print(f"\n  {cust_id}:")
        print(f"    Segment: {seg['segment']}")
        print(f"    LTV: {seg['lifetime_value']:,.0f} RUB")
        print(f"    Strategy: {seg['marketing_strategy']}")

    print(f"\n[Phase 8] Testing Return Processing...\n")

    # Test return processing
    return_handler = ReturnProcessingHandler("client_001", "WB_CN")
    returns = [
        {"return_id": "ret_001", "order_id": "ord_001", "reason": "defective", "order_value": 5000},
        {"return_id": "ret_002", "order_id": "ord_002", "reason": "wrong_item", "order_value": 3000},
        {"return_id": "ret_003", "order_id": "ord_003", "reason": "changed_mind", "order_value": 2000},
    ]

    result = return_handler.execute({"returns": returns})
    verification = return_handler.verify(result)

    print(f"✅ Return processing: {verification['overall_status']}")
    print(f"   Processed: {result['returns_processed']}")
    print(f"   Approved: {result['approved_count']}")
    print(f"   Total refunds: {result['total_refund_amount']:,.0f} RUB")


if __name__ == "__main__":
    main()
