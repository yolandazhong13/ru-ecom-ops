#!/usr/bin/env python3
"""Concrete ActionHandler for pricing updates on WB_CN.

Implements the pricing update workflow with:
1. Price validation against cost and market data
2. Multi-offer batch pricing updates
3. Post-execution price verification
4. Profit margin tracking
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class PricingUpdateError(Exception):
    """Raised when pricing update fails."""
    pass


class PricingActionHandler(ActionHandler):
    """Handles pricing updates for WB_CN.

    Validates prices against cost structure and market conditions,
    updates prices across multiple SKUs, verifies post-update state.
    """

    def __init__(
        self,
        client_id: str,
        pricing_data: dict[str, dict],
    ):
        """Initialize pricing handler.

        Args:
            client_id: WB_CN client identifier
            pricing_data: Dict mapping SKU to pricing targets:
                {
                    "MD-700": {
                        "your_price": 2500,
                        "old_price": 3000,
                        "min_price": 1500,
                        "cost": 800,
                        "target_margin": 0.45
                    }
                }
        """
        self.client_id = str(client_id)
        self.pricing_data = pricing_data
        self.before_prices = {}
        self.after_prices = {}
        self.margin_analysis = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute pricing updates per content_for_approval.

        Args:
            content: Approval content with pricing targets

        Returns:
            Dict with update results and price changes
        """
        # Validate pricing before execution
        validation_errors = []
        for sku, prices in self.pricing_data.items():
            errors = self._validate_price(sku, prices)
            validation_errors.extend(errors)

        if validation_errors:
            raise PricingUpdateError(f"Pricing validation failed: {validation_errors}")

        # Simulate reading before-state
        self.before_prices = {
            sku: {"your_price": 0, "old_price": 0, "min_price": 0}
            for sku in self.pricing_data.keys()
        }

        # Simulate API update (in real scenario, would call WB API)
        time.sleep(0.05)
        update_results = []
        for sku, prices in self.pricing_data.items():
            update_results.append({
                "sku": sku,
                "your_price": prices.get("your_price"),
                "old_price": prices.get("old_price"),
                "min_price": prices.get("min_price"),
                "http_status": 200,
            })
            self.after_prices[sku] = {
                "your_price": prices.get("your_price"),
                "old_price": prices.get("old_price"),
                "min_price": prices.get("min_price"),
            }

        # Calculate margin analysis
        for sku, prices in self.pricing_data.items():
            your_price = prices.get("your_price", 0)
            cost = prices.get("cost", 0)
            if cost > 0:
                margin = (your_price - cost) / cost
                self.margin_analysis[sku] = {
                    "your_price": your_price,
                    "cost": cost,
                    "margin": margin,
                    "margin_pct": f"{margin * 100:.1f}%",
                    "target_margin": prices.get("target_margin", 0),
                    "meets_target": margin >= prices.get("target_margin", 0),
                }

        return {
            "pricing_data": self.pricing_data,
            "before_prices": self.before_prices,
            "after_prices": self.after_prices,
            "update_results": update_results,
            "margin_analysis": self.margin_analysis,
            "sku_count": len(self.pricing_data),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of pricing updates.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with price and margin checks
        """
        validation_checks = {
            "prices_updated": False,
            "min_prices_valid": False,
            "margins_above_target": False,
            "no_zero_prices": False,
            "price_consistency": False,
        }

        error_details = []

        # Check 1: Prices were updated
        after_prices = execution_result.get("after_prices", {})
        if after_prices:
            validation_checks["prices_updated"] = True

        # Check 2: Min prices are valid (less than your_price)
        min_price_valid = True
        for sku, prices in after_prices.items():
            your_price = prices.get("your_price", 0)
            min_price = prices.get("min_price", 0)
            if min_price > 0 and your_price > 0:
                if min_price >= your_price:
                    min_price_valid = False
                    error_details.append(f"{sku}: min_price >= your_price")
        validation_checks["min_prices_valid"] = min_price_valid

        # Check 3: Margins above target
        margin_analysis = execution_result.get("margin_analysis", {})
        margins_ok = True
        for sku, analysis in margin_analysis.items():
            if not analysis.get("meets_target", False):
                margins_ok = False
                error_details.append(f"{sku}: margin {analysis['margin_pct']} below target")
        validation_checks["margins_above_target"] = margins_ok

        # Check 4: No zero prices
        no_zeros = True
        for sku, prices in after_prices.items():
            your_price = prices.get("your_price", 0)
            if your_price <= 0:
                no_zeros = False
                error_details.append(f"{sku}: invalid price {your_price}")
        validation_checks["no_zero_prices"] = no_zeros

        # Check 5: Price consistency (old_price >= your_price)
        consistent = True
        for sku, prices in after_prices.items():
            your_price = prices.get("your_price", 0)
            old_price = prices.get("old_price", 0)
            if old_price > 0 and old_price < your_price:
                consistent = False
                error_details.append(f"{sku}: old_price < your_price")
        validation_checks["price_consistency"] = consistent

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_pricing_updates" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "sku_count": len(margin_analysis),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_price(self, sku: str, prices: dict[str, Any]) -> list[str]:
        """Validate a single pricing entry.

        Args:
            sku: Product SKU
            prices: Price dict

        Returns:
            List of validation error messages
        """
        errors = []

        your_price = prices.get("your_price")
        cost = prices.get("cost", 0)
        target_margin = prices.get("target_margin", 0)
        min_price = prices.get("min_price")
        old_price = prices.get("old_price")

        # Validate your_price exists and is positive
        if not your_price or your_price <= 0:
            errors.append(f"{sku}: your_price must be positive")
            return errors  # Can't validate further without your_price

        # Validate min_price
        if min_price and min_price > 0:
            if min_price >= your_price:
                errors.append(f"{sku}: min_price must be less than your_price")
            if min_price < cost:
                errors.append(f"{sku}: min_price cannot be below cost")

        # Validate old_price consistency
        if old_price and old_price > 0:
            if old_price < your_price:
                errors.append(f"{sku}: old_price should not be less than your_price")

        # Validate margin
        if cost > 0:
            margin = (your_price - cost) / cost
            if margin < target_margin:
                errors.append(
                    f"{sku}: margin {margin:.1%} below target {target_margin:.1%}"
                )

        # Validate your_price >= cost (minimum viable)
        if your_price < cost:
            errors.append(f"{sku}: your_price cannot be below cost")

        return errors


def main() -> None:
    """Demo pricing action handler."""
    sample_pricing = {
        "MD-700": {
            "your_price": 2500,
            "old_price": 3000,
            "min_price": 1500,
            "cost": 800,
            "target_margin": 0.45,
        },
        "MD-4090 PRO": {
            "your_price": 10000,
            "old_price": 12000,
            "min_price": 8000,
            "cost": 3000,
            "target_margin": 0.50,
        },
    }

    handler = PricingActionHandler(
        client_id="wb_cn",
        pricing_data=sample_pricing,
    )

    print("[Pricing] Executing pricing update...")
    try:
        result = handler.execute({})
        print(f"[Pricing] ✓ Update successful")

        verification = handler.verify(result)
        print(f"[Pricing] ✓ Verification: {verification['overall_status']}")

        if verification.get("all_valid"):
            print(f"\n[Pricing] Margin Analysis:")
            for sku, analysis in result.get("margin_analysis", {}).items():
                print(f"  {sku}:")
                print(f"    Price: {analysis['your_price']}")
                print(f"    Cost: {analysis['cost']}")
                print(f"    Margin: {analysis['margin_pct']}")
                print(f"    Target: {analysis['target_margin']:.1%}")
                print(f"    Meets Target: {analysis['meets_target']}")

    except Exception as e:
        print(f"[Pricing] ✗ Error: {e}")


if __name__ == "__main__":
    main()
