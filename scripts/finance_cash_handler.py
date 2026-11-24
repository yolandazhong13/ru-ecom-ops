#!/usr/bin/env python3
"""Concrete ActionHandler for financial and cash flow management on WB_CN.

Implements financial workflow with:
1. Cash position and flow analysis
2. Burn rate calculation
3. Runway projection
4. Financial health assessment
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class FinanceCashError(Exception):
    """Raised when financial operations fail."""
    pass


class FinanceCashActionHandler(ActionHandler):
    """Handles financial and cash flow management for WB_CN.

    Monitors cash position, calculates burn rate, projects runway,
    and assesses overall financial health of operations.
    """

    def __init__(
        self,
        client_id: str,
        financial_data: dict[str, Any],
    ):
        """Initialize finance/cash handler.

        Args:
            client_id: WB_CN client identifier
            financial_data: Dict with financial metrics:
                {
                    "current_cash_rub": 500000,
                    "monthly_revenue_rub": 250000,
                    "monthly_cogs_rub": 120000,
                    "monthly_operating_costs_rub": 50000,
                    "monthly_marketing_spend_rub": 30000,
                    "accounts_receivable_rub": 75000,
                    "accounts_payable_rub": 40000,
                    "inventory_value_rub": 180000,
                    "liabilities_rub": 100000,
                    "reporting_period_days": 30
                }
        """
        self.client_id = str(client_id)
        self.action_type = "finance_cash"
        self.platform = "WB_CN"
        self.financial_data = financial_data
        self.analysis_results = {}
        self.cash_flow_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute financial and cash flow analysis.

        Args:
            content: Approval content with financial analysis criteria

        Returns:
            Dict with financial analysis and cash flow projections
        """
        # Validate financial data
        validation_errors = self._validate_financial_data()

        if validation_errors:
            raise FinanceCashError(f"Financial validation failed: {validation_errors}")

        # Analyze financial position
        self.analysis_results = self._analyze_financial_position()

        # Generate cash flow summary
        self.cash_flow_summary = self._generate_cash_flow_summary()

        return {
            "financial_data": self.financial_data,
            "analysis_results": self.analysis_results,
            "cash_flow_summary": self.cash_flow_summary,
            "financial_assessment": self._assess_financial_health(),
            "recommendations": self._generate_recommendations(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of financial analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with financial checks
        """
        validation_checks = {
            "cash_position_analyzed": False,
            "burn_rate_calculated": False,
            "runway_projected": False,
            "financial_ratios_valid": False,
            "recommendations_provided": False,
        }

        error_details = []

        # Check 1: Cash position analyzed
        analysis = execution_result.get("analysis_results", {})
        if analysis and "current_cash_rub" in analysis:
            validation_checks["cash_position_analyzed"] = True

        # Check 2: Burn rate calculated
        if analysis and "monthly_burn_rate_rub" in analysis:
            burn_rate = analysis.get("monthly_burn_rate_rub", 0)
            if isinstance(burn_rate, (int, float)):
                validation_checks["burn_rate_calculated"] = True
            else:
                error_details.append("Burn rate is not numeric")

        # Check 3: Runway projected
        if analysis and "runway_months" in analysis:
            validation_checks["runway_projected"] = True
        else:
            error_details.append("Runway not projected")

        # Check 4: Financial ratios valid
        ratios_valid = True
        if analysis:
            current_ratio = analysis.get("current_ratio", 0)
            if not (0 <= current_ratio <= 10):
                ratios_valid = False
                error_details.append(f"current_ratio {current_ratio} out of reasonable range")

            margin = analysis.get("gross_margin_percent", 0)
            if not (0 <= margin <= 100):
                ratios_valid = False
                error_details.append(f"gross_margin_percent {margin}% out of range")

        validation_checks["financial_ratios_valid"] = ratios_valid

        # Check 5: Recommendations provided
        recommendations = execution_result.get("recommendations", [])
        if recommendations and len(recommendations) > 0:
            validation_checks["recommendations_provided"] = True
        else:
            error_details.append("No financial recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_financial_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_financial_data(self) -> list[str]:
        """Validate financial data.

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "current_cash_rub": (int, float),
            "monthly_revenue_rub": (int, float),
            "monthly_cogs_rub": (int, float),
            "monthly_operating_costs_rub": (int, float),
            "monthly_marketing_spend_rub": (int, float),
            "accounts_receivable_rub": (int, float),
            "accounts_payable_rub": (int, float),
            "inventory_value_rub": (int, float),
            "liabilities_rub": (int, float),
            "reporting_period_days": int,
        }

        for field, field_type in required_fields.items():
            if field not in self.financial_data:
                errors.append(f"missing required field {field}")
                continue

            value = self.financial_data[field]
            if not isinstance(value, field_type):
                errors.append(f"{field} must be {field_type}")

        # Validate ranges (non-negative)
        non_negative_fields = [
            "current_cash_rub", "monthly_revenue_rub", "monthly_cogs_rub",
            "monthly_operating_costs_rub", "monthly_marketing_spend_rub",
            "accounts_receivable_rub", "accounts_payable_rub", "inventory_value_rub",
            "liabilities_rub"
        ]
        for field in non_negative_fields:
            if field in self.financial_data and self.financial_data[field] < 0:
                errors.append(f"{field} must be non-negative")

        if "reporting_period_days" in self.financial_data:
            days = self.financial_data["reporting_period_days"]
            if days <= 0 or days > 90:
                errors.append(f"reporting_period_days must be between 1 and 90")

        return errors

    def _analyze_financial_position(self) -> dict[str, Any]:
        """Analyze financial position.

        Returns:
            Dict with financial analysis
        """
        current_cash = self.financial_data.get("current_cash_rub", 0)
        monthly_revenue = self.financial_data.get("monthly_revenue_rub", 0)
        monthly_cogs = self.financial_data.get("monthly_cogs_rub", 0)
        monthly_operating = self.financial_data.get("monthly_operating_costs_rub", 0)
        monthly_marketing = self.financial_data.get("monthly_marketing_spend_rub", 0)
        ar = self.financial_data.get("accounts_receivable_rub", 0)
        ap = self.financial_data.get("accounts_payable_rub", 0)
        inventory = self.financial_data.get("inventory_value_rub", 0)
        liabilities = self.financial_data.get("liabilities_rub", 0)
        reporting_days = self.financial_data.get("reporting_period_days", 30)

        # Calculate monthly burn rate (expenses - revenue)
        total_monthly_expenses = monthly_cogs + monthly_operating + monthly_marketing
        monthly_net_income = monthly_revenue - total_monthly_expenses
        monthly_burn_rate = -monthly_net_income if monthly_net_income < 0 else 0

        # Calculate runway (months until cash depletes)
        if monthly_burn_rate > 0:
            runway_months = current_cash / monthly_burn_rate
        else:
            runway_months = 999  # Cash positive, infinite runway

        # Calculate financial ratios
        total_assets = current_cash + ar + inventory
        total_liabilities = ap + liabilities
        total_equity = total_assets - total_liabilities

        # Current ratio (liquidity)
        current_ratio = (current_cash + ar) / (ap + liabilities) if (ap + liabilities) > 0 else 0

        # Gross margin
        gross_margin = monthly_revenue - monthly_cogs if monthly_revenue > 0 else 0
        gross_margin_percent = (gross_margin / monthly_revenue * 100) if monthly_revenue > 0 else 0

        # Operating margin
        operating_margin = monthly_revenue - total_monthly_expenses if monthly_revenue > 0 else 0
        operating_margin_percent = (operating_margin / monthly_revenue * 100) if monthly_revenue > 0 else 0

        # Debt to equity ratio
        debt_to_equity = total_liabilities / total_equity if total_equity > 0 else 0

        # Cash conversion cycle
        cash_conversion = (inventory / monthly_cogs * reporting_days) if monthly_cogs > 0 else 0
        cash_conversion += (ar / monthly_revenue * reporting_days) if monthly_revenue > 0 else 0
        cash_conversion -= (ap / monthly_cogs * reporting_days) if monthly_cogs > 0 else 0

        # Financial health score (0-100)
        health_score = self._calculate_health_score(
            runway_months, current_ratio, operating_margin_percent,
            gross_margin_percent, debt_to_equity
        )

        return {
            "current_cash_rub": round(current_cash, 2),
            "monthly_revenue_rub": round(monthly_revenue, 2),
            "monthly_cogs_rub": round(monthly_cogs, 2),
            "monthly_operating_costs_rub": round(monthly_operating, 2),
            "monthly_marketing_spend_rub": round(monthly_marketing, 2),
            "total_monthly_expenses_rub": round(total_monthly_expenses, 2),
            "monthly_net_income_rub": round(monthly_net_income, 2),
            "monthly_burn_rate_rub": round(monthly_burn_rate, 2),
            "accounts_receivable_rub": round(ar, 2),
            "accounts_payable_rub": round(ap, 2),
            "inventory_value_rub": round(inventory, 2),
            "total_assets_rub": round(total_assets, 2),
            "total_liabilities_rub": round(total_liabilities, 2),
            "total_equity_rub": round(total_equity, 2),
            "runway_months": round(runway_months, 1),
            "current_ratio": round(current_ratio, 2),
            "gross_margin_percent": round(gross_margin_percent, 1),
            "operating_margin_percent": round(operating_margin_percent, 1),
            "debt_to_equity_ratio": round(debt_to_equity, 2),
            "cash_conversion_cycle_days": round(cash_conversion, 1),
            "financial_health_score": round(health_score, 1),
        }

    def _calculate_health_score(self, runway: float, current_ratio: float,
                               op_margin: float, gross_margin: float,
                               debt_to_equity: float) -> float:
        """Calculate overall financial health score.

        Args:
            runway: Months of runway
            current_ratio: Current ratio
            op_margin: Operating margin percentage
            gross_margin: Gross margin percentage
            debt_to_equity: Debt to equity ratio

        Returns:
            Health score 0-100
        """
        scores = []

        # Runway score (12+ months = 100, 0-3 = 20)
        runway_score = min(100, max(20, (runway / 12) * 100))
        scores.append(runway_score * 0.3)

        # Liquidity score (1.0+ = 100, <0.5 = 20)
        liquidity_score = min(100, max(20, current_ratio * 100))
        scores.append(liquidity_score * 0.2)

        # Profitability score (op margin 20%+ = 100, negative = 20)
        profitability_score = min(100, max(20, (op_margin + 50) / 0.7))
        scores.append(profitability_score * 0.3)

        # Gross margin score (45%+ = 100, <30% = 20)
        margin_score = min(100, max(20, (gross_margin - 20) / 0.25))
        scores.append(margin_score * 0.1)

        # Leverage score (D/E <0.5 = 100, >2 = 20)
        if debt_to_equity <= 0.5:
            leverage_score = 100
        elif debt_to_equity >= 2:
            leverage_score = 20
        else:
            leverage_score = 100 - ((debt_to_equity - 0.5) / 1.5 * 80)
        scores.append(leverage_score * 0.1)

        return sum(scores)

    def _generate_cash_flow_summary(self) -> dict[str, Any]:
        """Generate cash flow summary.

        Returns:
            Dict with cash flow summary
        """
        analysis = self.analysis_results

        monthly_net = analysis.get("monthly_net_income_rub", 0)
        runway = analysis.get("runway_months", 0)
        health_score = analysis.get("financial_health_score", 0)

        # Determine financial status
        if runway < 3 and monthly_net < 0:
            status = "CRITICAL"
        elif runway < 6 and monthly_net < 0:
            status = "CONCERNING"
        elif monthly_net < 0:
            status = "BURN_MODE"
        else:
            status = "PROFITABLE"

        # Monthly cash flow projection (next 3 months if burn mode)
        projections = []
        for month in range(1, 4):
            projected_cash = analysis.get("current_cash_rub", 0) - (analysis.get("monthly_burn_rate_rub", 0) * month)
            projections.append({
                "month": month,
                "projected_cash_rub": round(max(0, projected_cash), 2),
            })

        return {
            "current_cash_rub": analysis.get("current_cash_rub", 0),
            "monthly_net_income_rub": monthly_net,
            "monthly_burn_rate_rub": analysis.get("monthly_burn_rate_rub", 0),
            "runway_months": runway,
            "financial_status": status,
            "health_score": health_score,
            "cash_flow_projections_3m": projections,
            "analysis_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _assess_financial_health(self) -> dict[str, Any]:
        """Assess overall financial health.

        Returns:
            Dict with health assessment
        """
        analysis = self.analysis_results
        health_score = analysis.get("financial_health_score", 0)

        if health_score >= 80:
            assessment = "EXCELLENT"
        elif health_score >= 60:
            assessment = "GOOD"
        elif health_score >= 40:
            assessment = "FAIR"
        else:
            assessment = "POOR"

        # Identify key metrics
        current_ratio = analysis.get("current_ratio", 0)
        runway = analysis.get("runway_months", 0)
        op_margin = analysis.get("operating_margin_percent", 0)

        concerns = []
        if current_ratio < 1:
            concerns.append("Low liquidity: current_ratio < 1.0")
        if runway < 6 and analysis.get("monthly_burn_rate_rub", 0) > 0:
            concerns.append(f"Limited runway: {runway} months remaining")
        if op_margin < 0:
            concerns.append("Operating losses: negative operating margin")
        if analysis.get("debt_to_equity_ratio", 0) > 2:
            concerns.append("High leverage: debt to equity ratio > 2.0")

        strengths = []
        if current_ratio > 1.5:
            strengths.append("Strong liquidity position")
        if op_margin > 15:
            strengths.append("Healthy operating margins")
        if analysis.get("gross_margin_percent", 0) > 50:
            strengths.append("Strong gross margins")
        if runway > 12:
            strengths.append("Comfortable cash runway")

        return {
            "overall_assessment": assessment,
            "health_score": health_score,
            "concerns": concerns if concerns else ["None identified"],
            "strengths": strengths if strengths else ["Continue monitoring"],
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate financial recommendations.

        Returns:
            List of recommendations
        """
        recommendations = []
        analysis = self.analysis_results

        # Runway concerns
        runway = analysis.get("runway_months", 0)
        if runway < 3:
            recommendations.append("URGENT: Seek funding or reduce burn rate immediately")
        elif runway < 6:
            recommendations.append("Develop contingency plan for cash shortfall")

        # Burn rate concerns
        burn_rate = analysis.get("monthly_burn_rate_rub", 0)
        if burn_rate > 0:
            recommendations.append("Reduce monthly burn rate - review operating costs")
            recommendations.append("Prioritize revenue growth initiatives")

        # Liquidity concerns
        current_ratio = analysis.get("current_ratio", 0)
        if current_ratio < 1:
            recommendations.append("Improve cash position - reduce AR or increase AP terms")

        # Profitability
        op_margin = analysis.get("operating_margin_percent", 0)
        if op_margin < 0:
            recommendations.append("Improve unit economics - review pricing strategy")
            recommendations.append("Optimize cost structure - identify efficiency opportunities")

        # Working capital
        ccc = analysis.get("cash_conversion_cycle_days", 0)
        if ccc > 60:
            recommendations.append(f"Improve cash conversion cycle ({ccc} days) - optimize inventory/AR/AP")

        # Leverage
        de_ratio = analysis.get("debt_to_equity_ratio", 0)
        if de_ratio > 2:
            recommendations.append("Reduce debt - prioritize debt repayment")

        # Positive indicators
        if op_margin > 10 and runway > 12:
            recommendations.append("Continue current trajectory - operational health strong")

        if not recommendations:
            recommendations.append("Monitor financial metrics monthly")
            recommendations.append("Maintain current financial discipline")

        return recommendations

    def _summarize_financial_strategy(self) -> dict[str, Any]:
        """Summarize financial strategy insights.

        Returns:
            Summary dict with key metrics
        """
        analysis = self.analysis_results

        return {
            "cash_position": analysis.get("current_cash_rub", 0),
            "monthly_profitability": analysis.get("monthly_net_income_rub", 0),
            "runway_estimate": analysis.get("runway_months", 0),
            "financial_health": analysis.get("financial_health_score", 0),
            "liquidity_ratio": analysis.get("current_ratio", 0),
            "profitability_margin": analysis.get("operating_margin_percent", 0),
        }
