#!/usr/bin/env python3
"""Concrete ActionHandler for supplier evaluation and performance tracking on WB_CN.

Implements supplier management workflow with:
1. Supplier performance scoring
2. Quality metrics assessment
3. Delivery reliability tracking
4. Cost competitiveness analysis
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class SupplierEvaluationError(Exception):
    """Raised when supplier evaluation operations fail."""
    pass


class SupplierEvaluationActionHandler(ActionHandler):
    """Handles supplier evaluation and performance tracking for WB_CN.

    Scores suppliers based on quality, delivery, cost, and reliability
    metrics to inform procurement and partnership decisions.
    """

    def __init__(
        self,
        client_id: str,
        supplier_data: dict[str, dict],
    ):
        """Initialize supplier evaluation handler.

        Args:
            client_id: WB_CN client identifier
            supplier_data: Dict mapping supplier_id to supplier info:
                {
                    "supp_001": {
                        "supplier_id": "supp_001",
                        "supplier_name": "Factory Direct",
                        "total_orders": 150,
                        "on_time_deliveries": 142,
                        "defect_rate_percent": 2.5,
                        "avg_response_time_hours": 4,
                        "unit_cost_rub": 450,
                        "market_avg_cost_rub": 500,
                        "communication_score": 4.5,
                        "total_transactions_value_rub": 450000,
                        "years_in_business": 8
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "supplier_evaluation"
        self.platform = "WB_CN"
        self.supplier_data = supplier_data
        self.analysis_results = {}
        self.performance_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute supplier evaluation and scoring.

        Args:
            content: Approval content with supplier evaluation criteria

        Returns:
            Dict with supplier evaluation and recommendations
        """
        # Validate supplier data
        validation_errors = []
        for supplier_id, supplier_info in self.supplier_data.items():
            errors = self._validate_supplier_data(supplier_id, supplier_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise SupplierEvaluationError(f"Supplier validation failed: {validation_errors}")

        # Evaluate each supplier
        for supplier_id, supplier_info in self.supplier_data.items():
            evaluation = self._evaluate_supplier(supplier_id, supplier_info)
            self.analysis_results[supplier_id] = evaluation

        # Generate performance summary
        self.performance_summary = self._generate_performance_summary()

        return {
            "supplier_data": self.supplier_data,
            "analysis_results": self.analysis_results,
            "performance_summary": self.performance_summary,
            "supplier_count": len(self.supplier_data),
            "supplier_strategy": self._summarize_supplier_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of supplier evaluation.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with evaluation checks
        """
        validation_checks = {
            "all_suppliers_evaluated": False,
            "performance_scores_valid": False,
            "quality_metrics_verified": False,
            "delivery_metrics_verified": False,
            "recommendations_provided": False,
        }

        error_details = []

        # Check 1: All suppliers evaluated
        analysis_results = execution_result.get("analysis_results", {})
        supplier_data = execution_result.get("supplier_data", {})
        if len(analysis_results) == len(supplier_data) and len(supplier_data) > 0:
            validation_checks["all_suppliers_evaluated"] = True

        # Check 2: Performance scores valid (0-100)
        scores_valid = True
        for supplier_id, evaluation in analysis_results.items():
            score = evaluation.get("overall_performance_score", 0)
            if not (0 <= score <= 100):
                scores_valid = False
                error_details.append(f"{supplier_id}: performance_score {score} out of range")
        validation_checks["performance_scores_valid"] = scores_valid

        # Check 3: Quality metrics verified
        quality_valid = True
        for supplier_id, evaluation in analysis_results.items():
            defect_rate = evaluation.get("defect_rate_percent", 0)
            if not (0 <= defect_rate <= 100):
                quality_valid = False
                error_details.append(f"{supplier_id}: defect_rate {defect_rate}% out of range")
        validation_checks["quality_metrics_verified"] = quality_valid

        # Check 4: Delivery metrics verified
        delivery_valid = True
        for supplier_id, evaluation in analysis_results.items():
            on_time = evaluation.get("on_time_delivery_rate_percent", 0)
            if not (0 <= on_time <= 100):
                delivery_valid = False
                error_details.append(f"{supplier_id}: on_time_delivery {on_time}% out of range")
        validation_checks["delivery_metrics_verified"] = delivery_valid

        # Check 5: Recommendations provided
        summary = execution_result.get("performance_summary", {})
        if summary and summary.get("tier_distribution"):
            validation_checks["recommendations_provided"] = True
        else:
            error_details.append("No tier recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_supplier_evaluation" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "supplier_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_supplier_data(self, supplier_id: str, supplier_info: dict[str, Any]) -> list[str]:
        """Validate supplier data.

        Args:
            supplier_id: Supplier identifier
            supplier_info: Supplier info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "supplier_id": str,
            "supplier_name": str,
            "total_orders": int,
            "on_time_deliveries": int,
            "defect_rate_percent": (int, float),
            "avg_response_time_hours": (int, float),
            "unit_cost_rub": (int, float),
            "market_avg_cost_rub": (int, float),
            "communication_score": (int, float),
            "total_transactions_value_rub": (int, float),
            "years_in_business": int,
        }

        for field, field_type in required_fields.items():
            if field not in supplier_info:
                errors.append(f"{supplier_id}: missing required field {field}")
                continue

            value = supplier_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{supplier_id}: {field} must be {field_type}")

        # Validate ranges
        if "total_orders" in supplier_info and supplier_info["total_orders"] < 0:
            errors.append(f"{supplier_id}: total_orders must be non-negative")

        if "on_time_deliveries" in supplier_info and supplier_info["on_time_deliveries"] < 0:
            errors.append(f"{supplier_id}: on_time_deliveries must be non-negative")

        # Validate logical consistency
        total = supplier_info.get("total_orders", 0)
        on_time = supplier_info.get("on_time_deliveries", 0)
        if on_time > total:
            errors.append(f"{supplier_id}: on_time_deliveries cannot exceed total_orders")

        # Validate percentages
        if "defect_rate_percent" in supplier_info:
            rate = supplier_info["defect_rate_percent"]
            if not (0 <= rate <= 100):
                errors.append(f"{supplier_id}: defect_rate_percent must be 0-100")

        if "communication_score" in supplier_info:
            score = supplier_info["communication_score"]
            if not (0 <= score <= 5):
                errors.append(f"{supplier_id}: communication_score must be 0-5")

        return errors

    def _evaluate_supplier(self, supplier_id: str, supplier_info: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single supplier.

        Args:
            supplier_id: Supplier identifier
            supplier_info: Supplier info dict

        Returns:
            Dict with supplier evaluation
        """
        total_orders = supplier_info.get("total_orders", 1)
        on_time_deliveries = supplier_info.get("on_time_deliveries", 0)
        defect_rate = supplier_info.get("defect_rate_percent", 0)
        response_time = supplier_info.get("avg_response_time_hours", 0)
        unit_cost = supplier_info.get("unit_cost_rub", 0)
        market_cost = supplier_info.get("market_avg_cost_rub", 0)
        communication_score = supplier_info.get("communication_score", 0)
        transaction_value = supplier_info.get("total_transactions_value_rub", 0)
        years_in_business = supplier_info.get("years_in_business", 0)

        # Calculate delivery reliability score (0-100)
        on_time_rate = (on_time_deliveries / total_orders * 100) if total_orders > 0 else 0
        delivery_score = on_time_rate  # 95%+ = 100 score

        # Calculate quality score (0-100, inverted defect rate)
        quality_score = max(0, 100 - defect_rate)

        # Calculate responsiveness score (0-100, inverted response time)
        # Optimal: <4 hours = 100, 24+ hours = 20
        if response_time <= 4:
            responsiveness_score = 100
        elif response_time >= 24:
            responsiveness_score = 20
        else:
            responsiveness_score = 100 - ((response_time - 4) / 20 * 80)

        # Calculate cost competitiveness score (0-100)
        # Unit cost as % of market average
        if market_cost > 0:
            cost_ratio = (unit_cost / market_cost)
            if cost_ratio <= 0.95:
                cost_score = 100
            elif cost_ratio >= 1.05:
                cost_score = 20
            else:
                cost_score = 100 - ((cost_ratio - 0.95) / 0.1 * 80)
        else:
            cost_score = 50

        # Communication score already 0-5, convert to 0-100
        communication_score_scaled = communication_score * 20

        # Tenure credibility score (0-100)
        # 10+ years = 100, <1 year = 20
        if years_in_business >= 10:
            tenure_score = 100
        elif years_in_business < 1:
            tenure_score = 20
        else:
            tenure_score = 20 + (years_in_business / 10 * 80)

        # Calculate overall performance score
        overall_score = (
            delivery_score * 0.25 +
            quality_score * 0.30 +
            responsiveness_score * 0.15 +
            cost_score * 0.20 +
            communication_score_scaled * 0.10
        )

        # Determine tier based on score
        if overall_score >= 85:
            tier = "TIER_1_STRATEGIC"
            recommendation = "EXPAND_PARTNERSHIP"
        elif overall_score >= 70:
            tier = "TIER_2_PREFERRED"
            recommendation = "MAINTAIN_RELATIONSHIP"
        elif overall_score >= 55:
            tier = "TIER_3_ACCEPTABLE"
            recommendation = "MONITOR_PERFORMANCE"
        else:
            tier = "TIER_4_REVIEW"
            recommendation = "DEVELOP_IMPROVEMENT_PLAN"

        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []

        if delivery_score >= 95:
            strengths.append("Excellent on-time delivery")
        elif delivery_score < 80:
            weaknesses.append(f"Delivery reliability issue ({on_time_rate:.1f}%)")

        if quality_score >= 95:
            strengths.append("High quality standards")
        elif quality_score < 80:
            weaknesses.append(f"Quality concerns ({defect_rate:.1f}% defect rate)")

        if responsiveness_score >= 90:
            strengths.append("Quick response time")
        else:
            weaknesses.append(f"Slow response time ({response_time} hours)")

        if cost_ratio <= 0.95 if market_cost > 0 else False:
            strengths.append("Cost competitive")
        elif cost_ratio >= 1.05 if market_cost > 0 else False:
            weaknesses.append("Cost premium vs market")

        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_info.get("supplier_name", supplier_id),
            "total_orders": total_orders,
            "on_time_deliveries": on_time_deliveries,
            "on_time_delivery_rate_percent": round(on_time_rate, 1),
            "defect_rate_percent": round(defect_rate, 2),
            "avg_response_time_hours": round(response_time, 1),
            "unit_cost_rub": round(unit_cost, 2),
            "market_avg_cost_rub": round(market_cost, 2),
            "cost_ratio": round(cost_ratio if market_cost > 0 else 1.0, 3),
            "communication_score": round(communication_score, 1),
            "years_in_business": years_in_business,
            "total_transactions_value_rub": round(transaction_value, 2),
            "delivery_score": round(delivery_score, 1),
            "quality_score": round(quality_score, 1),
            "responsiveness_score": round(responsiveness_score, 1),
            "cost_competitiveness_score": round(cost_score, 1),
            "communication_score_scaled": round(communication_score_scaled, 1),
            "tenure_credibility_score": round(tenure_score, 1),
            "overall_performance_score": round(overall_score, 1),
            "supplier_tier": tier,
            "recommendation": recommendation,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    def _generate_performance_summary(self) -> dict[str, Any]:
        """Generate supplier performance summary.

        Returns:
            Dict with performance summary
        """
        tier_1_suppliers = []
        tier_2_suppliers = []
        tier_3_suppliers = []
        tier_4_suppliers = []

        total_transaction_value = 0
        avg_scores = {"delivery": 0, "quality": 0, "responsiveness": 0, "cost": 0}

        for supplier_id, evaluation in self.analysis_results.items():
            tier = evaluation.get("supplier_tier", "UNKNOWN")
            if tier == "TIER_1_STRATEGIC":
                tier_1_suppliers.append(supplier_id)
            elif tier == "TIER_2_PREFERRED":
                tier_2_suppliers.append(supplier_id)
            elif tier == "TIER_3_ACCEPTABLE":
                tier_3_suppliers.append(supplier_id)
            else:
                tier_4_suppliers.append(supplier_id)

            total_transaction_value += evaluation.get("total_transactions_value_rub", 0)
            avg_scores["delivery"] += evaluation.get("delivery_score", 0)
            avg_scores["quality"] += evaluation.get("quality_score", 0)
            avg_scores["responsiveness"] += evaluation.get("responsiveness_score", 0)
            avg_scores["cost"] += evaluation.get("cost_competitiveness_score", 0)

        supplier_count = len(self.analysis_results)
        for key in avg_scores:
            avg_scores[key] = avg_scores[key] / supplier_count if supplier_count > 0 else 0

        return {
            "tier_1_strategic": tier_1_suppliers,
            "tier_2_preferred": tier_2_suppliers,
            "tier_3_acceptable": tier_3_suppliers,
            "tier_4_review": tier_4_suppliers,
            "tier_distribution": {
                "TIER_1": len(tier_1_suppliers),
                "TIER_2": len(tier_2_suppliers),
                "TIER_3": len(tier_3_suppliers),
                "TIER_4": len(tier_4_suppliers),
            },
            "total_suppliers": supplier_count,
            "total_transaction_value_rub": round(total_transaction_value, 2),
            "avg_delivery_score": round(avg_scores["delivery"], 1),
            "avg_quality_score": round(avg_scores["quality"], 1),
            "avg_responsiveness_score": round(avg_scores["responsiveness"], 1),
            "avg_cost_score": round(avg_scores["cost"], 1),
            "evaluation_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_supplier_strategy(self) -> dict[str, Any]:
        """Summarize supplier strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_suppliers": 0}

        overall_scores = [a.get("overall_performance_score", 0) for a in self.analysis_results.values()]
        avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0

        actions_needed = []
        for supplier_id, evaluation in self.analysis_results.items():
            if evaluation.get("supplier_tier") == "TIER_4_REVIEW":
                actions_needed.append(supplier_id)
            elif evaluation.get("supplier_tier") == "TIER_1_STRATEGIC" and len(evaluation.get("weaknesses", [])) > 0:
                actions_needed.append(f"{supplier_id} (optimize relationship)")

        return {
            "total_suppliers": len(self.analysis_results),
            "avg_overall_score": round(avg_overall, 1),
            "highest_performer_score": round(max(overall_scores), 1) if overall_scores else 0,
            "lowest_performer_score": round(min(overall_scores), 1) if overall_scores else 0,
            "portfolio_transaction_value": round(self.performance_summary.get("total_transaction_value_rub", 0), 2),
            "suppliers_needing_attention": actions_needed,
            "strategic_partnerships": self.performance_summary.get("tier_distribution", {}).get("TIER_1", 0),
            "portfolio_health": "STRONG" if avg_overall >= 75 else "GOOD" if avg_overall >= 60 else "NEEDS_REVIEW",
        }
