#!/usr/bin/env python3
"""Concrete ActionHandler for competitive analysis and market intelligence on WB_CN.

Implements competitive analysis workflow with:
1. Competitor tracking and benchmarking
2. Market share analysis
3. Competitive positioning assessment
4. Strategic recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class CompetitorAnalysisError(Exception):
    """Raised when competitor analysis operations fail."""
    pass


class CompetitorAnalysisActionHandler(ActionHandler):
    """Handles competitor analysis and market intelligence for WB_CN.

    Tracks competitor performance, analyzes competitive positioning,
    monitors market share, and provides strategic competitive insights.
    """

    def __init__(
        self,
        client_id: str,
        competitor_data: dict[str, dict],
    ):
        """Initialize competitor analysis handler.

        Args:
            client_id: WB_CN client identifier
            competitor_data: Dict mapping competitor_id to competitor info:
                {
                    "comp_001": {
                        "competitor_id": "comp_001",
                        "competitor_name": "AudioTech Pro",
                        "product_count": 45,
                        "avg_product_price_rub": 2800,
                        "avg_rating": 4.2,
                        "review_count": 1250,
                        "monthly_sales_estimate": 500,
                        "market_share_percent": 12.5,
                        "price_competitiveness_score": 75,
                        "quality_perception_score": 82,
                        "shipping_speed_days": 3,
                        "return_policy_days": 30
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "competitor_analysis"
        self.platform = "WB_CN"
        self.competitor_data = competitor_data
        self.analysis_results = {}
        self.competitive_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute competitive analysis.

        Args:
            content: Approval content with competitive analysis criteria

        Returns:
            Dict with competitor analysis and strategic insights
        """
        # Validate competitor data
        validation_errors = []
        for competitor_id, competitor_info in self.competitor_data.items():
            errors = self._validate_competitor_data(competitor_id, competitor_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise CompetitorAnalysisError(f"Competitor validation failed: {validation_errors}")

        # Analyze each competitor
        for competitor_id, competitor_info in self.competitor_data.items():
            analysis = self._analyze_competitor(competitor_id, competitor_info)
            self.analysis_results[competitor_id] = analysis

        # Generate competitive summary
        self.competitive_summary = self._generate_competitive_summary()

        return {
            "competitor_data": self.competitor_data,
            "analysis_results": self.analysis_results,
            "competitive_summary": self.competitive_summary,
            "competitor_count": len(self.competitor_data),
            "competitive_strategy": self._summarize_competitive_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of competitor analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with competitive checks
        """
        validation_checks = {
            "all_competitors_analyzed": False,
            "competitive_scores_valid": False,
            "market_share_calculated": False,
            "threat_levels_assigned": False,
            "strategic_recommendations_provided": False,
        }

        error_details = []

        # Check 1: All competitors analyzed
        analysis_results = execution_result.get("analysis_results", {})
        competitor_data = execution_result.get("competitor_data", {})
        if len(analysis_results) == len(competitor_data) and len(competitor_data) > 0:
            validation_checks["all_competitors_analyzed"] = True

        # Check 2: Competitive scores valid (0-100)
        scores_valid = True
        for competitor_id, analysis in analysis_results.items():
            score = analysis.get("competitive_strength_score", 0)
            if not (0 <= score <= 100):
                scores_valid = False
                error_details.append(f"{competitor_id}: competitive_strength_score {score} out of range")
        validation_checks["competitive_scores_valid"] = scores_valid

        # Check 3: Market share calculated
        market_valid = True
        for competitor_id, analysis in analysis_results.items():
            share = analysis.get("market_share_percent", None)
            if share is None or not isinstance(share, (int, float)):
                market_valid = False
                error_details.append(f"{competitor_id}: market_share_percent not calculated")
        validation_checks["market_share_calculated"] = market_valid

        # Check 4: Threat levels assigned
        threat_valid = True
        for competitor_id, analysis in analysis_results.items():
            threat = analysis.get("threat_level", None)
            if threat not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                threat_valid = False
                error_details.append(f"{competitor_id}: invalid threat_level {threat}")
        validation_checks["threat_levels_assigned"] = threat_valid

        # Check 5: Strategic recommendations provided
        strategy = execution_result.get("competitive_strategy", {})
        if strategy and strategy.get("strategic_priorities"):
            validation_checks["strategic_recommendations_provided"] = True
        else:
            error_details.append("No strategic recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_competitor_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "competitor_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_competitor_data(self, competitor_id: str, competitor_info: dict[str, Any]) -> list[str]:
        """Validate competitor data.

        Args:
            competitor_id: Competitor identifier
            competitor_info: Competitor info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "competitor_id": str,
            "competitor_name": str,
            "product_count": int,
            "avg_product_price_rub": (int, float),
            "avg_rating": (int, float),
            "review_count": int,
            "monthly_sales_estimate": int,
            "market_share_percent": (int, float),
            "price_competitiveness_score": (int, float),
            "quality_perception_score": (int, float),
            "shipping_speed_days": (int, float),
            "return_policy_days": int,
        }

        for field, field_type in required_fields.items():
            if field not in competitor_info:
                errors.append(f"{competitor_id}: missing required field {field}")
                continue

            value = competitor_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{competitor_id}: {field} must be {field_type}")

        # Validate ranges
        if "product_count" in competitor_info and competitor_info["product_count"] < 0:
            errors.append(f"{competitor_id}: product_count must be non-negative")

        if "avg_rating" in competitor_info:
            rating = competitor_info["avg_rating"]
            if not (0 <= rating <= 5):
                errors.append(f"{competitor_id}: avg_rating must be 0-5")

        if "market_share_percent" in competitor_info:
            share = competitor_info["market_share_percent"]
            if not (0 <= share <= 100):
                errors.append(f"{competitor_id}: market_share_percent must be 0-100")

        if "price_competitiveness_score" in competitor_info:
            score = competitor_info["price_competitiveness_score"]
            if not (0 <= score <= 100):
                errors.append(f"{competitor_id}: price_competitiveness_score must be 0-100")

        if "quality_perception_score" in competitor_info:
            score = competitor_info["quality_perception_score"]
            if not (0 <= score <= 100):
                errors.append(f"{competitor_id}: quality_perception_score must be 0-100")

        return errors

    def _analyze_competitor(self, competitor_id: str, competitor_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single competitor.

        Args:
            competitor_id: Competitor identifier
            competitor_info: Competitor info dict

        Returns:
            Dict with competitor analysis
        """
        product_count = competitor_info.get("product_count", 0)
        avg_price = competitor_info.get("avg_product_price_rub", 0)
        avg_rating = competitor_info.get("avg_rating", 0)
        review_count = competitor_info.get("review_count", 0)
        monthly_sales = competitor_info.get("monthly_sales_estimate", 0)
        market_share = competitor_info.get("market_share_percent", 0)
        price_score = competitor_info.get("price_competitiveness_score", 0)
        quality_score = competitor_info.get("quality_perception_score", 0)
        shipping_days = competitor_info.get("shipping_speed_days", 0)
        return_days = competitor_info.get("return_policy_days", 0)

        # Calculate market presence score
        # Factors: product count, rating, review count
        product_score = min(100, (product_count / 100) * 100)  # 100+ products = max
        review_score = min(100, (review_count / 1000) * 100)  # 1000+ reviews = max
        rating_score = (avg_rating / 5) * 100  # 5.0 rating = 100

        market_presence_score = product_score * 0.4 + review_score * 0.3 + rating_score * 0.3

        # Calculate competitive strength score
        # Factors: pricing, quality perception, shipping speed, return policy, market presence
        shipping_score = min(100, 100 - (shipping_days * 10))  # 1-day = 90, 2-day = 80, etc.
        return_score = min(100, (return_days / 30) * 100)  # 30+ days = max

        competitive_strength = (
            price_score * 0.25 +
            quality_score * 0.30 +
            shipping_score * 0.15 +
            return_score * 0.10 +
            market_presence_score * 0.20
        )

        # Determine threat level
        if market_share > 10 and competitive_strength > 75:
            threat_level = "CRITICAL"
            threat_rank = 4
        elif market_share > 5 or competitive_strength > 70:
            threat_level = "HIGH"
            threat_rank = 3
        elif market_share > 2 or competitive_strength > 55:
            threat_level = "MEDIUM"
            threat_rank = 2
        else:
            threat_level = "LOW"
            threat_rank = 1

        # Identify competitive advantages
        strengths = []
        weaknesses = []

        if price_score > 80:
            strengths.append("Strong price positioning")
        elif price_score < 50:
            weaknesses.append("Price not competitive")

        if quality_score > 85:
            strengths.append("High quality perception")
        elif quality_score < 70:
            weaknesses.append("Quality perception concerns")

        if shipping_days <= 2:
            strengths.append("Fast shipping capability")
        elif shipping_days > 7:
            weaknesses.append("Slow shipping speed")

        if return_days >= 30:
            strengths.append("Customer-friendly return policy")
        elif return_days < 14:
            weaknesses.append("Restrictive return policy")

        if product_count > 50:
            strengths.append("Wide product selection")
        elif product_count < 20:
            weaknesses.append("Limited product catalog")

        # Competitive recommendations
        recommendations = self._recommend_competitive_actions(threat_level, strengths, weaknesses)

        # Calculate market intensity
        market_intensity = (market_share * 0.6 + (competitive_strength / 100) * 40)

        return {
            "competitor_id": competitor_id,
            "competitor_name": competitor_info.get("competitor_name", competitor_id),
            "product_count": product_count,
            "avg_product_price_rub": round(avg_price, 2),
            "avg_rating": round(avg_rating, 2),
            "review_count": review_count,
            "monthly_sales_estimate": monthly_sales,
            "market_share_percent": round(market_share, 2),
            "price_competitiveness_score": round(price_score, 1),
            "quality_perception_score": round(quality_score, 1),
            "shipping_speed_days": round(shipping_days, 1),
            "return_policy_days": return_days,
            "market_presence_score": round(market_presence_score, 1),
            "shipping_score": round(shipping_score, 1),
            "return_policy_score": round(return_score, 1),
            "competitive_strength_score": round(competitive_strength, 1),
            "market_intensity_score": round(market_intensity, 1),
            "threat_level": threat_level,
            "threat_rank": threat_rank,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "competitive_actions": recommendations,
        }

    def _recommend_competitive_actions(self, threat_level: str, strengths: list[str],
                                      weaknesses: list[str]) -> list[str]:
        """Recommend competitive response actions.

        Args:
            threat_level: Competitor threat level
            strengths: Competitor strengths
            weaknesses: Competitor weaknesses

        Returns:
            List of recommendations
        """
        recommendations = []

        if threat_level == "CRITICAL":
            recommendations.append("PRIORITY: Close identified competitive gaps immediately")
            recommendations.append("Conduct detailed competitive positioning analysis")
            recommendations.append("Develop counter-strategy in pricing/quality/service")

        elif threat_level == "HIGH":
            recommendations.append("Monitor competitor closely - quarterly review")
            recommendations.append("Identify and strengthen your competitive differentiation")

        elif threat_level == "MEDIUM":
            recommendations.append("Track market moves - semi-annual review")

        else:
            recommendations.append("Monitor as emerging competitor")

        # Recommendations based on competitor strengths/weaknesses
        if "Strong price positioning" in strengths:
            recommendations.append("Defend through value-add services, not price war")

        if "High quality perception" in strengths:
            recommendations.append("Invest in quality communication/certification")

        if "Wide product selection" in strengths:
            recommendations.append("Focus on niche depth vs. breadth competition")

        if "Price not competitive" in weaknesses:
            recommendations.append("Capitalize on price advantage in messaging")

        if "Quality perception concerns" in weaknesses:
            recommendations.append("Highlight your quality advantages in campaigns")

        if "Restrictive return policy" in weaknesses:
            recommendations.append("Promote your customer-friendly policies")

        return recommendations

    def _generate_competitive_summary(self) -> dict[str, Any]:
        """Generate competitive landscape summary.

        Returns:
            Dict with competitive summary
        """
        critical_threats = []
        high_threats = []
        medium_threats = []
        low_threats = []

        total_market_share = 0
        avg_competitive_strength = 0
        total_product_count = 0

        for competitor_id, analysis in self.analysis_results.items():
            threat = analysis.get("threat_level", "UNKNOWN")
            if threat == "CRITICAL":
                critical_threats.append(competitor_id)
            elif threat == "HIGH":
                high_threats.append(competitor_id)
            elif threat == "MEDIUM":
                medium_threats.append(competitor_id)
            else:
                low_threats.append(competitor_id)

            total_market_share += analysis.get("market_share_percent", 0)
            avg_competitive_strength += analysis.get("competitive_strength_score", 0)
            total_product_count += analysis.get("product_count", 0)

        competitor_count = len(self.analysis_results)
        avg_competitive_strength = avg_competitive_strength / competitor_count if competitor_count > 0 else 0

        # Identify top threat
        top_threat = max(self.analysis_results.items(),
                        key=lambda x: x[1].get("threat_rank", 0))[0] if self.analysis_results else "NONE"

        # Average competitor metrics
        avg_product_count = total_product_count / competitor_count if competitor_count > 0 else 0
        avg_market_share = total_market_share / competitor_count if competitor_count > 0 else 0

        return {
            "critical_threats": critical_threats,
            "high_threats": high_threats,
            "medium_threats": medium_threats,
            "low_threats": low_threats,
            "threat_distribution": {
                "CRITICAL": len(critical_threats),
                "HIGH": len(high_threats),
                "MEDIUM": len(medium_threats),
                "LOW": len(low_threats),
            },
            "total_competitors_tracked": competitor_count,
            "top_threat_competitor": top_threat,
            "collective_market_share_percent": round(total_market_share, 2),
            "avg_competitor_strength_score": round(avg_competitive_strength, 1),
            "avg_product_count_per_competitor": round(avg_product_count, 0),
            "avg_market_share_per_competitor": round(avg_market_share, 2),
            "competitive_landscape_health": "FRAGMENTED" if competitor_count > 10 else "CONSOLIDATED" if len(critical_threats) > 0 else "BALANCED",
            "analysis_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_competitive_strategy(self) -> dict[str, Any]:
        """Summarize competitive strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_competitors": 0}

        threat_ranks = [a.get("threat_rank", 0) for a in self.analysis_results.values()]
        strength_scores = [a.get("competitive_strength_score", 0) for a in self.analysis_results.values()]

        # Identify strategic opportunities
        strategic_opportunities = []

        critical_count = len(self.competitive_summary.get("critical_threats", []))
        if critical_count > 0:
            strategic_opportunities.append(f"Address {critical_count} critical threat(s) through differentiation")

        high_count = len(self.competitive_summary.get("high_threats", []))
        if high_count > 0:
            strategic_opportunities.append(f"Develop counter-strategies for {high_count} high-threat competitors")

        collective_share = self.competitive_summary.get("collective_market_share_percent", 0)
        if collective_share < 50:
            strategic_opportunities.append("Fragmented market - opportunity for consolidation/growth")

        avg_strength = sum(strength_scores) / len(strength_scores) if strength_scores else 0
        if avg_strength < 60:
            strategic_opportunities.append("Competitors moderately weak - opportunity to differentiate")

        if not strategic_opportunities:
            strategic_opportunities.append("Monitor competitive landscape quarterly")

        # Identify your competitive position focus
        focus_areas = []
        if collective_share > 50:
            focus_areas.append("Focus on differentiation in crowded market")
        else:
            focus_areas.append("Market consolidation opportunity")

        return {
            "total_competitors_analyzed": len(self.analysis_results),
            "avg_competitor_threat_rank": round(sum(threat_ranks) / len(threat_ranks), 1) if threat_ranks else 0,
            "avg_competitor_strength": round(avg_strength, 1),
            "competitive_landscape": self.competitive_summary.get("competitive_landscape_health", "UNKNOWN"),
            "collective_competitor_market_share": self.competitive_summary.get("collective_market_share_percent", 0),
            "top_threat": self.competitive_summary.get("top_threat_competitor", "NONE"),
            "strategic_priorities": focus_areas,
            "strategic_opportunities": strategic_opportunities,
            "competitive_advantage_focus": "Quality, service, and differentiation over price competition",
        }
