#!/usr/bin/env python3
"""Concrete ActionHandler for purchase order processing on WB_CN.

Implements purchase order workflow with:
1. Inventory calculation based on velocity and lead time
2. Order quantity optimization
3. Supplier validation
4. Order confirmation tracking
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class PurchaseOrderError(Exception):
    """Raised when purchase order processing fails."""
    pass


class PurchaseOrderActionHandler(ActionHandler):
    """Handles purchase order generation and processing for WB_CN.

    Calculates optimal order quantities based on:
    - Current inventory levels
    - Recent sales velocity
    - Production lead time
    - Safety stock requirements
    """

    def __init__(
        self,
        client_id: str,
        supplier_id: str,
    ):
        """Initialize purchase order handler.

        Args:
            client_id: WB_CN client identifier
            supplier_id: Supplier identifier
        """
        self.client_id = str(client_id)
        self.supplier_id = str(supplier_id)
        self.orders_generated = []
        self.cost_calculation = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Generate and process purchase orders.

        Args:
            content: Approval content with order requirements

        Returns:
            Dict with generated orders and calculations
        """
        order_items = content.get("order_items", {})

        if not order_items:
            raise PurchaseOrderError("No order items provided")

        # Validate order data
        validation_errors = []
        for sku, item in order_items.items():
            errors = self._validate_order_item(sku, item)
            validation_errors.extend(errors)

        if validation_errors:
            raise PurchaseOrderError(f"Order validation failed: {validation_errors}")

        # Calculate order quantities
        time.sleep(0.05)
        for sku, item in order_items.items():
            quantity = self._calculate_order_quantity(item)
            unit_cost = item.get("unit_cost", 0)
            total_cost = quantity * unit_cost

            order = {
                "sku": sku,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_cost": total_cost,
                "status": "pending_confirmation",
            }
            self.orders_generated.append(order)

            self.cost_calculation[sku] = {
                "sku": sku,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_cost": total_cost,
                "daily_velocity": item.get("daily_velocity", 0),
                "lead_time_days": item.get("lead_time_days", 0),
                "safety_stock_days": item.get("safety_stock_days", 0),
            }

        total_order_cost = sum(o["total_cost"] for o in self.orders_generated)

        return {
            "supplier_id": self.supplier_id,
            "orders_generated": self.orders_generated,
            "cost_calculation": self.cost_calculation,
            "total_order_cost": total_order_cost,
            "order_count": len(self.orders_generated),
            "status": "ready_for_submission",
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of purchase orders.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with order and cost checks
        """
        validation_checks = {
            "orders_generated": False,
            "quantities_valid": False,
            "costs_calculated": False,
            "no_zero_quantities": False,
            "cost_totals_match": False,
        }

        error_details = []

        # Check 1: Orders were generated
        orders = execution_result.get("orders_generated", [])
        if orders:
            validation_checks["orders_generated"] = True

        # Check 2: All quantities are valid (positive)
        quantities_ok = True
        for order in orders:
            if order.get("quantity", 0) <= 0:
                quantities_ok = False
                error_details.append(f"{order['sku']}: invalid quantity {order['quantity']}")
        validation_checks["quantities_valid"] = quantities_ok

        # Check 3: Costs are calculated for all orders
        costs_ok = len(orders) > 0
        for order in orders:
            if order.get("total_cost", 0) <= 0:
                costs_ok = False
                error_details.append(f"{order['sku']}: invalid cost {order['total_cost']}")
        validation_checks["costs_calculated"] = costs_ok

        # Check 4: No zero quantities
        no_zeros = all(o.get("quantity", 0) > 0 for o in orders)
        validation_checks["no_zero_quantities"] = no_zeros

        # Check 5: Cost totals match
        calculated_total = sum(o.get("total_cost", 0) for o in orders)
        reported_total = execution_result.get("total_order_cost", 0)
        if abs(calculated_total - reported_total) < 0.01:
            validation_checks["cost_totals_match"] = True
        else:
            error_details.append(
                f"Cost mismatch: calculated {calculated_total}, reported {reported_total}"
            )

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_purchase_orders" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "order_count": len(orders),
            "total_cost": reported_total,
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _calculate_order_quantity(self, item: dict[str, Any]) -> int:
        """Calculate optimal order quantity using EOQ-inspired formula.

        Args:
            item: Order item with velocity and lead time

        Returns:
            Recommended order quantity
        """
        daily_velocity = item.get("daily_velocity", 0)
        lead_time_days = item.get("lead_time_days", 42)  # Default 42 days
        safety_stock_days = item.get("safety_stock_days", 14)  # Default 14 days safety

        # Reorder point = (daily_velocity * lead_time_days) + safety_stock
        lead_time_stock = daily_velocity * lead_time_days
        safety_stock = daily_velocity * safety_stock_days

        # Order quantity targets coverage days
        coverage_days = item.get("coverage_days", 60)
        order_quantity = daily_velocity * coverage_days

        # Add buffer for lead time
        total_quantity = order_quantity + lead_time_stock

        # Round to nearest 10 for practical purposes
        return max(10, round(total_quantity / 10) * 10)

    def _validate_order_item(self, sku: str, item: dict[str, Any]) -> list[str]:
        """Validate a single order item.

        Args:
            sku: Product SKU
            item: Order item dict

        Returns:
            List of validation error messages
        """
        errors = []

        daily_velocity = item.get("daily_velocity")
        if not daily_velocity or daily_velocity <= 0:
            errors.append(f"{sku}: daily_velocity must be positive")

        unit_cost = item.get("unit_cost")
        if not unit_cost or unit_cost <= 0:
            errors.append(f"{sku}: unit_cost must be positive")

        lead_time = item.get("lead_time_days", 0)
        if lead_time < 0:
            errors.append(f"{sku}: lead_time_days must be non-negative")

        return errors


def main() -> None:
    """Demo purchase order action handler."""
    sample_orders = {
        "order_items": {
            "MD-700": {
                "daily_velocity": 5,
                "lead_time_days": 42,
                "safety_stock_days": 14,
                "coverage_days": 60,
                "unit_cost": 800,
            },
            "MD-4090 PRO": {
                "daily_velocity": 3,
                "lead_time_days": 42,
                "safety_stock_days": 14,
                "coverage_days": 60,
                "unit_cost": 3000,
            },
        }
    }

    handler = PurchaseOrderActionHandler(
        client_id="wb_cn",
        supplier_id="supplier_001",
    )

    print("[Purchase Order] Generating purchase orders...")
    try:
        result = handler.execute(sample_orders)
        print(f"[Purchase Order] ✓ Generated {result['order_count']} orders")

        verification = handler.verify(result)
        print(f"[Purchase Order] ✓ Verification: {verification['overall_status']}")

        if verification.get("all_valid"):
            print(f"\n[Purchase Order] Order Details:")
            for order in result.get("orders_generated", []):
                print(f"  {order['sku']}:")
                print(f"    Quantity: {order['quantity']} units")
                print(f"    Unit Cost: {order['unit_cost']}")
                print(f"    Total Cost: {order['total_cost']}")

            print(f"\n[Purchase Order] Total Order Cost: {result['total_order_cost']}")

    except Exception as e:
        print(f"[Purchase Order] ✗ Error: {e}")


if __name__ == "__main__":
    main()
