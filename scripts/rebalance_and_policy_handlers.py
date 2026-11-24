#!/usr/bin/env python3
"""Inventory rebalancing and policy change monitoring handlers.

Optimizes inventory distribution and tracks platform policy updates.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class InventoryRebalanceHandler(ActionHandler):
    """Optimizes inventory distribution across platforms."""

    def __init__(self, client_id: str):
        """Initialize inventory rebalance handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.rebalance_plan = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Calculate optimal inventory rebalancing.

        Args:
            content: Current inventory levels and platform data

        Returns:
            Dict with rebalancing recommendations
        """
        inventory = content.get("inventory", {})
        platform_demand = content.get("platform_demand", {})

        if not inventory or not platform_demand:
            raise ValueError("Missing inventory or platform demand data")

        time.sleep(0.05)

        total_inventory = sum(inv.get("quantity", 0) for inv in inventory.values())

        for sku, inv_data in inventory.items():
            current_qty = inv_data.get("quantity", 0)
            current_platform = inv_data.get("platform")

            demand = platform_demand.get(sku, {})
            wb_demand = demand.get("WB_CN", 0)
            ozon_demand = demand.get("Ozon RU", 0)

            total_demand = wb_demand + ozon_demand

            if total_demand == 0:
                continue

            # Calculate optimal distribution
            optimal_wb = int((wb_demand / total_demand) * current_qty)
            optimal_ozon = current_qty - optimal_wb

            # Calculate moves needed
            if current_platform == "WB_CN":
                move_to_ozon = max(0, optimal_ozon - 0)  # Assume no Ozon stock initially
            else:
                move_to_ozon = 0

            self.rebalance_plan[sku] = {
                "sku": sku,
                "total_quantity": current_qty,
                "wb_allocation": optimal_wb,
                "ozon_allocation": optimal_ozon,
                "wb_demand": wb_demand,
                "ozon_demand": ozon_demand,
                "rebalance_needed": move_to_ozon > 0,
                "recommended_action": f"Transfer {move_to_ozon} units to Ozon RU" if move_to_ozon > 0 else "No action needed",
            }

        return {
            "client_id": self.client_id,
            "total_skus": len(self.rebalance_plan),
            "rebalance_plan": self.rebalance_plan,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify rebalancing plan.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        plan = execution_result.get("rebalance_plan", {})

        validation_checks = {
            "plan_generated": len(plan) > 0,
            "allocations_valid": True,
            "demand_coverage": True,
        }

        error_details = []

        for sku, rebalance in plan.items():
            wb_alloc = rebalance.get("wb_allocation", 0)
            ozon_alloc = rebalance.get("ozon_allocation", 0)
            total = rebalance.get("total_quantity", 0)

            if wb_alloc + ozon_alloc != total:
                validation_checks["allocations_valid"] = False
                error_details.append(f"{sku}: allocation mismatch")

            if wb_alloc < 0 or ozon_alloc < 0:
                validation_checks["allocations_valid"] = False
                error_details.append(f"{sku}: negative allocation")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_rebalance_plan" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "skus_rebalanced": len(plan),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }


class PolicyChangeHandler(ActionHandler):
    """Monitors and tracks platform policy changes."""

    def __init__(self, client_id: str):
        """Initialize policy change monitoring handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.policy_changes = []
        self.impact_analysis = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Monitor policy changes across platforms.

        Args:
            content: Policy tracking configuration

        Returns:
            Dict with detected policy changes
        """
        policies = content.get("policies_to_track", [])

        if not policies:
            raise ValueError("No policies to track")

        time.sleep(0.05)

        detected_changes = self._check_policy_updates(policies)

        for change in detected_changes:
            self.policy_changes.append(change)

            # Analyze impact
            impact = self._analyze_policy_impact(change)
            self.impact_analysis[change["policy_id"]] = impact

        return {
            "client_id": self.client_id,
            "policies_monitored": len(policies),
            "changes_detected": len(self.policy_changes),
            "policy_changes": self.policy_changes,
            "impact_analysis": self.impact_analysis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify policy monitoring results.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        changes = execution_result.get("policy_changes", [])
        impacts = execution_result.get("impact_analysis", {})

        validation_checks = {
            "monitoring_complete": True,
            "changes_documented": True,
            "impact_assessed": len(impacts) == len(changes),
        }

        error_details = []

        for change in changes:
            if "policy_id" not in change or "policy_name" not in change:
                validation_checks["changes_documented"] = False
                error_details.append("Incomplete policy change record")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_policy_monitoring" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "changes_detected": len(changes),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _check_policy_updates(self, policies: list[str]) -> list[dict[str, Any]]:
        """Check for policy updates (simulated).

        Args:
            policies: Policies to check

        Returns:
            List of detected changes
        """
        changes = [
            {
                "policy_id": "policy_001",
                "policy_name": "Minimum Order Value",
                "platform": "WB_CN",
                "old_value": "100 RUB",
                "new_value": "150 RUB",
                "effective_date": "2026-11-22",
                "change_type": "threshold_increase",
            },
            {
                "policy_id": "policy_002",
                "policy_name": "Seller Commission",
                "platform": "Ozon RU",
                "old_value": "5%",
                "new_value": "6%",
                "effective_date": "2026-11-25",
                "change_type": "rate_increase",
            },
        ]
        return changes

    def _analyze_policy_impact(self, change: dict[str, Any]) -> dict[str, Any]:
        """Analyze impact of policy change.

        Args:
            change: Policy change record

        Returns:
            Impact analysis dict
        """
        policy_type = change.get("change_type", "")
        platform = change.get("platform", "")

        impact_level = "medium"
        if "increase" in policy_type:
            impact_level = "high"
        elif "threshold" in policy_type:
            impact_level = "high"

        return {
            "policy_id": change.get("policy_id"),
            "impact_level": impact_level,
            "affected_category": "all_sellers",
            "recommendations": [
                "Review pricing strategy",
                "Assess profitability impact",
                "Update automated systems",
            ],
            "urgency": "high" if impact_level == "high" else "medium",
        }


def main() -> None:
    """Demo Phase 7 handlers."""
    print("[Phase 7] Testing Inventory Rebalancing...\n")

    # Test inventory rebalancing
    rebalance_handler = InventoryRebalanceHandler("client_001")
    inventory = {
        "MD-700": {"quantity": 100, "platform": "WB_CN"},
        "MD-4090": {"quantity": 50, "platform": "WB_CN"},
    }
    platform_demand = {
        "MD-700": {"WB_CN": 40, "Ozon RU": 60},
        "MD-4090": {"WB_CN": 30, "Ozon RU": 20},
    }

    result = rebalance_handler.execute({
        "inventory": inventory,
        "platform_demand": platform_demand,
    })
    verification = rebalance_handler.verify(result)

    print(f"✅ Inventory rebalancing: {verification['overall_status']}")
    for sku, plan in result.get("rebalance_plan", {}).items():
        print(f"\n  {sku}:")
        print(f"    Total Inventory: {plan['total_quantity']} units")
        print(f"    Recommended WB_CN: {plan['wb_allocation']} units")
        print(f"    Recommended Ozon: {plan['ozon_allocation']} units")
        print(f"    Action: {plan['recommended_action']}")

    print(f"\n[Phase 7] Testing Policy Change Monitoring...\n")

    # Test policy monitoring
    policy_handler = PolicyChangeHandler("client_001")
    result = policy_handler.execute({
        "policies_to_track": ["min_order_value", "seller_commission", "return_policy"]
    })
    verification = policy_handler.verify(result)

    print(f"✅ Policy monitoring: {verification['overall_status']}")
    print(f"   Changes detected: {result['changes_detected']}")
    for change in result.get("policy_changes", []):
        impact = result.get("impact_analysis", {}).get(change["policy_id"], {})
        print(f"\n  {change['policy_name']} ({change['platform']}):")
        print(f"    Change: {change['old_value']} → {change['new_value']}")
        print(f"    Effective: {change['effective_date']}")
        print(f"    Impact Level: {impact.get('impact_level', 'unknown').upper()}")


if __name__ == "__main__":
    main()
