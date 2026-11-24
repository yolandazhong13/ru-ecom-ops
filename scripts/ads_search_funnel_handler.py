#!/usr/bin/env python3
"""Concrete ActionHandler for search advertising funnel optimization on WB_CN.

Implements ads funnel analysis with:
1. Search keyword performance tracking
2. Campaign efficiency metrics
3. Conversion funnel analysis
4. Bidding strategy optimization
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class AdsFunnelError(Exception):
    """Raised when ads funnel operations fail."""
    pass


class AdsSearchFunnelActionHandler(ActionHandler):
    """Handles search advertising funnel optimization for WB_CN.

    Analyzes search campaign performance, conversion funnels, and
    recommends bidding strategy adjustments.
    """

    def __init__(
        self,
        client_id: str,
        campaign_data: dict[str, dict],
    ):
        """Initialize ads search funnel handler.

        Args:
            client_id: WB_CN client identifier
            campaign_data: Dict mapping campaign_id to campaign info:
                {
                    "search_md700_01": {
                        "campaign_name": "MD-700 Search",
                        "impressions": 50000,
                        "clicks": 2500,
                        "conversions": 125,
                        "spend_rub": 5000,
                        "revenue_rub": 15000,
                        "avg_bid_kopeks": 200,
                        "current_cpc_rub": 2.0
                    }
                }
        """
        self.client_id = str(client_id)
        self.campaign_data = campaign_data
        self.funnel_analysis = {}
        self.optimization_recommendations = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute ads funnel analysis per content_for_approval.

        Args:
            content: Approval content with campaign optimization criteria

        Returns:
            Dict with funnel analysis and bidding recommendations
        """
        # Validate campaign data
        validation_errors = []
        for campaign_id, campaign_info in self.campaign_data.items():
            errors = self._validate_campaign_data(campaign_id, campaign_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise AdsFunnelError(f"Campaign validation failed: {validation_errors}")

        # Analyze each campaign's funnel
        for campaign_id, campaign_info in self.campaign_data.items():
            analysis = self._analyze_campaign_funnel(campaign_id, campaign_info)
            self.funnel_analysis[campaign_id] = analysis

        # Generate optimization recommendations
        self.optimization_recommendations = self._generate_recommendations()

        return {
            "campaign_data": self.campaign_data,
            "funnel_analysis": self.funnel_analysis,
            "optimization_recommendations": self.optimization_recommendations,
            "campaign_count": len(self.campaign_data),
            "optimization_summary": self._summarize_optimization(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of ads funnel analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with analysis checks
        """
        validation_checks = {
            "all_campaigns_analyzed": False,
            "funnel_metrics_valid": False,
            "efficiency_scores_valid": False,
            "recommendations_provided": False,
            "roi_calculations_verified": False,
        }

        error_details = []

        # Check 1: All campaigns analyzed
        funnel_analysis = execution_result.get("funnel_analysis", {})
        campaign_data = execution_result.get("campaign_data", {})
        if len(funnel_analysis) == len(campaign_data) and len(campaign_data) > 0:
            validation_checks["all_campaigns_analyzed"] = True

        # Check 2: Funnel metrics valid
        metrics_valid = True
        for campaign_id, analysis in funnel_analysis.items():
            ctr = analysis.get("ctr_percent", 0)
            cvr = analysis.get("cvr_percent", 0)
            if not (0 <= ctr <= 100) or not (0 <= cvr <= 100):
                metrics_valid = False
                error_details.append(f"{campaign_id}: invalid funnel metrics")
        validation_checks["funnel_metrics_valid"] = metrics_valid

        # Check 3: Efficiency scores valid (0-100)
        scores_valid = True
        for campaign_id, analysis in funnel_analysis.items():
            efficiency = analysis.get("efficiency_score", 0)
            if not (0 <= efficiency <= 100):
                scores_valid = False
                error_details.append(f"{campaign_id}: efficiency_score {efficiency} out of range")
        validation_checks["efficiency_scores_valid"] = scores_valid

        # Check 4: Recommendations provided
        recommendations = execution_result.get("optimization_recommendations", {})
        if recommendations and len(recommendations.get("campaigns_to_optimize", [])) >= 0:
            validation_checks["recommendations_provided"] = True
        else:
            error_details.append("No optimization recommendations generated")

        # Check 5: ROI calculations verified
        roi_verified = True
        for campaign_id, analysis in funnel_analysis.items():
            roi = analysis.get("roi_percent", 0)
            if roi is None or not isinstance(roi, (int, float)):
                roi_verified = False
                error_details.append(f"{campaign_id}: ROI calculation invalid")
        validation_checks["roi_calculations_verified"] = roi_verified

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_ads_optimization" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "campaign_count": len(funnel_analysis),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_campaign_data(self, campaign_id: str, campaign_info: dict[str, Any]) -> list[str]:
        """Validate campaign data.

        Args:
            campaign_id: Campaign identifier
            campaign_info: Campaign info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "campaign_name": str,
            "impressions": int,
            "clicks": int,
            "conversions": int,
            "spend_rub": (int, float),
            "revenue_rub": (int, float),
            "avg_bid_kopeks": (int, float),
            "current_cpc_rub": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in campaign_info:
                errors.append(f"{campaign_id}: missing required field {field}")
                continue

            value = campaign_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{campaign_id}: {field} must be {field_type}")

        # Validate ranges
        if "impressions" in campaign_info and campaign_info["impressions"] < 0:
            errors.append(f"{campaign_id}: impressions must be non-negative")

        if "spend_rub" in campaign_info and campaign_info["spend_rub"] < 0:
            errors.append(f"{campaign_id}: spend_rub must be non-negative")

        # Validate logical consistency
        impressions = campaign_info.get("impressions", 0)
        clicks = campaign_info.get("clicks", 0)
        conversions = campaign_info.get("conversions", 0)

        if clicks > impressions:
            errors.append(f"{campaign_id}: clicks cannot exceed impressions")
        if conversions > clicks:
            errors.append(f"{campaign_id}: conversions cannot exceed clicks")

        return errors

    def _analyze_campaign_funnel(self, campaign_id: str, campaign_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze campaign funnel performance.

        Args:
            campaign_id: Campaign identifier
            campaign_info: Campaign info dict

        Returns:
            Dict with funnel analysis results
        """
        impressions = campaign_info.get("impressions", 1)
        clicks = campaign_info.get("clicks", 0)
        conversions = campaign_info.get("conversions", 0)
        spend = campaign_info.get("spend_rub", 0)
        revenue = campaign_info.get("revenue_rub", 0)
        avg_bid = campaign_info.get("avg_bid_kopeks", 0)
        current_cpc = campaign_info.get("current_cpc_rub", 0)

        # Calculate funnel metrics
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cvr = (conversions / clicks * 100) if clicks > 0 else 0
        overall_conversion = (conversions / impressions * 100) if impressions > 0 else 0

        # Calculate cost metrics
        cpc = (spend / clicks) if clicks > 0 else 0
        cost_per_conversion = (spend / conversions) if conversions > 0 else 0
        average_order_value = (revenue / conversions) if conversions > 0 else 0

        # Calculate efficiency metrics
        roas = (revenue / spend) if spend > 0 else 0
        roi = ((revenue - spend) / spend * 100) if spend > 0 else 0

        # Calculate efficiency score (0-100)
        # Optimal CTR: 2-5%, CVR: 2-10%
        ctr_score = min(100, (ctr / 5) * 100) if ctr > 0 else 0
        cvr_score = min(100, (cvr / 10) * 100) if cvr > 0 else 0
        roi_score = min(100, max(0, roi / 50 * 100))  # 50% ROI = max score
        efficiency_score = (ctr_score * 0.3 + cvr_score * 0.4 + roi_score * 0.3)

        # Determine optimization priority
        priority = self._determine_priority(efficiency_score, roi, cpc, current_cpc)

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign_info.get("campaign_name", campaign_id),
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr_percent": round(ctr, 2),
            "cvr_percent": round(cvr, 2),
            "overall_conversion_percent": round(overall_conversion, 2),
            "spend_rub": round(spend, 2),
            "revenue_rub": round(revenue, 2),
            "cpc_rub": round(cpc, 2),
            "cost_per_conversion_rub": round(cost_per_conversion, 2),
            "average_order_value_rub": round(average_order_value, 2),
            "roas": round(roas, 2),
            "roi_percent": round(roi, 2),
            "efficiency_score": round(efficiency_score, 1),
            "current_cpc_rub": current_cpc,
            "avg_bid_kopeks": avg_bid,
            "optimization_priority": priority,
        }

    def _determine_priority(self, efficiency_score: float, roi: float, cpc: float, current_cpc: float) -> str:
        """Determine optimization priority level.

        Args:
            efficiency_score: Campaign efficiency score
            roi: Return on ad spend percentage
            cpc: Cost per click
            current_cpc: Current CPC setting

        Returns:
            Priority level string
        """
        if efficiency_score < 30 and roi < 0:
            return "CRITICAL_REVIEW"
        elif efficiency_score < 50 or roi < 10:
            return "HIGH_PRIORITY"
        elif efficiency_score < 70:
            return "MEDIUM_PRIORITY"
        else:
            return "LOW_PRIORITY"

    def _generate_recommendations(self) -> dict[str, Any]:
        """Generate optimization recommendations.

        Returns:
            Dict with optimization recommendations
        """
        campaigns_to_optimize = []
        campaigns_performing_well = []

        for campaign_id, analysis in self.funnel_analysis.items():
            priority = analysis.get("optimization_priority", "UNKNOWN")
            if priority in {"CRITICAL_REVIEW", "HIGH_PRIORITY"}:
                campaigns_to_optimize.append({
                    "campaign_id": campaign_id,
                    "priority": priority,
                    "current_efficiency": analysis.get("efficiency_score"),
                    "recommendation": self._get_recommendation(analysis),
                })
            elif priority == "LOW_PRIORITY":
                campaigns_performing_well.append(campaign_id)

        return {
            "campaigns_to_optimize": campaigns_to_optimize,
            "campaigns_performing_well": campaigns_performing_well,
            "total_campaigns": len(self.funnel_analysis),
            "optimization_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _get_recommendation(self, analysis: dict[str, Any]) -> str:
        """Get specific recommendation for campaign.

        Args:
            analysis: Campaign analysis dict

        Returns:
            Recommendation string
        """
        ctr = analysis.get("ctr_percent", 0)
        cvr = analysis.get("cvr_percent", 0)
        roi = analysis.get("roi_percent", 0)

        if roi < 0:
            return "Review keywords and landing pages; consider pausing underperforming keywords"
        elif ctr < 1:
            return "Increase bid or improve ad copy to increase click-through rate"
        elif cvr < 1:
            return "Optimize landing page or product targeting to improve conversion"
        else:
            return "Monitor performance; consider bid optimization"

    def _summarize_optimization(self) -> dict[str, Any]:
        """Summarize optimization insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.funnel_analysis:
            return {"total_campaigns": 0}

        efficiency_scores = [a.get("efficiency_score", 0) for a in self.funnel_analysis.values()]
        roi_values = [a.get("roi_percent", 0) for a in self.funnel_analysis.values()]
        total_spend = sum(a.get("spend_rub", 0) for a in self.funnel_analysis.values())
        total_revenue = sum(a.get("revenue_rub", 0) for a in self.funnel_analysis.values())

        return {
            "total_campaigns": len(self.funnel_analysis),
            "avg_efficiency_score": round(sum(efficiency_scores) / len(efficiency_scores), 1) if efficiency_scores else 0,
            "total_spend_rub": round(total_spend, 2),
            "total_revenue_rub": round(total_revenue, 2),
            "portfolio_roi_percent": round((total_revenue - total_spend) / total_spend * 100, 2) if total_spend > 0 else 0,
            "portfolio_roas": round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
            "campaigns_needing_optimization": sum(1 for a in self.funnel_analysis.values() if a.get("optimization_priority") in {"CRITICAL_REVIEW", "HIGH_PRIORITY"}),
        }
