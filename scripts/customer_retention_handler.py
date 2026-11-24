#!/usr/bin/env python3
"""Concrete ActionHandler for customer retention and loyalty management on WB_CN.

Implements customer retention workflow with:
1. Customer lifecycle analysis
2. Churn risk assessment
3. Loyalty program management
4. Retention strategy recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class CustomerRetentionError(Exception):
    """Raised when customer retention operations fail."""
    pass


class CustomerRetentionActionHandler(ActionHandler):
    """Handles customer retention and loyalty program management for WB_CN.

    Analyzes customer lifecycle, identifies churn risks, manages loyalty
    programs, and recommends retention strategies to improve customer LTV.
    """

    def __init__(
        self,
        client_id: str,
        customer_data: dict[str, dict],
    ):
        """Initialize customer retention handler.

        Args:
            client_id: WB_CN client identifier
            customer_data: Dict mapping customer_id to customer info:
                {
                    "cust_001": {
                        "customer_id": "cust_001",
                        "total_purchases": 5,
                        "total_spend_rub": 12500,
                        "first_purchase_days_ago": 180,
                        "last_purchase_days_ago": 15,
                        "avg_order_value_rub": 2500,
                        "repeat_purchase_rate": 0.6,
                        "product_category_diversity": 3,
                        "support_tickets": 1,
                        "net_promoter_score": 8,
                        "loyalty_program_tier": "SILVER"
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "customer_retention"
        self.platform = "WB_CN"
        self.customer_data = customer_data
        self.analysis_results = {}
        self.retention_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute customer retention analysis.

        Args:
            content: Approval content with retention analysis criteria

        Returns:
            Dict with customer analysis and retention recommendations
        """
        # Validate customer data
        validation_errors = []
        for customer_id, customer_info in self.customer_data.items():
            errors = self._validate_customer_data(customer_id, customer_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise CustomerRetentionError(f"Customer validation failed: {validation_errors}")

        # Analyze each customer
        for customer_id, customer_info in self.customer_data.items():
            analysis = self._analyze_customer_retention(customer_id, customer_info)
            self.analysis_results[customer_id] = analysis

        # Generate retention summary
        self.retention_summary = self._generate_retention_summary()

        return {
            "customer_data": self.customer_data,
            "analysis_results": self.analysis_results,
            "retention_summary": self.retention_summary,
            "customer_count": len(self.customer_data),
            "retention_strategy": self._summarize_retention_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of customer retention analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with retention checks
        """
        validation_checks = {
            "all_customers_analyzed": False,
            "churn_risk_scores_valid": False,
            "customer_lifetime_value_calculated": False,
            "loyalty_tiers_assigned": False,
            "retention_recommendations_provided": False,
        }

        error_details = []

        # Check 1: All customers analyzed
        analysis_results = execution_result.get("analysis_results", {})
        customer_data = execution_result.get("customer_data", {})
        if len(analysis_results) == len(customer_data) and len(customer_data) > 0:
            validation_checks["all_customers_analyzed"] = True

        # Check 2: Churn risk scores valid (0-100)
        risk_valid = True
        for customer_id, analysis in analysis_results.items():
            risk_score = analysis.get("churn_risk_score", 0)
            if not (0 <= risk_score <= 100):
                risk_valid = False
                error_details.append(f"{customer_id}: churn_risk_score {risk_score} out of range")
        validation_checks["churn_risk_scores_valid"] = risk_valid

        # Check 3: Customer lifetime value calculated
        ltv_valid = True
        for customer_id, analysis in analysis_results.items():
            ltv = analysis.get("estimated_customer_ltv_rub", None)
            if ltv is None or not isinstance(ltv, (int, float)):
                ltv_valid = False
                error_details.append(f"{customer_id}: customer LTV not calculated")
        validation_checks["customer_lifetime_value_calculated"] = ltv_valid

        # Check 4: Loyalty tiers assigned
        tier_valid = True
        for customer_id, analysis in analysis_results.items():
            tier = analysis.get("retention_tier", None)
            if tier not in ["HIGH_VALUE", "MEDIUM_VALUE", "AT_RISK", "LOW_ENGAGEMENT"]:
                tier_valid = False
                error_details.append(f"{customer_id}: invalid retention_tier {tier}")
        validation_checks["loyalty_tiers_assigned"] = tier_valid

        # Check 5: Retention recommendations provided
        summary = execution_result.get("retention_strategy", {})
        if summary and summary.get("intervention_opportunities"):
            validation_checks["retention_recommendations_provided"] = True
        else:
            error_details.append("No retention recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_retention_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "customer_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_customer_data(self, customer_id: str, customer_info: dict[str, Any]) -> list[str]:
        """Validate customer data.

        Args:
            customer_id: Customer identifier
            customer_info: Customer info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "customer_id": str,
            "total_purchases": int,
            "total_spend_rub": (int, float),
            "first_purchase_days_ago": int,
            "last_purchase_days_ago": int,
            "avg_order_value_rub": (int, float),
            "repeat_purchase_rate": (int, float),
            "product_category_diversity": int,
            "support_tickets": int,
            "net_promoter_score": (int, float),
            "loyalty_program_tier": str,
        }

        for field, field_type in required_fields.items():
            if field not in customer_info:
                errors.append(f"{customer_id}: missing required field {field}")
                continue

            value = customer_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{customer_id}: {field} must be {field_type}")

        # Validate ranges
        if "total_purchases" in customer_info and customer_info["total_purchases"] < 0:
            errors.append(f"{customer_id}: total_purchases must be non-negative")

        if "repeat_purchase_rate" in customer_info:
            rate = customer_info["repeat_purchase_rate"]
            if not (0 <= rate <= 1):
                errors.append(f"{customer_id}: repeat_purchase_rate must be 0-1")

        if "net_promoter_score" in customer_info:
            score = customer_info["net_promoter_score"]
            if not (0 <= score <= 10):
                errors.append(f"{customer_id}: net_promoter_score must be 0-10")

        return errors

    def _analyze_customer_retention(self, customer_id: str, customer_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze customer retention metrics.

        Args:
            customer_id: Customer identifier
            customer_info: Customer info dict

        Returns:
            Dict with customer retention analysis
        """
        total_purchases = customer_info.get("total_purchases", 0)
        total_spend = customer_info.get("total_spend_rub", 0)
        first_purchase_ago = customer_info.get("first_purchase_days_ago", 0)
        last_purchase_ago = customer_info.get("last_purchase_days_ago", 0)
        avg_order_value = customer_info.get("avg_order_value_rub", 0)
        repeat_rate = customer_info.get("repeat_purchase_rate", 0)
        category_diversity = customer_info.get("product_category_diversity", 0)
        support_tickets = customer_info.get("support_tickets", 0)
        nps_score = customer_info.get("net_promoter_score", 0)
        loyalty_tier = customer_info.get("loyalty_program_tier", "BRONZE")

        # Calculate customer lifetime value (CLV)
        # Simple model: total_spend * repeat_rate * (1 + category_diversity * 0.1)
        clv = total_spend * (1 + repeat_rate) * (1 + category_diversity * 0.1)

        # Calculate customer age in months
        customer_age_months = max(1, first_purchase_ago / 30)

        # Calculate monthly spend rate
        monthly_spend = total_spend / customer_age_months if customer_age_months > 0 else 0

        # Calculate purchase frequency (purchases per month)
        purchase_frequency = total_purchases / customer_age_months if customer_age_months > 0 else 0

        # Calculate days since last purchase (recency metric)
        recency = last_purchase_ago

        # Churn risk calculation
        # Factors: recency (high = high risk), purchase frequency (low = high risk), NPS (low = high risk)
        recency_score = min(100, (recency / 60) * 100)  # 60+ days = high risk
        frequency_score = max(0, 100 - (purchase_frequency / 2) * 100)  # <0.5 purchases/month = high risk
        nps_score_risk = max(0, (10 - nps_score) / 10 * 100)  # Low NPS = high risk
        support_score = min(100, support_tickets * 10)  # More tickets = more risk

        churn_risk = (recency_score * 0.4 + frequency_score * 0.25 + nps_score_risk * 0.25 + support_score * 0.1)

        # Determine retention tier based on CLV and churn risk
        if churn_risk < 30 and clv > 50000:
            retention_tier = "HIGH_VALUE"
            tier_recommendation = "NURTURE_AND_EXPAND"
        elif churn_risk < 50 and clv > 20000:
            retention_tier = "MEDIUM_VALUE"
            tier_recommendation = "MAINTAIN_AND_GROW"
        elif churn_risk > 60:
            retention_tier = "AT_RISK"
            tier_recommendation = "URGENT_RETENTION_PROGRAM"
        else:
            retention_tier = "LOW_ENGAGEMENT"
            tier_recommendation = "REACTIVATION_CAMPAIGN"

        # Identify engagement drivers
        engagement_drivers = []
        if repeat_rate > 0.5:
            engagement_drivers.append("Strong repeat purchaser")
        if category_diversity > 2:
            engagement_drivers.append("Cross-category buyer")
        if nps_score >= 8:
            engagement_drivers.append("High promoter")
        if support_tickets == 0:
            engagement_drivers.append("No support issues")

        # Generate retention recommendations
        retention_actions = self._recommend_retention_actions(
            retention_tier, churn_risk, repeat_rate, nps_score, avg_order_value, recency
        )

        # Calculate potential recovery value if at-risk customer is retained
        recovery_value = monthly_spend * 12 if retention_tier == "AT_RISK" else 0

        return {
            "customer_id": customer_id,
            "total_purchases": total_purchases,
            "total_spend_rub": round(total_spend, 2),
            "customer_age_months": round(customer_age_months, 1),
            "monthly_spend_rub": round(monthly_spend, 2),
            "purchase_frequency_per_month": round(purchase_frequency, 2),
            "avg_order_value_rub": round(avg_order_value, 2),
            "repeat_purchase_rate": round(repeat_rate, 2),
            "product_category_diversity": category_diversity,
            "net_promoter_score": round(nps_score, 1),
            "days_since_last_purchase": recency,
            "support_tickets": support_tickets,
            "recency_risk_score": round(recency_score, 1),
            "frequency_risk_score": round(frequency_score, 1),
            "nps_risk_score": round(nps_score_risk, 1),
            "support_risk_score": round(support_score, 1),
            "churn_risk_score": round(churn_risk, 1),
            "estimated_customer_ltv_rub": round(clv, 2),
            "potential_recovery_value_rub": round(recovery_value, 2),
            "retention_tier": retention_tier,
            "tier_recommendation": tier_recommendation,
            "loyalty_program_tier": loyalty_tier,
            "engagement_drivers": engagement_drivers,
            "retention_actions": retention_actions,
        }

    def _recommend_retention_actions(self, tier: str, churn_risk: float, repeat_rate: float,
                                    nps_score: float, avg_order_value: float, recency: int) -> list[str]:
        """Recommend retention actions based on tier and metrics.

        Args:
            tier: Retention tier
            churn_risk: Churn risk score (0-100)
            repeat_rate: Repeat purchase rate
            nps_score: Net Promoter Score (0-10)
            avg_order_value: Average order value
            recency: Days since last purchase

        Returns:
            List of recommended actions
        """
        actions = []

        if tier == "HIGH_VALUE":
            actions.append("VIP program: Exclusive early access to new products")
            actions.append("Personal account manager or concierge service")
            if repeat_rate < 0.7:
                actions.append("Cross-sell premium product bundles")
            actions.append("Annual loyalty bonus/rebate program")

        elif tier == "MEDIUM_VALUE":
            actions.append("Tier-based loyalty rewards acceleration")
            actions.append("Personalized product recommendations")
            if repeat_rate < 0.5:
                actions.append("Special promotions on frequently purchased categories")
            actions.append("Referral bonus program")

        elif tier == "AT_RISK":
            actions.append("URGENT: Send win-back offer (15-20% discount)")
            if recency > 90:
                actions.append("Re-engagement email campaign with incentive")
            if nps_score < 7:
                actions.append("Request feedback and address concerns")
            actions.append("Offering: Free shipping on next order")
            actions.append("Schedule follow-up contact within 7 days")

        else:  # LOW_ENGAGEMENT
            actions.append("Reactivation campaign: Special discount for returning customers")
            actions.append("Product discovery email: New items in preferred categories")
            if avg_order_value > 0:
                actions.append(f"Incentive offer: {int((avg_order_value * 0.1) / 100) * 100} RUB discount")
            actions.append("Survey: Understand why engagement has decreased")

        # General actions for high churn risk
        if churn_risk > 60:
            actions.append("Immediate retention review meeting")
            actions.append("Consider service recovery if any issues exist")

        if nps_score < 6:
            actions.append("Priority: Understand dissatisfaction drivers")
            actions.append("Proactive support outreach")

        return actions

    def _generate_retention_summary(self) -> dict[str, Any]:
        """Generate retention analysis summary.

        Returns:
            Dict with retention summary
        """
        high_value_customers = []
        medium_value_customers = []
        at_risk_customers = []
        low_engagement_customers = []

        total_clv = 0
        total_recovery_potential = 0
        avg_churn_risk = 0

        for customer_id, analysis in self.analysis_results.items():
            tier = analysis.get("retention_tier", "UNKNOWN")
            if tier == "HIGH_VALUE":
                high_value_customers.append(customer_id)
            elif tier == "MEDIUM_VALUE":
                medium_value_customers.append(customer_id)
            elif tier == "AT_RISK":
                at_risk_customers.append(customer_id)
            else:
                low_engagement_customers.append(customer_id)

            total_clv += analysis.get("estimated_customer_ltv_rub", 0)
            total_recovery_potential += analysis.get("potential_recovery_value_rub", 0)
            avg_churn_risk += analysis.get("churn_risk_score", 0)

        customer_count = len(self.analysis_results)
        avg_churn_risk = avg_churn_risk / customer_count if customer_count > 0 else 0

        return {
            "high_value_customers": high_value_customers,
            "medium_value_customers": medium_value_customers,
            "at_risk_customers": at_risk_customers,
            "low_engagement_customers": low_engagement_customers,
            "tier_distribution": {
                "HIGH_VALUE": len(high_value_customers),
                "MEDIUM_VALUE": len(medium_value_customers),
                "AT_RISK": len(at_risk_customers),
                "LOW_ENGAGEMENT": len(low_engagement_customers),
            },
            "total_customers": customer_count,
            "total_customer_lifetime_value_rub": round(total_clv, 2),
            "retention_recovery_opportunity_rub": round(total_recovery_potential, 2),
            "avg_churn_risk_score": round(avg_churn_risk, 1),
            "portfolio_health": "HEALTHY" if avg_churn_risk < 40 else "AT_RISK" if avg_churn_risk > 60 else "MODERATE",
            "analysis_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_retention_strategy(self) -> dict[str, Any]:
        """Summarize retention strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_customers": 0}

        clv_values = [a.get("estimated_customer_ltv_rub", 0) for a in self.analysis_results.values()]
        churn_scores = [a.get("churn_risk_score", 0) for a in self.analysis_results.values()]
        nps_scores = [a.get("net_promoter_score", 0) for a in self.analysis_results.values()]

        # Identify intervention opportunities
        intervention_opportunities = []

        at_risk_count = len(self.retention_summary.get("at_risk_customers", []))
        if at_risk_count > 0:
            intervention_opportunities.append(f"{at_risk_count} at-risk customers need urgent retention program")

        high_value_count = len(self.retention_summary.get("high_value_customers", []))
        if high_value_count > 0:
            intervention_opportunities.append(f"Expand VIP program for {high_value_count} high-value customers")

        low_engagement_count = len(self.retention_summary.get("low_engagement_customers", []))
        if low_engagement_count > 0:
            intervention_opportunities.append(f"Reactivation campaigns for {low_engagement_count} low-engagement customers")

        if not intervention_opportunities:
            intervention_opportunities.append("Portfolio well-balanced across retention tiers")

        return {
            "total_customers": len(self.analysis_results),
            "avg_customer_lifetime_value_rub": round(sum(clv_values) / len(clv_values), 2) if clv_values else 0,
            "portfolio_total_clv_rub": self.retention_summary.get("total_customer_lifetime_value_rub", 0),
            "recovery_opportunity_rub": self.retention_summary.get("retention_recovery_opportunity_rub", 0),
            "avg_churn_risk": round(sum(churn_scores) / len(churn_scores), 1) if churn_scores else 0,
            "avg_nps_score": round(sum(nps_scores) / len(nps_scores), 1) if nps_scores else 0,
            "portfolio_health": self.retention_summary.get("portfolio_health", "UNKNOWN"),
            "intervention_opportunities": intervention_opportunities,
            "strategic_focus": "Balance between nurturing high-value customers and recovering at-risk segment",
        }
