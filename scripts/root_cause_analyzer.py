#!/usr/bin/env python3
"""Root cause analysis and recommendations."""
from __future__ import annotations

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class RootCause:
    """Root cause analysis result."""
    issue: str
    probable_causes: List[str]
    affected_count: int
    confidence: float
    recommended_actions: List[str]


class RootCauseAnalyzer:
    """Analyzes root causes of issues."""

    def analyze_unmatched_orders(self, orders: List[Dict[str, Any]]) -> RootCause:
        """Analyze unmatched orders.

        Args:
            orders: Order list

        Returns:
            RootCause analysis
        """
        unmatched = [o for o in orders if not o.get("matched_on_platform", True)]

        causes = []
        if unmatched:
            # Analyze characteristics
            platforms = set(o.get("platform") for o in unmatched)
            states = set(o.get("state_machine_state") for o in unmatched)

            if len(platforms) == 1:
                causes.append(f"Platform-specific issue ({list(platforms)[0]})")

            if "shipped" in states:
                causes.append("Orders already shipped, reconciliation lag")

            if len(unmatched) > len(orders) * 0.2:
                causes.append("Systemic reconciliation problem")
            else:
                causes.append("Isolated reconciliation failures")

        return RootCause(
            issue="Unmatched orders on platform",
            probable_causes=causes or ["Unknown"],
            affected_count=len(unmatched),
            confidence=0.8 if causes else 0.4,
            recommended_actions=[
                "Check API connectivity to platform",
                "Verify order IDs match platform records",
                "Review reconciliation logs",
                "Retry sync for affected orders",
            ],
        )

    def analyze_payment_delays(self, orders: List[Dict[str, Any]]) -> RootCause:
        """Analyze payment delays.

        Args:
            orders: Order list

        Returns:
            RootCause analysis
        """
        pending = [o for o in orders if o.get("state_machine_state") == "pending_payment"]

        causes = []
        if pending:
            # High value orders might delay
            high_value = [o for o in pending if o.get("total_amount", 0) > 5000]
            if high_value:
                causes.append(f"High transaction values ({len(high_value)} orders)")

            if len(pending) > len(orders) * 0.15:
                causes.append("High overall payment delay rate")
            else:
                causes.append("Isolated payment issues")

        return RootCause(
            issue="Payment confirmation delays",
            probable_causes=causes or ["Unknown"],
            affected_count=len(pending),
            confidence=0.7,
            recommended_actions=[
                "Check payment gateway status",
                "Review transaction logs",
                "Contact payment provider",
                "Resend payment requests",
            ],
        )

    def analyze_low_shop_success(self, shop_id: str, orders: List[Dict[str, Any]]) -> RootCause:
        """Analyze low shop success.

        Args:
            shop_id: Shop ID
            orders: Order list

        Returns:
            RootCause analysis
        """
        shop_orders = [o for o in orders if o.get("shop_id") == shop_id]
        confirmed = sum(1 for o in shop_orders if o.get("state_machine_state") == "confirmed")

        causes = []
        if shop_orders:
            success_rate = confirmed / len(shop_orders)

            if success_rate < 0.5:
                # Check for patterns
                unconfirmed_payment = sum(1 for o in shop_orders if not o.get("payment_confirmed"))
                unmatched = sum(1 for o in shop_orders if not o.get("matched_on_platform"))

                if unconfirmed_payment > len(shop_orders) * 0.5:
                    causes.append("High unconfirmed payment rate")
                if unmatched > len(shop_orders) * 0.3:
                    causes.append("Reconciliation issues")

                causes.append(f"Shop configuration or integration problem")

        return RootCause(
            issue=f"Low success rate for shop {shop_id}",
            probable_causes=causes or ["Unknown"],
            affected_count=len(shop_orders) - confirmed,
            confidence=0.75,
            recommended_actions=[
                f"Review shop {shop_id} configuration",
                "Check API credentials",
                "Audit recent transactions",
                "Contact shop for verification",
            ],
        )


def main() -> None:
    """Demo root cause analysis."""
    print("[RootCauseAnalyzer] Testing root cause analysis\n")

    analyzer = RootCauseAnalyzer()

    orders = [
        {"shop_id": "shop_1", "platform": "Ozon", "state_machine_state": "pending_payment", "matched_on_platform": False, "payment_confirmed": False, "total_amount": 1500},
        {"shop_id": "shop_1", "platform": "Ozon", "state_machine_state": "confirmed", "matched_on_platform": True, "payment_confirmed": True, "total_amount": 1200},
        {"shop_id": "shop_2", "platform": "WB_CN", "state_machine_state": "pending_payment", "matched_on_platform": True, "payment_confirmed": False, "total_amount": 8000},
    ]

    print("[RootCauseAnalyzer] Analyzing issues...\n")

    # Analyze unmatched
    rca1 = analyzer.analyze_unmatched_orders(orders)
    print(f"Issue: {rca1.issue}")
    print(f"  Causes: {', '.join(rca1.probable_causes)}")
    print(f"  Affected: {rca1.affected_count}")
    print(f"  Actions: {rca1.recommended_actions[0]}\n")

    # Analyze payment
    rca2 = analyzer.analyze_payment_delays(orders)
    print(f"Issue: {rca2.issue}")
    print(f"  Causes: {', '.join(rca2.probable_causes)}")
    print(f"  Affected: {rca2.affected_count}\n")

    # Analyze shop
    rca3 = analyzer.analyze_low_shop_success("shop_1", orders)
    print(f"Issue: {rca3.issue}")
    print(f"  Confidence: {rca3.confidence:.0%}")
    print(f"  Recommendation: {rca3.recommended_actions[0]}")


if __name__ == "__main__":
    main()
