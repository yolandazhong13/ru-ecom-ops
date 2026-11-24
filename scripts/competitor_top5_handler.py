#!/usr/bin/env python3
"""Concrete ActionHandler for competitor tracking and analysis on WB_CN.

Implements competitor intelligence with:
1. Top 5 competitor identification
2. Price and positioning monitoring
3. Product strategy analysis
4. Competitive recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class CompetitorTrackingError(Exception):
    """Raised when competitor tracking fails."""
    pass


class CompetitorTop5ActionHandler(ActionHandler):
    """Handles top-5 competitor tracking and analysis for WB_CN.

    Monitors competitor pricing, positioning, and strategy to inform
    product and pricing decisions.
    """

    def __init__(
        self,
        client_id: str,
        competitor_data: dict[str, dict],
    ):
        """Initialize competitor tracking handler.

        Args:
            client_id: WB_CN client identifier
            competitor_data: Dict mapping competitor_id to competitor info:
                {
                    "comp_001": {
                        "shop_name": "Factory Direct Store",
                        "product_count": 342,
                        "avg_rating": 4.8,
                        "follower_count": 15000,
                        "price_range_min": 1500,
                        "price_range_max": 4500,
                        "market_share_estimate": 0.08,
                        "promotion_frequency": "high"
                    }
                }
        """
        self.client_id = str(client_id)
        self.competitor_data = competitor_data
        self.analysis_results = {}
        self.ranking = []

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute competitor analysis per content_for_approval.

        Args:
            content: Approval content with competitor tracking criteria

        Returns:
            Dict with competitor analysis and strategic recommendations
        """
        # Validate competitor data
        validation_errors = []
        for comp_id, comp_info in self.competitor_data.items():
            errors = self._validate_competitor(comp_id, comp_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise CompetitorTrackingError(f"Competitor validation failed: {validation_errors}")

        # Analyze each competitor
        for comp_id, comp_info in self.competitor_data.items():
            analysis = self._analyze_competitor(comp_id, comp_info)
            self.analysis_results[comp_id] = analysis

        # Generate ranking and recommendations
        self.ranking = self._generate_ranking()

        return {
            "competitor_data": self.competitor_data,
            "analysis_results": self.analysis_results,
            "top5_ranking": self.ranking,
            "competitor_count": len(self.competitor_data),
            "strategic_summary": self._summarize_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of competitor analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with analysis checks
        """
        validation_checks = {
            "all_competitors_analyzed": False,
            "threat_scores_valid": False,
            "ranking_provided": False,
            "market_data_complete": False,
            "strategic_insights_included": False,
        }

        error_details = []

        # Check 1: All competitors analyzed
        analysis_results = execution_result.get("analysis_results", {})
        competitor_data = execution_result.get("competitor_data", {})
        if len(analysis_results) == len(competitor_data) and len(competitor_data) > 0:
            validation_checks["all_competitors_analyzed"] = True

        # Check 2: Threat scores in valid range (0-100)
        scores_valid = True
        for comp_id, analysis in analysis_results.items():
            threat_score = analysis.get("threat_score", 0)
            if not (0 <= threat_score <= 100):
                scores_valid = False
                error_details.append(f"{comp_id}: threat_score {threat_score} out of range")
        validation_checks["threat_scores_valid"] = scores_valid

        # Check 3: Ranking provided
        ranking = execution_result.get("top5_ranking", [])
        if ranking and len(ranking) > 0:
            validation_checks["ranking_provided"] = True
        else:
            error_details.append("No competitor ranking generated")

        # Check 4: Market data complete
        market_complete = True
        for comp_id, analysis in analysis_results.items():
            required_fields = [
                "avg_rating", "follower_count", "market_share_estimate",
                "pricing_competitiveness", "threat_score"
            ]
            for field in required_fields:
                if field not in analysis or analysis[field] is None:
                    market_complete = False
                    error_details.append(f"{comp_id}: missing market data {field}")
        validation_checks["market_data_complete"] = market_complete

        # Check 5: Strategic insights included
        summary = execution_result.get("strategic_summary", {})
        if summary and summary.get("top_threat") and summary.get("market_opportunity"):
            validation_checks["strategic_insights_included"] = True
        else:
            error_details.append("Strategic insights incomplete")

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

    def _validate_competitor(self, comp_id: str, comp_info: dict[str, Any]) -> list[str]:
        """Validate a single competitor entry.

        Args:
            comp_id: Competitor identifier
            comp_info: Competitor info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "shop_name": str,
            "product_count": int,
            "avg_rating": (int, float),
            "follower_count": int,
            "price_range_min": (int, float),
            "price_range_max": (int, float),
            "market_share_estimate": (int, float),
            "promotion_frequency": str,
        }

        for field, field_type in required_fields.items():
            if field not in comp_info:
                errors.append(f"{comp_id}: missing required field {field}")
                continue

            value = comp_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{comp_id}: {field} must be {field_type}")

        # Validate ranges
        if "avg_rating" in comp_info:
            rating = comp_info["avg_rating"]
            if not (0 <= rating <= 5):
                errors.append(f"{comp_id}: avg_rating must be between 0 and 5")

        if "market_share_estimate" in comp_info:
            share = comp_info["market_share_estimate"]
            if not (0 <= share <= 1):
                errors.append(f"{comp_id}: market_share_estimate must be between 0 and 1")

        # Validate price range consistency
        if "price_range_min" in comp_info and "price_range_max" in comp_info:
            min_p = comp_info["price_range_min"]
            max_p = comp_info["price_range_max"]
            if min_p > max_p:
                errors.append(f"{comp_id}: price_range_min must be <= price_range_max")

        return errors

    def _analyze_competitor(self, comp_id: str, comp_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single competitor.

        Args:
            comp_id: Competitor identifier
            comp_info: Competitor info dict

        Returns:
            Dict with competitive analysis
        """
        shop_name = comp_info.get("shop_name", comp_id)
        avg_rating = comp_info.get("avg_rating", 3.0)
        follower_count = comp_info.get("follower_count", 0)
        market_share = comp_info.get("market_share_estimate", 0)
        promotion_freq = comp_info.get("promotion_frequency", "low")
        product_count = comp_info.get("product_count", 0)
        price_min = comp_info.get("price_range_min", 0)
        price_max = comp_info.get("price_range_max", 0)

        # Calculate quality score (0-100)
        quality_score = avg_rating * 20  # 5 stars = 100

        # Calculate reach score (0-100, logarithmic)
        reach_score = min(100, (follower_count / 100000) * 100) if follower_count > 0 else 0

        # Calculate market presence (0-100)
        market_presence = min(100, (market_share * 1000) if market_share > 0 else 0)

        # Calculate aggressiveness score based on promotion frequency
        aggressiveness_map = {"low": 20, "medium": 50, "high": 80}
        aggressiveness = aggressiveness_map.get(promotion_freq, 50)

        # Calculate pricing competitiveness (0-100, center at mid-range)
        price_mid = (price_min + price_max) / 2 if price_max > 0 else 0
        price_range = price_max - price_min
        pricing_competitiveness = min(100, 100 - (price_range / 5000 * 100))

        # Composite threat score
        threat_score = (
            quality_score * 0.25 +
            reach_score * 0.25 +
            market_presence * 0.30 +
            aggressiveness * 0.20
        )

        return {
            "competitor_id": comp_id,
            "shop_name": shop_name,
            "avg_rating": round(avg_rating, 2),
            "follower_count": follower_count,
            "product_count": product_count,
            "market_share_estimate": round(market_share, 3),
            "promotion_frequency": promotion_freq,
            "quality_score": round(quality_score, 1),
            "reach_score": round(reach_score, 1),
            "market_presence": round(market_presence, 1),
            "aggressiveness": round(aggressiveness, 1),
            "pricing_competitiveness": round(pricing_competitiveness, 1),
            "threat_score": round(threat_score, 1),
            "threat_level": self._get_threat_level(threat_score),
        }

    def _get_threat_level(self, threat_score: float) -> str:
        """Get threat level string based on score.

        Args:
            threat_score: Competitive threat score

        Returns:
            Threat level string
        """
        if threat_score >= 70:
            return "CRITICAL"
        elif threat_score >= 50:
            return "HIGH"
        elif threat_score >= 30:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_ranking(self) -> list[dict[str, Any]]:
        """Generate top 5 competitor ranking.

        Returns:
            List of top 5 competitors with rankings
        """
        # Sort by threat score descending
        sorted_competitors = sorted(
            self.analysis_results.items(),
            key=lambda x: x[1].get("threat_score", 0),
            reverse=True
        )

        ranking = []
        for idx, (comp_id, analysis) in enumerate(sorted_competitors[:5], 1):
            ranking.append({
                "rank": idx,
                "competitor_id": comp_id,
                "shop_name": analysis.get("shop_name"),
                "threat_score": analysis.get("threat_score"),
                "threat_level": analysis.get("threat_level"),
            })

        return ranking

    def _summarize_strategy(self) -> dict[str, Any]:
        """Summarize strategic competitive insights.

        Returns:
            Summary dict with key insights
        """
        if not self.analysis_results:
            return {"total_competitors": 0}

        threat_scores = [a.get("threat_score", 0) for a in self.analysis_results.values()]
        avg_threat = sum(threat_scores) / len(threat_scores) if threat_scores else 0

        # Find top threat
        top_threat = None
        top_threat_score = 0
        for comp_id, analysis in self.analysis_results.items():
            if analysis.get("threat_score", 0) > top_threat_score:
                top_threat = comp_id
                top_threat_score = analysis.get("threat_score", 0)

        # Identify market opportunity (gap in market)
        avg_quality = sum(a.get("quality_score", 0) for a in self.analysis_results.values()) / len(self.analysis_results) if self.analysis_results else 0
        avg_reach = sum(a.get("reach_score", 0) for a in self.analysis_results.values()) / len(self.analysis_results) if self.analysis_results else 0

        opportunity = "high_quality_low_reach" if avg_quality > 60 and avg_reach < 40 else "low_quality_high_reach" if avg_quality < 40 and avg_reach > 60 else "balanced_competition"

        return {
            "total_competitors": len(self.analysis_results),
            "avg_threat_score": round(avg_threat, 1),
            "top_threat": top_threat,
            "top_threat_score": round(top_threat_score, 1),
            "market_opportunity": opportunity,
            "critical_threats": sum(1 for a in self.analysis_results.values() if a.get("threat_level") == "CRITICAL"),
        }
