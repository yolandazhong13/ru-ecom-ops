#!/usr/bin/env python3
"""Concrete ActionHandler for returns analysis and profitability tracking on WB_CN.

Implements returns workflow with:
1. Return rate monitoring and analysis
2. Profitability impact calculation
3. Root cause identification
4. Corrective action recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class ReturnsProfitError(Exception):
    """Raised when returns/profit operations fail."""
    pass


class ReturnsProfitActionHandler(ActionHandler):
    """Handles returns analysis and profitability tracking for WB_CN.

    Monitors return rates, analyzes root causes, and quantifies
    profitability impact to recommend corrective actions.
    """

    def __init__(
        self,
        client_id: str,
        returns_data: dict[str, dict],
    ):
        """Initialize returns/profit handler.

        Args:
            client_id: WB_CN client identifier
            returns_data: Dict mapping product_id to returns info:
                {
                    "MD-700": {
                        "product_id": "MD-700",
                        "product_name": "Mesh Speaker",
                        "total_orders": 500,
                        "returned_orders": 25,
                        "avg_return_reason": "quality_issue",
                        "revenue_per_order": 2500,
                        "cost_per_order": 1200,
                        "return_processing_cost": 150,
                        "replacement_rate": 0.3,
                        "refund_rate": 0.7
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "returns_profit"
        self.platform = "WB_CN"
        self.returns_data = returns_data
        self.analysis_results = {}
        self.profitability_impact = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute returns and profitability analysis.

        Args:
            content: Approval content with returns analysis criteria

        Returns:
            Dict with returns analysis and profitability impact
        """
        # Validate returns data
        validation_errors = []
        for product_id, product_info in self.returns_data.items():
            errors = self._validate_returns_data(product_id, product_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise ReturnsProfitError(f"Returns validation failed: {validation_errors}")

        # Analyze returns for each product
        for product_id, product_info in self.returns_data.items():
            analysis = self._analyze_returns_impact(product_id, product_info)
            self.analysis_results[product_id] = analysis

        # Generate profitability impact summary
        self.profitability_impact = self._calculate_profitability_impact()

        return {
            "returns_data": self.returns_data,
            "analysis_results": self.analysis_results,
            "profitability_impact": self.profitability_impact,
            "product_count": len(self.returns_data),
            "returns_strategy": self._summarize_returns_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of returns analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with returns checks
        """
        validation_checks = {
            "all_products_analyzed": False,
            "return_rates_valid": False,
            "profitability_impact_calculated": False,
            "root_causes_identified": False,
            "corrective_actions_provided": False,
        }

        error_details = []

        # Check 1: All products analyzed
        analysis_results = execution_result.get("analysis_results", {})
        returns_data = execution_result.get("returns_data", {})
        if len(analysis_results) == len(returns_data) and len(returns_data) > 0:
            validation_checks["all_products_analyzed"] = True

        # Check 2: Return rates valid (0-100%)
        rates_valid = True
        for product_id, analysis in analysis_results.items():
            return_rate = analysis.get("return_rate_percent", 0)
            if not (0 <= return_rate <= 100):
                rates_valid = False
                error_details.append(f"{product_id}: return_rate {return_rate}% out of range")
        validation_checks["return_rates_valid"] = rates_valid

        # Check 3: Profitability impact calculated
        impact = execution_result.get("profitability_impact", {})
        if impact and "total_loss_rub" in impact:
            validation_checks["profitability_impact_calculated"] = True
        else:
            error_details.append("Profitability impact not calculated")

        # Check 4: Root causes identified
        causes_identified = True
        for product_id, analysis in analysis_results.items():
            root_cause = analysis.get("root_cause", None)
            if not root_cause:
                causes_identified = False
                error_details.append(f"{product_id}: root_cause not identified")
        validation_checks["root_causes_identified"] = causes_identified

        # Check 5: Corrective actions provided
        actions_provided = True
        for product_id, analysis in analysis_results.items():
            actions = analysis.get("corrective_actions", [])
            if not actions or len(actions) == 0:
                actions_provided = False
                error_details.append(f"{product_id}: no corrective actions provided")
        validation_checks["corrective_actions_provided"] = actions_provided

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_returns_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "product_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_returns_data(self, product_id: str, product_info: dict[str, Any]) -> list[str]:
        """Validate returns data for a product.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "product_id": str,
            "product_name": str,
            "total_orders": int,
            "returned_orders": int,
            "avg_return_reason": str,
            "revenue_per_order": (int, float),
            "cost_per_order": (int, float),
            "return_processing_cost": (int, float),
            "replacement_rate": (int, float),
            "refund_rate": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in product_info:
                errors.append(f"{product_id}: missing required field {field}")
                continue

            value = product_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{product_id}: {field} must be {field_type}")

        # Validate ranges
        if "total_orders" in product_info and product_info["total_orders"] < 0:
            errors.append(f"{product_id}: total_orders must be non-negative")

        if "returned_orders" in product_info and product_info["returned_orders"] < 0:
            errors.append(f"{product_id}: returned_orders must be non-negative")

        # Validate logical consistency
        total = product_info.get("total_orders", 0)
        returned = product_info.get("returned_orders", 0)
        if returned > total:
            errors.append(f"{product_id}: returned_orders cannot exceed total_orders")

        # Validate rate fractions
        if "replacement_rate" in product_info:
            rate = product_info["replacement_rate"]
            if not (0 <= rate <= 1):
                errors.append(f"{product_id}: replacement_rate must be between 0 and 1")

        if "refund_rate" in product_info:
            rate = product_info["refund_rate"]
            if not (0 <= rate <= 1):
                errors.append(f"{product_id}: refund_rate must be between 0 and 1")

        return errors

    def _analyze_returns_impact(self, product_id: str, product_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze returns impact for a single product.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            Dict with returns analysis
        """
        total_orders = product_info.get("total_orders", 1)
        returned_orders = product_info.get("returned_orders", 0)
        avg_return_reason = product_info.get("avg_return_reason", "unknown")
        revenue_per_order = product_info.get("revenue_per_order", 0)
        cost_per_order = product_info.get("cost_per_order", 0)
        return_processing_cost = product_info.get("return_processing_cost", 0)
        replacement_rate = product_info.get("replacement_rate", 0)
        refund_rate = product_info.get("refund_rate", 0)

        # Calculate return rate
        return_rate = (returned_orders / total_orders * 100) if total_orders > 0 else 0

        # Calculate financial impact per return
        refund_loss = revenue_per_order * refund_rate
        replacement_cost = cost_per_order * replacement_rate
        total_loss_per_return = refund_loss + replacement_cost + return_processing_cost

        # Calculate total impact
        total_impact_rub = total_loss_per_return * returned_orders

        # Determine severity level
        if return_rate > 10:
            severity = "CRITICAL"
            risk_level = 5
        elif return_rate > 5:
            severity = "HIGH"
            risk_level = 4
        elif return_rate > 2:
            severity = "MEDIUM"
            risk_level = 3
        else:
            severity = "LOW"
            risk_level = 1

        # Categorize root cause and suggest actions
        root_cause_analysis = self._categorize_root_cause(avg_return_reason, return_rate)
        corrective_actions = self._recommend_corrective_actions(avg_return_reason, return_rate)

        # Calculate projected impact if trend continues
        monthly_projected_loss = (total_impact_rub / 30) if total_orders > 0 else 0

        return {
            "product_id": product_id,
            "product_name": product_info.get("product_name", product_id),
            "total_orders": total_orders,
            "returned_orders": returned_orders,
            "return_rate_percent": round(return_rate, 2),
            "avg_return_reason": avg_return_reason,
            "revenue_per_order": round(revenue_per_order, 2),
            "cost_per_order": round(cost_per_order, 2),
            "return_processing_cost": round(return_processing_cost, 2),
            "loss_per_return_rub": round(total_loss_per_return, 2),
            "total_loss_rub": round(total_impact_rub, 2),
            "monthly_projected_loss_rub": round(monthly_projected_loss, 2),
            "replacement_rate": replacement_rate,
            "refund_rate": refund_rate,
            "root_cause": root_cause_analysis,
            "severity_level": severity,
            "risk_level": risk_level,
            "corrective_actions": corrective_actions,
        }

    def _categorize_root_cause(self, reason: str, return_rate: float) -> str:
        """Categorize root cause of returns.

        Args:
            reason: Primary return reason
            return_rate: Return rate percentage

        Returns:
            Root cause category
        """
        reason_lower = reason.lower()

        if "quality" in reason_lower or "defect" in reason_lower:
            return "QUALITY_DEFECTS"
        elif "mismatch" in reason_lower or "description" in reason_lower:
            return "PRODUCT_MISMATCH"
        elif "damage" in reason_lower:
            return "SHIPPING_DAMAGE"
        elif "wrong" in reason_lower or "error" in reason_lower:
            return "FULFILLMENT_ERROR"
        else:
            return "OTHER"

    def _recommend_corrective_actions(self, reason: str, return_rate: float) -> list[str]:
        """Recommend corrective actions based on root cause.

        Args:
            reason: Primary return reason
            return_rate: Return rate percentage

        Returns:
            List of recommended actions
        """
        actions = []
        reason_lower = reason.lower()

        if "quality" in reason_lower or "defect" in reason_lower:
            actions.append("Audit manufacturing/supplier quality control")
            actions.append("Implement pre-shipment quality inspection")
            if return_rate > 5:
                actions.append("Consider alternative supplier evaluation")

        elif "mismatch" in reason_lower or "description" in reason_lower:
            actions.append("Review and enhance product description accuracy")
            actions.append("Add more detailed product images and specifications")
            actions.append("Clarify size/material/color options in listing")

        elif "damage" in reason_lower:
            actions.append("Evaluate packaging and shipping materials")
            actions.append("Test packaging with logistics partner")
            actions.append("Consider upgraded packaging for fragile items")

        elif "wrong" in reason_lower or "error" in reason_lower:
            actions.append("Audit fulfillment process and picking accuracy")
            actions.append("Implement barcode verification at packing")
            actions.append("Increase quality checks before shipment")

        if return_rate > 10:
            actions.append("Priority: Schedule urgent quality review meeting")
            actions.append("Establish daily return monitoring until improvement")

        if not actions:
            actions.append("Monitor return trends and investigate patterns")
            actions.append("Request detailed feedback from returned items")

        return actions

    def _calculate_profitability_impact(self) -> dict[str, Any]:
        """Calculate overall profitability impact from returns.

        Returns:
            Dict with profitability impact summary
        """
        total_loss = 0
        total_returned = 0
        critical_products = []
        high_risk_products = []

        for product_id, analysis in self.analysis_results.items():
            loss = analysis.get("total_loss_rub", 0)
            total_loss += loss
            total_returned += analysis.get("returned_orders", 0)

            risk_level = analysis.get("risk_level", 1)
            if risk_level == 5:
                critical_products.append(product_id)
            elif risk_level == 4:
                high_risk_products.append(product_id)

        total_orders = sum(a.get("total_orders", 0) for a in self.analysis_results.values())
        overall_return_rate = (total_returned / total_orders * 100) if total_orders > 0 else 0

        return {
            "total_loss_rub": round(total_loss, 2),
            "total_returned_orders": int(total_returned),
            "overall_return_rate_percent": round(overall_return_rate, 2),
            "critical_products": critical_products,
            "high_risk_products": high_risk_products,
            "critical_product_count": len(critical_products),
            "high_risk_product_count": len(high_risk_products),
            "impact_analysis_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_returns_strategy(self) -> dict[str, Any]:
        """Summarize returns strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_products": 0}

        return_rates = [a.get("return_rate_percent", 0) for a in self.analysis_results.values()]
        loss_values = [a.get("total_loss_rub", 0) for a in self.analysis_results.values()]

        # Identify top return reasons
        reason_counts = {}
        for analysis in self.analysis_results.values():
            reason = analysis.get("root_cause", "OTHER")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        top_reason = max(reason_counts, key=reason_counts.get) if reason_counts else "UNKNOWN"

        return {
            "total_products": len(self.analysis_results),
            "avg_return_rate_percent": round(sum(return_rates) / len(return_rates), 2) if return_rates else 0,
            "highest_return_rate_percent": round(max(return_rates), 2) if return_rates else 0,
            "lowest_return_rate_percent": round(min(return_rates), 2) if return_rates else 0,
            "total_financial_loss_rub": round(sum(loss_values), 2),
            "avg_loss_per_product_rub": round(sum(loss_values) / len(loss_values), 2) if loss_values else 0,
            "top_return_reason": top_reason,
            "needs_intervention": len([a for a in self.analysis_results.values() if a.get("severity_level") in {"HIGH", "CRITICAL"}]) > 0,
        }
