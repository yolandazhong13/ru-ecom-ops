#!/usr/bin/env python3
"""Concrete ActionHandler for product selection and sourcing on WB_CN.

Implements selection workflow with:
1. Market demand analysis
2. Competitive landscape assessment
3. Profitability validation
4. SKU selection recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class SelectionError(Exception):
    """Raised when product selection fails."""
    pass


class SelectionActionHandler(ActionHandler):
    """Handles product selection and sourcing for WB_CN.

    Analyzes market demand, competitive positioning, and profitability
    to recommend SKU selection for sourcing and listing.
    """

    def __init__(
        self,
        client_id: str,
        selection_data: dict[str, dict],
    ):
        """Initialize selection handler.

        Args:
            client_id: WB_CN client identifier
            selection_data: Dict mapping SKU to selection criteria:
                {
                    "MD-700": {
                        "market_demand_rank": 1,
                        "search_volume": 15000,
                        "competitor_count": 45,
                        "avg_competitor_price": 2500,
                        "target_margin": 0.45,
                        "cost": 800,
                        "market_saturation": 0.65
                    }
                }
        """
        self.client_id = str(client_id)
        self.selection_data = selection_data
        self.analysis_results = {}
        self.recommendations = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute product selection analysis per content_for_approval.

        Args:
            content: Approval content with selection criteria

        Returns:
            Dict with selection analysis and recommendations
        """
        # Validate selection data
        validation_errors = []
        for sku, sku_info in self.selection_data.items():
            errors = self._validate_sku_data(sku, sku_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise SelectionError(f"Selection validation failed: {validation_errors}")

        # Analyze each SKU
        for sku, sku_info in self.selection_data.items():
            analysis = self._analyze_sku(sku, sku_info)
            self.analysis_results[sku] = analysis

        # Generate recommendations
        self.recommendations = self._generate_recommendations()

        return {
            "selection_data": self.selection_data,
            "analysis_results": self.analysis_results,
            "recommendations": self.recommendations,
            "sku_count": len(self.selection_data),
            "recommendation_summary": self._summarize_analysis(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of selection analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with analysis checks
        """
        validation_checks = {
            "all_skus_analyzed": False,
            "scores_in_valid_range": False,
            "recommendations_provided": False,
            "market_data_complete": False,
            "profitability_validated": False,
        }

        error_details = []

        # Check 1: All SKUs analyzed
        analysis_results = execution_result.get("analysis_results", {})
        selection_data = execution_result.get("selection_data", {})
        if len(analysis_results) == len(selection_data) and len(selection_data) > 0:
            validation_checks["all_skus_analyzed"] = True

        # Check 2: Scores in valid range (0-100)
        scores_valid = True
        for sku, analysis in analysis_results.items():
            selection_score = analysis.get("selection_score", 0)
            if not (0 <= selection_score <= 100):
                scores_valid = False
                error_details.append(f"{sku}: selection_score {selection_score} out of range")
        validation_checks["scores_in_valid_range"] = scores_valid

        # Check 3: Recommendations provided
        recommendations = execution_result.get("recommendations", {})
        if recommendations and len(recommendations.get("recommended_skus", [])) > 0:
            validation_checks["recommendations_provided"] = True
        else:
            error_details.append("No SKUs recommended")

        # Check 4: Market data complete
        market_complete = True
        for sku, analysis in analysis_results.items():
            required_fields = [
                "search_volume", "competitor_count", "market_saturation",
                "avg_competitor_price", "competitiveness_score"
            ]
            for field in required_fields:
                if field not in analysis or analysis[field] is None:
                    market_complete = False
                    error_details.append(f"{sku}: missing market data {field}")
        validation_checks["market_data_complete"] = market_complete

        # Check 5: Profitability validated
        profitability_valid = True
        for sku, analysis in analysis_results.items():
            margin_ratio = analysis.get("margin_ratio", 0)
            feasibility = analysis.get("feasibility_check", {})
            if not feasibility.get("meets_margin_target", False):
                profitability_valid = False
                error_details.append(f"{sku}: does not meet margin target")
        validation_checks["profitability_validated"] = profitability_valid

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_selection_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "sku_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_sku_data(self, sku: str, sku_info: dict[str, Any]) -> list[str]:
        """Validate a single SKU selection entry.

        Args:
            sku: SKU identifier
            sku_info: SKU info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "market_demand_rank": int,
            "search_volume": (int, float),
            "competitor_count": int,
            "avg_competitor_price": (int, float),
            "target_margin": (int, float),
            "cost": (int, float),
            "market_saturation": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in sku_info:
                errors.append(f"{sku}: missing required field {field}")
                continue

            value = sku_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{sku}: {field} must be {field_type}")

        # Validate ranges
        if "market_saturation" in sku_info:
            sat = sku_info["market_saturation"]
            if not (0 <= sat <= 1):
                errors.append(f"{sku}: market_saturation must be between 0 and 1")

        if "target_margin" in sku_info:
            margin = sku_info["target_margin"]
            if not (0 <= margin <= 1):
                errors.append(f"{sku}: target_margin must be between 0 and 1")

        # Validate positive values
        if "search_volume" in sku_info and sku_info["search_volume"] < 0:
            errors.append(f"{sku}: search_volume must be non-negative")

        return errors

    def _analyze_sku(self, sku: str, sku_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single SKU for selection viability.

        Args:
            sku: SKU identifier
            sku_info: SKU info dict

        Returns:
            Dict with analysis results
        """
        search_volume = sku_info.get("search_volume", 0)
        competitor_count = sku_info.get("competitor_count", 0)
        market_saturation = sku_info.get("market_saturation", 0)
        avg_competitor_price = sku_info.get("avg_competitor_price", 0)
        target_margin = sku_info.get("target_margin", 0)
        cost = sku_info.get("cost", 0)
        market_demand_rank = sku_info.get("market_demand_rank", 999)

        # Calculate demand score (0-100)
        demand_score = min(100, (search_volume / 10000) * 100) if search_volume > 0 else 0

        # Calculate competitiveness score (0-100)
        # Lower competitor count = higher score
        competitiveness_score = max(0, 100 - (competitor_count / 100 * 100))

        # Calculate saturation impact (0-100, inverted)
        # Lower saturation = higher score
        saturation_score = (1 - market_saturation) * 100

        # Calculate market positioning score
        market_positioning_score = (
            demand_score * 0.40 +
            competitiveness_score * 0.30 +
            saturation_score * 0.30
        )

        # Calculate margin feasibility
        margin_ratio = target_margin
        meets_target = margin_ratio >= 0.35  # 35% threshold

        # Composite selection score
        selection_score = market_positioning_score * 0.60 + (margin_ratio * 100) * 0.40

        # Feasibility check
        feasibility = {
            "meets_margin_target": meets_target,
            "has_demand": demand_score > 20,
            "competitive_positioning": "good" if competitiveness_score > 50 else "challenging",
            "market_opportunity": "high" if saturation_score > 50 else "moderate" if saturation_score > 25 else "low",
        }

        return {
            "sku": sku,
            "market_demand_rank": market_demand_rank,
            "search_volume": search_volume,
            "competitor_count": competitor_count,
            "market_saturation": round(market_saturation, 2),
            "avg_competitor_price": avg_competitor_price,
            "demand_score": round(demand_score, 1),
            "competitiveness_score": round(competitiveness_score, 1),
            "saturation_score": round(saturation_score, 1),
            "market_positioning_score": round(market_positioning_score, 1),
            "margin_ratio": round(margin_ratio, 2),
            "selection_score": round(selection_score, 1),
            "feasibility_check": feasibility,
            "recommendation": self._get_recommendation(selection_score, feasibility),
        }

    def _get_recommendation(self, selection_score: float, feasibility: dict[str, Any]) -> str:
        """Get recommendation string based on scores.

        Args:
            selection_score: Overall selection score
            feasibility: Feasibility check dict

        Returns:
            Recommendation string
        """
        if selection_score >= 70 and feasibility.get("meets_margin_target"):
            return "RECOMMEND"
        elif selection_score >= 50 and feasibility.get("meets_margin_target"):
            return "CONDITIONAL"
        else:
            return "HOLD"

    def _generate_recommendations(self) -> dict[str, Any]:
        """Generate SKU selection recommendations.

        Returns:
            Dict with recommended SKUs and sourcing strategy
        """
        # Sort by selection score
        sorted_skus = sorted(
            self.analysis_results.items(),
            key=lambda x: x[1].get("selection_score", 0),
            reverse=True
        )

        recommended = [s[0] for s in sorted_skus if s[1].get("recommendation") == "RECOMMEND"]
        conditional = [s[0] for s in sorted_skus if s[1].get("recommendation") == "CONDITIONAL"]

        recommendations = {
            "recommended_skus": recommended,
            "conditional_skus": conditional,
            "total_recommended": len(recommended),
            "total_conditional": len(conditional),
            "selection_timestamp": "2026-11-23T00:00:00+08:00",
        }

        return recommendations

    def _summarize_analysis(self) -> dict[str, Any]:
        """Summarize key analysis insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_skus": 0}

        scores = [a.get("selection_score", 0) for a in self.analysis_results.values()]
        recommended = sum(1 for a in self.analysis_results.values() if a.get("recommendation") == "RECOMMEND")

        return {
            "total_skus": len(self.analysis_results),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "recommended_count": recommended,
            "highest_score": round(max(scores), 1) if scores else 0,
            "recommendation_rate": round((recommended / len(self.analysis_results)) * 100, 1) if self.analysis_results else 0,
        }
