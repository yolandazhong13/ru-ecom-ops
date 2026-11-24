#!/usr/bin/env python3
"""Concrete ActionHandler for supplier evaluation and management on WB_CN.

Implements supplier assessment with:
1. Lead time and reliability scoring
2. Quality metrics tracking
3. Pricing competitiveness analysis
4. Supplier recommendation for sourcing decisions
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class SupplierEvaluationError(Exception):
    """Raised when supplier evaluation fails."""
    pass


class SupplierActionHandler(ActionHandler):
    """Handles supplier evaluation and management for WB_CN.

    Evaluates suppliers based on lead time, quality, reliability,
    and pricing to support sourcing decisions.
    """

    def __init__(
        self,
        client_id: str,
        supplier_data: dict[str, dict],
    ):
        """Initialize supplier handler.

        Args:
            client_id: WB_CN client identifier
            supplier_data: Dict mapping supplier_id to supplier info:
                {
                    "supplier_001": {
                        "name": "Factory ABC",
                        "lead_time_days": 42,
                        "quality_score": 0.95,
                        "on_time_delivery_rate": 0.98,
                        "avg_price_per_unit": 800,
                        "min_order_qty": 100
                    }
                }
        """
        self.client_id = str(client_id)
        self.supplier_data = supplier_data
        self.evaluation_results = {}
        self.recommendations = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute supplier evaluation per content_for_approval.

        Args:
            content: Approval content with evaluation criteria

        Returns:
            Dict with supplier scores and recommendations
        """
        # Validate supplier data
        validation_errors = []
        for supplier_id, supplier_info in self.supplier_data.items():
            errors = self._validate_supplier(supplier_id, supplier_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise SupplierEvaluationError(f"Supplier validation failed: {validation_errors}")

        # Evaluate each supplier
        for supplier_id, supplier_info in self.supplier_data.items():
            score = self._calculate_supplier_score(supplier_id, supplier_info)
            self.evaluation_results[supplier_id] = score

        # Generate recommendations
        self.recommendations = self._generate_recommendations()

        return {
            "supplier_data": self.supplier_data,
            "evaluation_results": self.evaluation_results,
            "recommendations": self.recommendations,
            "supplier_count": len(self.supplier_data),
            "recommendation_summary": self._summarize_recommendations(),
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
            "scores_in_valid_range": False,
            "recommendations_provided": False,
            "no_incomplete_data": False,
            "ranking_consistent": False,
        }

        error_details = []

        # Check 1: All suppliers evaluated
        evaluation_results = execution_result.get("evaluation_results", {})
        supplier_data = execution_result.get("supplier_data", {})
        if len(evaluation_results) == len(supplier_data) and len(supplier_data) > 0:
            validation_checks["all_suppliers_evaluated"] = True

        # Check 2: Scores in valid range (0-100)
        scores_valid = True
        for supplier_id, score_dict in evaluation_results.items():
            overall_score = score_dict.get("overall_score", 0)
            if not (0 <= overall_score <= 100):
                scores_valid = False
                error_details.append(f"{supplier_id}: score {overall_score} out of range")
        validation_checks["scores_in_valid_range"] = scores_valid

        # Check 3: Recommendations provided
        recommendations = execution_result.get("recommendations", {})
        if recommendations and len(recommendations) > 0:
            validation_checks["recommendations_provided"] = True
        else:
            error_details.append("No recommendations generated")

        # Check 4: No incomplete data
        no_incomplete = True
        for supplier_id, score_dict in evaluation_results.items():
            required_fields = ["lead_time_score", "quality_score", "reliability_score",
                             "price_score", "overall_score"]
            for field in required_fields:
                if field not in score_dict:
                    no_incomplete = False
                    error_details.append(f"{supplier_id}: missing {field}")
        validation_checks["no_incomplete_data"] = no_incomplete

        # Check 5: Ranking consistent (top-ranked suppliers have highest scores)
        ranking_consistent = True
        sorted_suppliers = sorted(
            evaluation_results.items(),
            key=lambda x: x[1].get("overall_score", 0),
            reverse=True
        )
        top_suppliers = [s[0] for s in sorted_suppliers[:3]]
        if top_suppliers:
            # Verify top suppliers are in recommendations
            for supplier_id in top_suppliers:
                if supplier_id not in recommendations.get("top_candidates", []):
                    ranking_consistent = False
                    error_details.append(f"Top supplier {supplier_id} not in top candidates")
        validation_checks["ranking_consistent"] = ranking_consistent

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_supplier_evaluation" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "supplier_count": len(evaluation_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_supplier(self, supplier_id: str, supplier_info: dict[str, Any]) -> list[str]:
        """Validate a single supplier entry.

        Args:
            supplier_id: Supplier identifier
            supplier_info: Supplier info dict

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate required fields
        required_fields = {
            "name": str,
            "lead_time_days": (int, float),
            "quality_score": (int, float),
            "on_time_delivery_rate": (int, float),
            "avg_price_per_unit": (int, float),
            "min_order_qty": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in supplier_info:
                errors.append(f"{supplier_id}: missing required field {field}")
                continue

            value = supplier_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{supplier_id}: {field} must be {field_type}")

        # Validate ranges
        if "quality_score" in supplier_info:
            score = supplier_info["quality_score"]
            if not (0 <= score <= 1):
                errors.append(f"{supplier_id}: quality_score must be between 0 and 1")

        if "on_time_delivery_rate" in supplier_info:
            rate = supplier_info["on_time_delivery_rate"]
            if not (0 <= rate <= 1):
                errors.append(f"{supplier_id}: on_time_delivery_rate must be between 0 and 1")

        # Validate lead time is positive
        if "lead_time_days" in supplier_info:
            days = supplier_info["lead_time_days"]
            if days < 0:
                errors.append(f"{supplier_id}: lead_time_days must be positive")

        return errors

    def _calculate_supplier_score(self, supplier_id: str, supplier_info: dict[str, Any]) -> dict[str, Any]:
        """Calculate composite score for a supplier.

        Args:
            supplier_id: Supplier identifier
            supplier_info: Supplier info dict

        Returns:
            Dict with individual and overall scores
        """
        # Lead time score (lower is better, normalized to 0-100)
        lead_time = supplier_info.get("lead_time_days", 100)
        lead_time_score = max(0, 100 - (lead_time / 60 * 100))  # 60 days = 0 score

        # Quality score (convert 0-1 to 0-100)
        quality_score = supplier_info.get("quality_score", 0.5) * 100

        # Reliability score (convert 0-1 to 0-100)
        reliability_score = supplier_info.get("on_time_delivery_rate", 0.5) * 100

        # Price score (lower is better, normalized)
        avg_price = supplier_info.get("avg_price_per_unit", 1000)
        price_score = max(0, 100 - (avg_price / 2000 * 100))  # 2000 = reference price

        # Weighted overall score
        overall_score = (
            lead_time_score * 0.25 +
            quality_score * 0.30 +
            reliability_score * 0.30 +
            price_score * 0.15
        )

        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_info.get("name", supplier_id),
            "lead_time_score": round(lead_time_score, 1),
            "quality_score": round(quality_score, 1),
            "reliability_score": round(reliability_score, 1),
            "price_score": round(price_score, 1),
            "overall_score": round(overall_score, 1),
            "lead_time_days": lead_time,
            "quality": supplier_info.get("quality_score", 0),
            "reliability": supplier_info.get("on_time_delivery_rate", 0),
            "avg_price": supplier_info.get("avg_price_per_unit", 0),
        }

    def _generate_recommendations(self) -> dict[str, Any]:
        """Generate supplier recommendations based on evaluation.

        Returns:
            Dict with top candidates and sourcing recommendations
        """
        # Sort by overall score
        sorted_suppliers = sorted(
            self.evaluation_results.items(),
            key=lambda x: x[1].get("overall_score", 0),
            reverse=True
        )

        top_candidates = [s[0] for s in sorted_suppliers[:3]]

        recommendations = {
            "top_candidates": top_candidates,
            "primary_supplier": top_candidates[0] if top_candidates else None,
            "backup_suppliers": top_candidates[1:3] if len(top_candidates) > 1 else [],
            "evaluation_timestamp": "2026-11-23T00:00:00+08:00",
        }

        return recommendations

    def _summarize_recommendations(self) -> dict[str, Any]:
        """Summarize key recommendation insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.evaluation_results:
            return {"total_suppliers": 0}

        scores = [r.get("overall_score", 0) for r in self.evaluation_results.values()]

        return {
            "total_suppliers": len(self.evaluation_results),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "highest_score": round(max(scores), 1) if scores else 0,
            "lowest_score": round(min(scores), 1) if scores else 0,
            "primary_sourcing": self.recommendations.get("primary_supplier"),
        }
