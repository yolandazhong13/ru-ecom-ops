#!/usr/bin/env python3
"""Concrete ActionHandler for inventory replenishment analysis on WB_CN.

Implements replenishment workflow with:
1. Current inventory level assessment
2. Days available calculation
3. Replenishment need determination
4. Safety stock and coverage targets
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class InventoryReplenishmentError(Exception):
    """Raised when inventory replenishment operations fail."""
    pass


class InventoryReplenishmentActionHandler(ActionHandler):
    """Handles inventory replenishment analysis for WB_CN.

    Analyzes current stock levels, calculates coverage days, and
    recommends replenishment quantities based on demand and safety targets.
    """

    def __init__(
        self,
        client_id: str,
        inventory_data: dict[str, dict],
    ):
        """Initialize inventory replenishment handler.

        Args:
            client_id: WB_CN client identifier
            inventory_data: Dict mapping sku to inventory info:
                {
                    "wb1xx5bipa": {
                        "sku": "wb1xx5bipa",
                        "product_name": "Mesh Speaker",
                        "current_stock": 450,
                        "in_transit_qty": 300,
                        "daily_avg_sales": 15,
                        "is_flagship": False,
                        "safety_stock": 60,
                        "reorder_point": 90,
                        "lead_time_days": 7,
                        "cost_per_unit": 450
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "inventory_replenishment"
        self.platform = "WB_CN"
        self.inventory_data = inventory_data
        self.analysis_results = {}
        self.replenishment_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute inventory replenishment analysis.

        Args:
            content: Approval content with replenishment criteria

        Returns:
            Dict with replenishment analysis and recommendations
        """
        # Validate inventory data
        validation_errors = []
        for sku, sku_info in self.inventory_data.items():
            errors = self._validate_inventory_data(sku, sku_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise InventoryReplenishmentError(f"Inventory validation failed: {validation_errors}")

        # Analyze each SKU for replenishment
        for sku, sku_info in self.inventory_data.items():
            analysis = self._analyze_replenishment_need(sku, sku_info)
            self.analysis_results[sku] = analysis

        # Generate replenishment summary
        self.replenishment_summary = self._generate_replenishment_summary()

        return {
            "inventory_data": self.inventory_data,
            "analysis_results": self.analysis_results,
            "replenishment_summary": self.replenishment_summary,
            "sku_count": len(self.inventory_data),
            "replenishment_strategy": self._summarize_replenishment_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of replenishment analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with replenishment checks
        """
        validation_checks = {
            "all_skus_analyzed": False,
            "coverage_days_valid": False,
            "status_levels_valid": False,
            "replenishment_quantities_calculated": False,
            "stock_metrics_complete": False,
        }

        error_details = []

        # Check 1: All SKUs analyzed
        analysis_results = execution_result.get("analysis_results", {})
        inventory_data = execution_result.get("inventory_data", {})
        if len(analysis_results) == len(inventory_data) and len(inventory_data) > 0:
            validation_checks["all_skus_analyzed"] = True

        # Check 2: Coverage days valid (0-365)
        coverage_valid = True
        for sku, analysis in analysis_results.items():
            coverage = analysis.get("days_available", 0)
            if not (0 <= coverage <= 365):
                coverage_valid = False
                error_details.append(f"{sku}: days_available {coverage} out of range")
        validation_checks["coverage_days_valid"] = coverage_valid

        # Check 3: Status levels valid
        status_valid = True
        valid_statuses = {"RED", "ORANGE", "YELLOW", "GREEN"}
        for sku, analysis in analysis_results.items():
            status = analysis.get("status_level", "UNKNOWN")
            if status not in valid_statuses:
                status_valid = False
                error_details.append(f"{sku}: invalid status_level {status}")
        validation_checks["status_levels_valid"] = status_valid

        # Check 4: Replenishment quantities calculated
        quantities_calculated = True
        for sku, analysis in analysis_results.items():
            replenish_qty = analysis.get("replenishment_quantity", None)
            if replenish_qty is None:
                quantities_calculated = False
                error_details.append(f"{sku}: replenishment_quantity not calculated")
        validation_checks["replenishment_quantities_calculated"] = quantities_calculated

        # Check 5: Stock metrics complete
        metrics_complete = True
        for sku, analysis in analysis_results.items():
            required_fields = [
                "current_stock", "in_transit_qty", "daily_avg_sales",
                "safety_stock", "coverage_days", "status_level"
            ]
            for field in required_fields:
                if field not in analysis or analysis[field] is None:
                    metrics_complete = False
                    error_details.append(f"{sku}: missing metric {field}")
        validation_checks["stock_metrics_complete"] = metrics_complete

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_replenishment_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "sku_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_inventory_data(self, sku: str, sku_info: dict[str, Any]) -> list[str]:
        """Validate inventory data for a SKU.

        Args:
            sku: SKU identifier
            sku_info: SKU info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "sku": str,
            "product_name": str,
            "current_stock": int,
            "in_transit_qty": int,
            "daily_avg_sales": (int, float),
            "is_flagship": bool,
            "safety_stock": int,
            "reorder_point": int,
            "lead_time_days": int,
            "cost_per_unit": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in sku_info:
                errors.append(f"{sku}: missing required field {field}")
                continue

            value = sku_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{sku}: {field} must be {field_type}")

        # Validate ranges
        if "current_stock" in sku_info and sku_info["current_stock"] < 0:
            errors.append(f"{sku}: current_stock must be non-negative")

        if "in_transit_qty" in sku_info and sku_info["in_transit_qty"] < 0:
            errors.append(f"{sku}: in_transit_qty must be non-negative")

        if "daily_avg_sales" in sku_info and sku_info["daily_avg_sales"] < 0:
            errors.append(f"{sku}: daily_avg_sales must be non-negative")

        if "safety_stock" in sku_info and sku_info["safety_stock"] < 0:
            errors.append(f"{sku}: safety_stock must be non-negative")

        if "lead_time_days" in sku_info and sku_info["lead_time_days"] < 0:
            errors.append(f"{sku}: lead_time_days must be non-negative")

        return errors

    def _analyze_replenishment_need(self, sku: str, sku_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze replenishment need for a single SKU.

        Args:
            sku: SKU identifier
            sku_info: SKU info dict

        Returns:
            Dict with replenishment analysis
        """
        current_stock = sku_info.get("current_stock", 0)
        in_transit_qty = sku_info.get("in_transit_qty", 0)
        daily_avg_sales = sku_info.get("daily_avg_sales", 0)
        is_flagship = sku_info.get("is_flagship", False)
        safety_stock = sku_info.get("safety_stock", 0)
        reorder_point = sku_info.get("reorder_point", 0)
        lead_time_days = sku_info.get("lead_time_days", 0)
        cost_per_unit = sku_info.get("cost_per_unit", 0)

        # Calculate days available (current stock / daily sales)
        if daily_avg_sales > 0:
            days_available = current_stock / daily_avg_sales
        else:
            days_available = 365  # Assume infinite if no sales

        # Determine status level based on days available
        # RED: 0-10 days, ORANGE: 11-20 days, YELLOW: 21-40 days, GREEN: 40+ days
        if days_available <= 10:
            status_level = "RED"
        elif days_available <= 20:
            status_level = "ORANGE"
        elif days_available <= 40:
            status_level = "YELLOW"
        else:
            status_level = "GREEN"

        # Determine target coverage days based on flagship status
        target_coverage_days = 75 if is_flagship else 60

        # Calculate replenishment quantity
        # Formula: target_coverage_days × daily_avg_sales - current_stock - in_transit + safety_stock
        if daily_avg_sales > 0:
            replenishment_qty = max(
                0,
                (target_coverage_days * daily_avg_sales) - current_stock - in_transit_qty + safety_stock
            )
        else:
            replenishment_qty = 0

        # Calculate replenishment cost
        replenishment_cost = replenishment_qty * cost_per_unit

        # Determine urgency
        if status_level == "RED":
            urgency = "CRITICAL"
        elif status_level == "ORANGE":
            urgency = "HIGH"
        elif status_level == "YELLOW":
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        # Decision
        needs_replenishment = status_level in {"RED", "ORANGE", "YELLOW"}

        return {
            "sku": sku,
            "product_name": sku_info.get("product_name", sku),
            "current_stock": current_stock,
            "in_transit_qty": in_transit_qty,
            "total_available": current_stock + in_transit_qty,
            "daily_avg_sales": round(daily_avg_sales, 2),
            "safety_stock": safety_stock,
            "days_available": round(days_available, 1),
            "target_coverage_days": target_coverage_days,
            "status_level": status_level,
            "urgency": urgency,
            "needs_replenishment": needs_replenishment,
            "replenishment_quantity": int(replenishment_qty),
            "replenishment_cost_rub": round(replenishment_cost, 2),
            "is_flagship": is_flagship,
            "lead_time_days": lead_time_days,
            "reorder_point": reorder_point,
        }

    def _generate_replenishment_summary(self) -> dict[str, Any]:
        """Generate replenishment summary.

        Returns:
            Dict with replenishment summary
        """
        critical_skus = []
        high_priority_skus = []
        medium_priority_skus = []
        low_priority_skus = []

        total_replenishment_qty = 0
        total_replenishment_cost = 0

        for sku, analysis in self.analysis_results.items():
            urgency = analysis.get("urgency", "UNKNOWN")
            if urgency == "CRITICAL":
                critical_skus.append(sku)
            elif urgency == "HIGH":
                high_priority_skus.append(sku)
            elif urgency == "MEDIUM":
                medium_priority_skus.append(sku)
            else:
                low_priority_skus.append(sku)

            if analysis.get("needs_replenishment"):
                total_replenishment_qty += analysis.get("replenishment_quantity", 0)
                total_replenishment_cost += analysis.get("replenishment_cost_rub", 0)

        return {
            "critical_replenishment": critical_skus,
            "high_priority_replenishment": high_priority_skus,
            "medium_priority_replenishment": medium_priority_skus,
            "low_priority_replenishment": low_priority_skus,
            "total_critical": len(critical_skus),
            "total_high": len(high_priority_skus),
            "total_medium": len(medium_priority_skus),
            "total_low": len(low_priority_skus),
            "total_replenishment_qty": int(total_replenishment_qty),
            "total_replenishment_cost_rub": round(total_replenishment_cost, 2),
            "replenishment_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_replenishment_strategy(self) -> dict[str, Any]:
        """Summarize replenishment strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_skus": 0}

        total_stock = sum(a.get("current_stock", 0) for a in self.analysis_results.values())
        total_in_transit = sum(a.get("in_transit_qty", 0) for a in self.analysis_results.values())
        total_daily_sales = sum(a.get("daily_avg_sales", 0) for a in self.analysis_results.values())

        # Calculate portfolio average days available
        avg_days_available = sum(a.get("days_available", 0) for a in self.analysis_results.values()) / len(self.analysis_results) if self.analysis_results else 0

        # Count by status
        red_count = sum(1 for a in self.analysis_results.values() if a.get("status_level") == "RED")
        orange_count = sum(1 for a in self.analysis_results.values() if a.get("status_level") == "ORANGE")
        yellow_count = sum(1 for a in self.analysis_results.values() if a.get("status_level") == "YELLOW")
        green_count = sum(1 for a in self.analysis_results.values() if a.get("status_level") == "GREEN")

        return {
            "total_skus": len(self.analysis_results),
            "total_current_stock": int(total_stock),
            "total_in_transit": int(total_in_transit),
            "total_portfolio_stock": int(total_stock + total_in_transit),
            "total_daily_sales": round(total_daily_sales, 2),
            "avg_days_available": round(avg_days_available, 1),
            "status_distribution": {
                "RED": red_count,
                "ORANGE": orange_count,
                "YELLOW": yellow_count,
                "GREEN": green_count,
            },
            "needs_immediate_attention": red_count > 0,
            "replenishment_budget_required": self.replenishment_summary.get("total_replenishment_cost_rub", 0),
        }
