#!/usr/bin/env python3
"""Concrete ActionHandler for pricing optimization on WB_CN.

Implements dynamic pricing workflow with:
1. Competitive price positioning analysis
2. Price elasticity and demand modeling
3. Margin optimization recommendations
4. Dynamic pricing strategy suggestions
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class PricingOptimizationError(Exception):
    """Raised when pricing optimization operations fail."""
    pass


class PricingOptimizationActionHandler(ActionHandler):
    """Handles pricing optimization and strategy for WB_CN.

    Analyzes competitive pricing, demand elasticity, and margin targets
    to recommend optimal pricing and dynamic pricing strategies.
    """

    def __init__(
        self,
        client_id: str,
        pricing_data: dict[str, dict],
    ):
        """Initialize pricing optimization handler.

        Args:
            client_id: WB_CN client identifier
            pricing_data: Dict mapping product_id to pricing info:
                {
                    "MD-700": {
                        "product_id": "MD-700",
                        "product_name": "Mesh Speaker",
                        "current_price_rub": 2500,
                        "cost_rub": 1200,
                        "competitor_price_min_rub": 2200,
                        "competitor_price_max_rub": 3000,
                        "competitor_price_avg_rub": 2650,
                        "monthly_sales_volume": 500,
                        "search_rank": 3,
                        "stock_level": 450,
                        "market_saturation": 0.65,
                        "is_flagship": False,
                        "price_sensitivity": 0.8
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "pricing_optimization"
        self.platform = "WB_CN"
        self.pricing_data = pricing_data
        self.analysis_results = {}
        self.optimization_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute pricing optimization analysis.

        Args:
            content: Approval content with pricing optimization criteria

        Returns:
            Dict with pricing analysis and optimization recommendations
        """
        # Validate pricing data
        validation_errors = []
        for product_id, product_info in self.pricing_data.items():
            errors = self._validate_pricing_data(product_id, product_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise PricingOptimizationError(f"Pricing validation failed: {validation_errors}")

        # Analyze pricing for each product
        for product_id, product_info in self.pricing_data.items():
            analysis = self._analyze_pricing_opportunity(product_id, product_info)
            self.analysis_results[product_id] = analysis

        # Generate optimization summary
        self.optimization_summary = self._generate_optimization_summary()

        return {
            "pricing_data": self.pricing_data,
            "analysis_results": self.analysis_results,
            "optimization_summary": self.optimization_summary,
            "product_count": len(self.pricing_data),
            "pricing_strategy": self._summarize_pricing_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of pricing optimization.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with pricing checks
        """
        validation_checks = {
            "all_products_analyzed": False,
            "competitive_positioning_valid": False,
            "margin_calculations_verified": False,
            "price_recommendations_provided": False,
            "strategy_recommendations_included": False,
        }

        error_details = []

        # Check 1: All products analyzed
        analysis_results = execution_result.get("analysis_results", {})
        pricing_data = execution_result.get("pricing_data", {})
        if len(analysis_results) == len(pricing_data) and len(pricing_data) > 0:
            validation_checks["all_products_analyzed"] = True

        # Check 2: Competitive positioning valid
        positioning_valid = True
        for product_id, analysis in analysis_results.items():
            position = analysis.get("competitive_position", None)
            if position not in ["PREMIUM", "MARKET_ALIGNED", "VALUE_PLAY"]:
                positioning_valid = False
                error_details.append(f"{product_id}: invalid competitive_position {position}")
        validation_checks["competitive_positioning_valid"] = positioning_valid

        # Check 3: Margin calculations verified
        margins_valid = True
        for product_id, analysis in analysis_results.items():
            margin = analysis.get("current_margin_percent", 0)
            if not (0 <= margin <= 100):
                margins_valid = False
                error_details.append(f"{product_id}: current_margin_percent {margin}% out of range")
        validation_checks["margin_calculations_verified"] = margins_valid

        # Check 4: Price recommendations provided
        for product_id, analysis in analysis_results.items():
            recommended_price = analysis.get("recommended_price_rub", None)
            if recommended_price is None:
                error_details.append(f"{product_id}: no recommended_price provided")
        if len(error_details) == 0:
            validation_checks["price_recommendations_provided"] = True

        # Check 5: Strategy recommendations included
        strategy = execution_result.get("pricing_strategy", {})
        if strategy and strategy.get("optimization_opportunities"):
            validation_checks["strategy_recommendations_included"] = True
        else:
            error_details.append("No strategy recommendations generated")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_pricing_optimization" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "product_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_pricing_data(self, product_id: str, product_info: dict[str, Any]) -> list[str]:
        """Validate pricing data for a product.

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
            "current_price_rub": (int, float),
            "cost_rub": (int, float),
            "competitor_price_min_rub": (int, float),
            "competitor_price_max_rub": (int, float),
            "competitor_price_avg_rub": (int, float),
            "monthly_sales_volume": int,
            "search_rank": int,
            "stock_level": int,
            "market_saturation": (int, float),
            "is_flagship": bool,
            "price_sensitivity": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in product_info:
                errors.append(f"{product_id}: missing required field {field}")
                continue

            value = product_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{product_id}: {field} must be {field_type}")

        # Validate ranges
        if "current_price_rub" in product_info and product_info["current_price_rub"] <= 0:
            errors.append(f"{product_id}: current_price_rub must be positive")

        if "cost_rub" in product_info and product_info["cost_rub"] < 0:
            errors.append(f"{product_id}: cost_rub must be non-negative")

        if "market_saturation" in product_info:
            sat = product_info["market_saturation"]
            if not (0 <= sat <= 1):
                errors.append(f"{product_id}: market_saturation must be 0-1")

        if "price_sensitivity" in product_info:
            sens = product_info["price_sensitivity"]
            if not (0 <= sens <= 1):
                errors.append(f"{product_id}: price_sensitivity must be 0-1")

        # Validate price range consistency
        min_p = product_info.get("competitor_price_min_rub", 0)
        max_p = product_info.get("competitor_price_max_rub", 0)
        if min_p > max_p:
            errors.append(f"{product_id}: competitor_price_min must be <= competitor_price_max")

        return errors

    def _analyze_pricing_opportunity(self, product_id: str, product_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze pricing opportunity for a single product.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            Dict with pricing analysis
        """
        current_price = product_info.get("current_price_rub", 0)
        cost = product_info.get("cost_rub", 0)
        comp_min = product_info.get("competitor_price_min_rub", 0)
        comp_max = product_info.get("competitor_price_max_rub", 0)
        comp_avg = product_info.get("competitor_price_avg_rub", 0)
        monthly_volume = product_info.get("monthly_sales_volume", 0)
        search_rank = product_info.get("search_rank", 999)
        stock_level = product_info.get("stock_level", 0)
        market_saturation = product_info.get("market_saturation", 0)
        is_flagship = product_info.get("is_flagship", False)
        price_sensitivity = product_info.get("price_sensitivity", 0)

        # Calculate current margin
        current_margin = current_price - cost if current_price > cost else 0
        current_margin_percent = (current_margin / current_price * 100) if current_price > 0 else 0

        # Calculate competitive positioning
        comp_range = comp_max - comp_min
        comp_mid = (comp_min + comp_max) / 2 if comp_max > 0 else 0
        price_vs_avg = ((current_price - comp_avg) / comp_avg * 100) if comp_avg > 0 else 0

        if current_price > comp_avg * 1.05:
            competitive_position = "PREMIUM"
        elif current_price < comp_avg * 0.95:
            competitive_position = "VALUE_PLAY"
        else:
            competitive_position = "MARKET_ALIGNED"

        # Calculate price elasticity impact
        # Higher price_sensitivity = more elastic (demand changes more with price)
        elasticity_factor = price_sensitivity

        # Optimize price based on factors
        # Consider: margin target (40%), competitor positioning, demand, stock, market saturation

        # Base target: 40% margin
        target_margin_percent = 40
        target_price_from_margin = cost / (1 - target_margin_percent / 100) if target_margin_percent < 100 else current_price

        # Adjust based on inventory and market saturation
        inventory_factor = 1.0
        if stock_level < monthly_volume * 0.5:
            inventory_factor = 1.1  # Low inventory - increase price
        elif stock_level > monthly_volume * 2:
            inventory_factor = 0.95  # High inventory - decrease price

        saturation_factor = 1.0
        if market_saturation > 0.8:
            saturation_factor = 0.98  # High saturation - slight price decrease
        elif market_saturation < 0.3:
            saturation_factor = 1.05  # Low saturation - slight price increase

        # Adjust based on search rank (visibility)
        visibility_factor = 1.0
        if search_rank > 10:
            visibility_factor = 0.98  # Low visibility - decrease price to boost sales
        elif search_rank <= 3:
            visibility_factor = 1.03  # High visibility - premium pricing possible

        # Calculate recommended price
        recommended_price = target_price_from_margin * inventory_factor * saturation_factor * visibility_factor

        # Round to nearest 50 rubles for practical pricing
        recommended_price = round(recommended_price / 50) * 50

        # Calculate projected metrics
        projected_margin = recommended_price - cost if recommended_price > cost else 0
        projected_margin_percent = (projected_margin / recommended_price * 100) if recommended_price > 0 else 0

        # Estimate demand impact
        price_change_percent = ((recommended_price - current_price) / current_price * 100) if current_price > 0 else 0
        demand_elasticity = -elasticity_factor * price_change_percent  # Negative = higher price = lower demand
        projected_volume = monthly_volume * (1 + demand_elasticity / 100)

        projected_revenue = recommended_price * projected_volume
        current_revenue = current_price * monthly_volume

        # Determine pricing recommendation
        revenue_improvement = ((projected_revenue - current_revenue) / current_revenue * 100) if current_revenue > 0 else 0

        if abs(recommended_price - current_price) < 50:
            recommendation = "MAINTAIN_CURRENT"
        elif revenue_improvement > 5:
            recommendation = "INCREASE_PRICE"
        elif revenue_improvement < -5 and current_margin_percent > 25:
            recommendation = "DECREASE_PRICE"
        else:
            recommendation = "MONITOR_AND_ADJUST"

        # Suggested dynamic pricing strategy
        if is_flagship:
            strategy = "PREMIUM_POSITIONING"
        elif market_saturation > 0.75:
            strategy = "COMPETITIVE_MATCHING"
        elif search_rank > 10:
            strategy = "AGGRESSIVE_PROMOTION"
        else:
            strategy = "BALANCED_OPTIMIZATION"

        return {
            "product_id": product_id,
            "product_name": product_info.get("product_name", product_id),
            "current_price_rub": round(current_price, 2),
            "cost_rub": round(cost, 2),
            "current_margin_rub": round(current_margin, 2),
            "current_margin_percent": round(current_margin_percent, 1),
            "competitor_price_min_rub": round(comp_min, 2),
            "competitor_price_max_rub": round(comp_max, 2),
            "competitor_price_avg_rub": round(comp_avg, 2),
            "price_vs_competitors_percent": round(price_vs_avg, 1),
            "competitive_position": competitive_position,
            "monthly_sales_volume": monthly_volume,
            "search_rank": search_rank,
            "stock_level": stock_level,
            "market_saturation": round(market_saturation, 2),
            "price_sensitivity": round(price_sensitivity, 2),
            "recommended_price_rub": round(recommended_price, 2),
            "projected_margin_rub": round(projected_margin, 2),
            "projected_margin_percent": round(projected_margin_percent, 1),
            "price_change_rub": round(recommended_price - current_price, 2),
            "price_change_percent": round(price_change_percent, 1),
            "projected_volume": round(projected_volume, 0),
            "projected_revenue_rub": round(projected_revenue, 2),
            "revenue_improvement_percent": round(revenue_improvement, 1),
            "pricing_recommendation": recommendation,
            "dynamic_pricing_strategy": strategy,
        }

    def _generate_optimization_summary(self) -> dict[str, Any]:
        """Generate pricing optimization summary.

        Returns:
            Dict with optimization summary
        """
        increase_candidates = []
        decrease_candidates = []
        maintain_candidates = []

        total_current_revenue = 0
        total_projected_revenue = 0

        for product_id, analysis in self.analysis_results.items():
            rec = analysis.get("pricing_recommendation", "UNKNOWN")
            if rec == "INCREASE_PRICE":
                increase_candidates.append(product_id)
            elif rec == "DECREASE_PRICE":
                decrease_candidates.append(product_id)
            else:
                maintain_candidates.append(product_id)

            total_current_revenue += analysis.get("current_price_rub", 0) * analysis.get("monthly_sales_volume", 0)
            total_projected_revenue += analysis.get("projected_revenue_rub", 0)

        total_revenue_opportunity = total_projected_revenue - total_current_revenue

        return {
            "increase_price_candidates": increase_candidates,
            "decrease_price_candidates": decrease_candidates,
            "maintain_price_candidates": maintain_candidates,
            "total_increase_opportunities": len(increase_candidates),
            "total_decrease_opportunities": len(decrease_candidates),
            "total_maintain": len(maintain_candidates),
            "total_current_monthly_revenue_rub": round(total_current_revenue, 2),
            "total_projected_monthly_revenue_rub": round(total_projected_revenue, 2),
            "revenue_opportunity_rub": round(total_revenue_opportunity, 2),
            "revenue_opportunity_percent": round((total_revenue_opportunity / total_current_revenue * 100) if total_current_revenue > 0 else 0, 1),
            "optimization_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_pricing_strategy(self) -> dict[str, Any]:
        """Summarize pricing strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_products": 0}

        # Count by strategy type
        strategies = {}
        for analysis in self.analysis_results.values():
            strategy = analysis.get("dynamic_pricing_strategy", "UNKNOWN")
            strategies[strategy] = strategies.get(strategy, 0) + 1

        # Count by competitive position
        positions = {}
        for analysis in self.analysis_results.values():
            position = analysis.get("competitive_position", "UNKNOWN")
            positions[position] = positions.get(position, 0) + 1

        # Calculate portfolio metrics
        margins = [a.get("current_margin_percent", 0) for a in self.analysis_results.values()]
        avg_margin = sum(margins) / len(margins) if margins else 0

        optimization_opportunities = []
        if len(self.analysis_results) > 0:
            if len(self.optimization_summary.get("increase_price_candidates", [])) > 0:
                optimization_opportunities.append("Price increases available for select products")
            if len(self.optimization_summary.get("decrease_price_candidates", [])) > 0:
                optimization_opportunities.append("Price reductions can boost volume")
            if self.optimization_summary.get("revenue_opportunity_rub", 0) > 0:
                optimization_opportunities.append(f"Revenue opportunity: {self.optimization_summary.get('revenue_opportunity_rub')} RUB")

        return {
            "total_products": len(self.analysis_results),
            "avg_current_margin_percent": round(avg_margin, 1),
            "highest_margin_percent": round(max(margins), 1) if margins else 0,
            "lowest_margin_percent": round(min(margins), 1) if margins else 0,
            "pricing_strategies": strategies,
            "competitive_positions": positions,
            "portfolio_strategy_distribution": strategies,
            "monthly_revenue_opportunity_rub": self.optimization_summary.get("revenue_opportunity_rub", 0),
            "optimization_opportunities": optimization_opportunities if optimization_opportunities else ["Portfolio well-optimized"],
            "portfolio_health": "STRONG" if avg_margin > 35 else "GOOD" if avg_margin > 25 else "NEEDS_REVIEW",
        }
