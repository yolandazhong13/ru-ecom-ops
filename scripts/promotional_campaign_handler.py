#!/usr/bin/env python3
"""Concrete ActionHandler for promotional campaign management on WB_CN.

Implements campaign workflow with:
1. Campaign performance tracking and analysis
2. ROI and effectiveness metrics
3. Audience targeting insights
4. Campaign optimization recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class PromotionalCampaignError(Exception):
    """Raised when promotional campaign operations fail."""
    pass


class PromotionalCampaignActionHandler(ActionHandler):
    """Handles promotional campaign management and optimization for WB_CN.

    Tracks campaign performance, calculates ROI, analyzes audience engagement,
    and recommends optimization strategies for marketing campaigns.
    """

    def __init__(
        self,
        client_id: str,
        campaign_data: dict[str, dict],
    ):
        """Initialize promotional campaign handler.

        Args:
            client_id: WB_CN client identifier
            campaign_data: Dict mapping campaign_id to campaign info:
                {
                    "camp_001": {
                        "campaign_id": "camp_001",
                        "campaign_name": "Speaker Launch Q4",
                        "campaign_type": "flash_sale",
                        "budget_rub": 50000,
                        "spend_rub": 48500,
                        "impressions": 500000,
                        "clicks": 15000,
                        "conversions": 450,
                        "revenue_rub": 125000,
                        "avg_order_value_rub": 2500,
                        "target_audience": "audio_enthusiasts",
                        "campaign_duration_days": 7,
                        "discount_percent": 15,
                        "free_shipping": True
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "promotional_campaign"
        self.platform = "WB_CN"
        self.campaign_data = campaign_data
        self.analysis_results = {}
        self.performance_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute promotional campaign analysis.

        Args:
            content: Approval content with campaign analysis criteria

        Returns:
            Dict with campaign analysis and optimization recommendations
        """
        # Validate campaign data
        validation_errors = []
        for campaign_id, campaign_info in self.campaign_data.items():
            errors = self._validate_campaign_data(campaign_id, campaign_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise PromotionalCampaignError(f"Campaign validation failed: {validation_errors}")

        # Analyze each campaign
        for campaign_id, campaign_info in self.campaign_data.items():
            analysis = self._analyze_campaign_performance(campaign_id, campaign_info)
            self.analysis_results[campaign_id] = analysis

        # Generate performance summary
        self.performance_summary = self._generate_performance_summary()

        return {
            "campaign_data": self.campaign_data,
            "analysis_results": self.analysis_results,
            "performance_summary": self.performance_summary,
            "campaign_count": len(self.campaign_data),
            "campaign_strategy": self._summarize_campaign_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of campaign analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with campaign checks
        """
        validation_checks = {
            "all_campaigns_analyzed": False,
            "performance_metrics_valid": False,
            "roi_calculations_verified": False,
            "engagement_metrics_verified": False,
            "optimization_recommendations_provided": False,
        }

        error_details = []

        # Check 1: All campaigns analyzed
        analysis_results = execution_result.get("analysis_results", {})
        campaign_data = execution_result.get("campaign_data", {})
        if len(analysis_results) == len(campaign_data) and len(campaign_data) > 0:
            validation_checks["all_campaigns_analyzed"] = True

        # Check 2: Performance metrics valid
        metrics_valid = True
        for campaign_id, analysis in analysis_results.items():
            ctr = analysis.get("ctr_percent", 0)
            cvr = analysis.get("cvr_percent", 0)
            if not (0 <= ctr <= 100) or not (0 <= cvr <= 100):
                metrics_valid = False
                error_details.append(f"{campaign_id}: invalid performance metrics")
        validation_checks["performance_metrics_valid"] = metrics_valid

        # Check 3: ROI calculations verified
        roi_valid = True
        for campaign_id, analysis in analysis_results.items():
            roi = analysis.get("roi_percent", None)
            if roi is None or not isinstance(roi, (int, float)):
                roi_valid = False
                error_details.append(f"{campaign_id}: ROI not calculated")
        validation_checks["roi_calculations_verified"] = roi_valid

        # Check 4: Engagement metrics verified
        engagement_valid = True
        for campaign_id, analysis in analysis_results.items():
            engagement = analysis.get("engagement_score", 0)
            if not (0 <= engagement <= 100):
                engagement_valid = False
                error_details.append(f"{campaign_id}: engagement_score {engagement} out of range")
        validation_checks["engagement_metrics_verified"] = engagement_valid

        # Check 5: Optimization recommendations provided
        summary = execution_result.get("campaign_strategy", {})
        if summary and summary.get("optimization_areas"):
            validation_checks["optimization_recommendations_provided"] = True
        else:
            error_details.append("No optimization recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_campaign_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "campaign_count": len(analysis_results),
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
            "campaign_id": str,
            "campaign_name": str,
            "campaign_type": str,
            "budget_rub": (int, float),
            "spend_rub": (int, float),
            "impressions": int,
            "clicks": int,
            "conversions": int,
            "revenue_rub": (int, float),
            "avg_order_value_rub": (int, float),
            "target_audience": str,
            "campaign_duration_days": int,
            "discount_percent": (int, float),
            "free_shipping": bool,
        }

        for field, field_type in required_fields.items():
            if field not in campaign_info:
                errors.append(f"{campaign_id}: missing required field {field}")
                continue

            value = campaign_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{campaign_id}: {field} must be {field_type}")

        # Validate ranges
        if "budget_rub" in campaign_info and campaign_info["budget_rub"] < 0:
            errors.append(f"{campaign_id}: budget_rub must be non-negative")

        if "spend_rub" in campaign_info and campaign_info["spend_rub"] < 0:
            errors.append(f"{campaign_id}: spend_rub must be non-negative")

        # Validate logical consistency
        budget = campaign_info.get("budget_rub", 0)
        spend = campaign_info.get("spend_rub", 0)
        if spend > budget:
            errors.append(f"{campaign_id}: spend_rub cannot exceed budget_rub")

        impressions = campaign_info.get("impressions", 0)
        clicks = campaign_info.get("clicks", 0)
        conversions = campaign_info.get("conversions", 0)

        if clicks > impressions:
            errors.append(f"{campaign_id}: clicks cannot exceed impressions")
        if conversions > clicks:
            errors.append(f"{campaign_id}: conversions cannot exceed clicks")

        # Validate discount
        if "discount_percent" in campaign_info:
            discount = campaign_info["discount_percent"]
            if not (0 <= discount <= 100):
                errors.append(f"{campaign_id}: discount_percent must be 0-100")

        return errors

    def _analyze_campaign_performance(self, campaign_id: str, campaign_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze campaign performance.

        Args:
            campaign_id: Campaign identifier
            campaign_info: Campaign info dict

        Returns:
            Dict with campaign analysis
        """
        budget = campaign_info.get("budget_rub", 0)
        spend = campaign_info.get("spend_rub", 0)
        impressions = campaign_info.get("impressions", 1)
        clicks = campaign_info.get("clicks", 0)
        conversions = campaign_info.get("conversions", 0)
        revenue = campaign_info.get("revenue_rub", 0)
        avg_order_value = campaign_info.get("avg_order_value_rub", 0)
        campaign_type = campaign_info.get("campaign_type", "general")
        discount = campaign_info.get("discount_percent", 0)
        free_shipping = campaign_info.get("free_shipping", False)
        duration_days = campaign_info.get("campaign_duration_days", 1)

        # Calculate engagement metrics
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cvr = (conversions / clicks * 100) if clicks > 0 else 0
        overall_conversion = (conversions / impressions * 100) if impressions > 0 else 0

        # Calculate ROI
        roi = ((revenue - spend) / spend * 100) if spend > 0 else 0
        roas = (revenue / spend) if spend > 0 else 0

        # Calculate cost per acquisition
        cpa = (spend / conversions) if conversions > 0 else 0

        # Calculate cost efficiency metrics
        cost_per_impression = (spend / impressions) if impressions > 0 else 0
        cost_per_click = (spend / clicks) if clicks > 0 else 0

        # Calculate engagement score (0-100)
        # Optimal CTR: 2-5%, CVR: 2-10%
        ctr_score = min(100, (ctr / 5) * 100) if ctr > 0 else 0
        cvr_score = min(100, (cvr / 10) * 100) if cvr > 0 else 0
        roi_score = min(100, max(0, roi / 50 * 100))  # 50% ROI = max score
        engagement_score = ctr_score * 0.3 + cvr_score * 0.4 + roi_score * 0.3

        # Campaign performance rating
        if engagement_score >= 80:
            performance_rating = "EXCELLENT"
        elif engagement_score >= 60:
            performance_rating = "GOOD"
        elif engagement_score >= 40:
            performance_rating = "FAIR"
        else:
            performance_rating = "NEEDS_IMPROVEMENT"

        # Determine budget efficiency
        budget_utilization = (spend / budget * 100) if budget > 0 else 0
        budget_efficiency = "OPTIMAL" if 95 <= budget_utilization <= 105 else "UNDERSPEND" if budget_utilization < 90 else "OVERSPEND"

        # Calculate daily metrics
        daily_spend = spend / duration_days if duration_days > 0 else 0
        daily_conversions = conversions / duration_days if duration_days > 0 else 0
        daily_revenue = revenue / duration_days if duration_days > 0 else 0

        # Campaign type insights
        type_recommendation = self._get_type_recommendation(campaign_type, engagement_score, roi, conversions)

        # Optimization suggestions
        optimization_suggestions = self._suggest_optimizations(
            ctr, cvr, roi, engagement_score, budget_utilization, discount, free_shipping
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign_info.get("campaign_name", campaign_id),
            "campaign_type": campaign_type,
            "budget_rub": round(budget, 2),
            "spend_rub": round(spend, 2),
            "budget_utilization_percent": round(budget_utilization, 1),
            "budget_efficiency": budget_efficiency,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr_percent": round(ctr, 2),
            "cvr_percent": round(cvr, 2),
            "overall_conversion_percent": round(overall_conversion, 2),
            "revenue_rub": round(revenue, 2),
            "avg_order_value_rub": round(avg_order_value, 2),
            "roi_percent": round(roi, 1),
            "roas": round(roas, 2),
            "cpa_rub": round(cpa, 2),
            "cost_per_impression_rub": round(cost_per_impression, 4),
            "cost_per_click_rub": round(cost_per_click, 2),
            "daily_spend_rub": round(daily_spend, 2),
            "daily_conversions": round(daily_conversions, 1),
            "daily_revenue_rub": round(daily_revenue, 2),
            "ctr_score": round(ctr_score, 1),
            "cvr_score": round(cvr_score, 1),
            "roi_score": round(roi_score, 1),
            "engagement_score": round(engagement_score, 1),
            "performance_rating": performance_rating,
            "discount_percent": discount,
            "free_shipping": free_shipping,
            "campaign_duration_days": duration_days,
            "type_recommendation": type_recommendation,
            "optimization_suggestions": optimization_suggestions,
        }

    def _get_type_recommendation(self, campaign_type: str, engagement_score: float,
                               roi: float, conversions: int) -> str:
        """Get recommendation for campaign type based on performance.

        Args:
            campaign_type: Type of campaign
            engagement_score: Overall engagement score
            roi: Return on ad spend percentage
            conversions: Number of conversions

        Returns:
            Recommendation string
        """
        if engagement_score >= 70 and roi > 0:
            return f"EXPAND_{campaign_type.upper()}_BUDGET"
        elif engagement_score >= 50 or (roi > 0 and conversions > 10):
            return f"CONTINUE_{campaign_type.upper()}_WITH_OPTIMIZATION"
        elif roi < 0 or engagement_score < 30:
            return f"REVIEW_{campaign_type.upper()}_STRATEGY"
        else:
            return "MAINTAIN_CURRENT_APPROACH"

    def _suggest_optimizations(self, ctr: float, cvr: float, roi: float,
                              engagement: float, budget_util: float,
                              discount: float, free_shipping: bool) -> list[str]:
        """Suggest campaign optimizations.

        Args:
            ctr: Click-through rate
            cvr: Conversion rate
            roi: Return on investment percentage
            engagement: Engagement score
            budget_util: Budget utilization percentage
            discount: Discount percentage
            free_shipping: Free shipping offered

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # CTR optimization
        if ctr < 1:
            suggestions.append("Improve ad copy and creative to increase CTR")
            suggestions.append("Test different targeting audiences")
        elif ctr > 5:
            suggestions.append("Consider increasing bid/budget - strong CTR indicates good ad quality")

        # CVR optimization
        if cvr < 1:
            suggestions.append("Optimize landing page and checkout flow")
            suggestions.append("Review product-market fit for this audience")
        elif cvr > 10:
            suggestions.append("Scale budget - conversion performance is strong")

        # ROI optimization
        if roi < 0:
            suggestions.append("Consider pausing underperforming ad sets")
            suggestions.append("Review pricing strategy - may need adjustment")
        elif roi > 50:
            suggestions.append("Scale budget and expand to similar audiences")

        # Budget optimization
        if budget_util < 90:
            suggestions.append("Increase daily budget to utilize allocation")
        elif budget_util > 110:
            suggestions.append("Campaign exceeding budget - increase allocation or cap daily spend")

        # Discount/shipping optimization
        if discount > 0 and roi < 10:
            suggestions.append("Consider reducing discount to improve margins")
        if not free_shipping and engagement > 70:
            suggestions.append("Test free shipping promotion to boost conversions")

        # Overall health
        if engagement < 50:
            suggestions.append("Campaign underperforming - consider full strategy review")

        if not suggestions:
            suggestions.append("Campaign performing well - monitor and maintain")

        return suggestions

    def _generate_performance_summary(self) -> dict[str, Any]:
        """Generate campaign performance summary.

        Returns:
            Dict with performance summary
        """
        excellent_campaigns = []
        good_campaigns = []
        fair_campaigns = []
        poor_campaigns = []

        total_budget = 0
        total_spend = 0
        total_revenue = 0
        total_conversions = 0

        for campaign_id, analysis in self.analysis_results.items():
            rating = analysis.get("performance_rating", "UNKNOWN")
            if rating == "EXCELLENT":
                excellent_campaigns.append(campaign_id)
            elif rating == "GOOD":
                good_campaigns.append(campaign_id)
            elif rating == "FAIR":
                fair_campaigns.append(campaign_id)
            else:
                poor_campaigns.append(campaign_id)

            total_budget += analysis.get("budget_rub", 0)
            total_spend += analysis.get("spend_rub", 0)
            total_revenue += analysis.get("revenue_rub", 0)
            total_conversions += analysis.get("conversions", 0)

        portfolio_roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0
        portfolio_roas = (total_revenue / total_spend) if total_spend > 0 else 0

        return {
            "excellent_campaigns": excellent_campaigns,
            "good_campaigns": good_campaigns,
            "fair_campaigns": fair_campaigns,
            "poor_campaigns": poor_campaigns,
            "performance_distribution": {
                "EXCELLENT": len(excellent_campaigns),
                "GOOD": len(good_campaigns),
                "FAIR": len(fair_campaigns),
                "NEEDS_IMPROVEMENT": len(poor_campaigns),
            },
            "total_campaigns": len(self.analysis_results),
            "total_budget_rub": round(total_budget, 2),
            "total_spend_rub": round(total_spend, 2),
            "total_revenue_rub": round(total_revenue, 2),
            "total_conversions": int(total_conversions),
            "portfolio_roi_percent": round(portfolio_roi, 1),
            "portfolio_roas": round(portfolio_roas, 2),
            "analysis_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_campaign_strategy(self) -> dict[str, Any]:
        """Summarize campaign strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_campaigns": 0}

        engagement_scores = [a.get("engagement_score", 0) for a in self.analysis_results.values()]
        roi_values = [a.get("roi_percent", 0) for a in self.analysis_results.values()]
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
        avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0

        # Identify campaign types
        types = {}
        for analysis in self.analysis_results.values():
            ctype = analysis.get("campaign_type", "unknown")
            types[ctype] = types.get(ctype, 0) + 1

        # Optimization areas
        optimization_areas = []
        if avg_engagement < 50:
            optimization_areas.append("Overall engagement below target - review creative and targeting")
        if avg_roi < 0:
            optimization_areas.append("Portfolio ROI negative - audit all campaigns for efficiency")
        if len(self.performance_summary.get("poor_campaigns", [])) > len(self.performance_summary.get("excellent_campaigns", [])):
            optimization_areas.append("More underperforming than excellent campaigns - shift budget to winners")

        if not optimization_areas:
            optimization_areas.append("Portfolio performing well - continue current strategy")

        return {
            "total_campaigns": len(self.analysis_results),
            "avg_engagement_score": round(avg_engagement, 1),
            "portfolio_avg_roi_percent": round(avg_roi, 1),
            "highest_roi_campaign": max(self.analysis_results.items(), key=lambda x: x[1].get("roi_percent", 0))[0] if self.analysis_results else "N/A",
            "lowest_roi_campaign": min(self.analysis_results.items(), key=lambda x: x[1].get("roi_percent", 0))[0] if self.analysis_results else "N/A",
            "campaign_types": types,
            "portfolio_health": "STRONG" if avg_engagement > 60 else "GOOD" if avg_engagement > 45 else "NEEDS_REVIEW",
            "optimization_areas": optimization_areas,
            "budget_allocation_insight": f"{len(self.performance_summary.get('excellent_campaigns', []))} excellent campaigns should receive priority budget allocation",
        }
