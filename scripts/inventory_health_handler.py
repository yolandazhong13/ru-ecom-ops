#!/usr/bin/env python3
"""Concrete ActionHandler for inventory health monitoring on WB_CN.

Implements inventory health workflow with:
1. Stock level monitoring and alerts
2. Supply chain health assessment
3. SKU performance tracking
4. Inventory optimization recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class InventoryHealthError(Exception):
    """Raised when inventory health operations fail."""
    pass


class InventoryHealthActionHandler(ActionHandler):
    """Handles inventory health monitoring and supply chain tracking for WB_CN.

    Monitors stock levels, assesses supply chain health, tracks SKU performance,
    and recommends inventory optimization strategies.
    """

    def __init__(
        self,
        client_id: str,
        inventory_data: dict[str, dict],
    ):
        """Initialize inventory health handler.

        Args:
            client_id: WB_CN client identifier
            inventory_data: Dict mapping sku_id to inventory info:
                {
                    "SKU-001": {
                        "sku_id": "SKU-001",
                        "sku_name": "Premium Speaker",
                        "current_stock": 450,
                        "in_transit_qty": 150,
                        "locked_qty": 50,
                        "daily_sales_avg": 15,
                        "reorder_point": 100,
                        "safety_stock": 75,
                        "warehouse_location": "WH-CN-001",
                        "last_restock_days_ago": 10,
                        "supplier_lead_time_days": 20,
                        "stock_turn_rate": 24
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "inventory_health"
        self.platform = "WB_CN"
        self.inventory_data = inventory_data
        self.analysis_results = {}
        self.health_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute inventory health analysis.

        Args:
            content: Approval content with inventory monitoring criteria

        Returns:
            Dict with inventory health analysis and recommendations
        """
        # Validate inventory data
        validation_errors = []
        for sku_id, sku_info in self.inventory_data.items():
            errors = self._validate_inventory_data(sku_id, sku_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise InventoryHealthError(f"Inventory validation failed: {validation_errors}")

        # Analyze each SKU
        for sku_id, sku_info in self.inventory_data.items():
            analysis = self._analyze_inventory_health(sku_id, sku_info)
            self.analysis_results[sku_id] = analysis

        # Generate health summary
        self.health_summary = self._generate_health_summary()

        return {
            "inventory_data": self.inventory_data,
            "analysis_results": self.analysis_results,
            "health_summary": self.health_summary,
            "sku_count": len(self.inventory_data),
            "inventory_strategy": self._summarize_inventory_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of inventory health analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with inventory checks
        """
        validation_checks = {
            "all_skus_analyzed": False,
            "stock_levels_valid": False,
            "health_scores_calculated": False,
            "alert_conditions_identified": False,
            "recommendations_provided": False,
        }

        error_details = []

        # Check 1: All SKUs analyzed
        analysis_results = execution_result.get("analysis_results", {})
        inventory_data = execution_result.get("inventory_data", {})
        if len(analysis_results) == len(inventory_data) and len(inventory_data) > 0:
            validation_checks["all_skus_analyzed"] = True

        # Check 2: Stock levels valid
        levels_valid = True
        for sku_id, analysis in analysis_results.items():
            days_available = analysis.get("days_stock_available", 0)
            if not (0 <= days_available <= 365):
                levels_valid = False
                error_details.append(f"{sku_id}: days_stock_available {days_available} out of range")
        validation_checks["stock_levels_valid"] = levels_valid

        # Check 3: Health scores calculated
        scores_valid = True
        for sku_id, analysis in analysis_results.items():
            score = analysis.get("health_score", 0)
            if not (0 <= score <= 100):
                scores_valid = False
                error_details.append(f"{sku_id}: health_score {score} out of range")
        validation_checks["health_scores_calculated"] = scores_valid

        # Check 4: Alert conditions identified
        alerts_valid = True
        for sku_id, analysis in analysis_results.items():
            alert = analysis.get("alert_level", None)
            if alert not in ["GREEN", "YELLOW", "ORANGE", "RED"]:
                alerts_valid = False
                error_details.append(f"{sku_id}: invalid alert_level {alert}")
        validation_checks["alert_conditions_identified"] = alerts_valid

        # Check 5: Recommendations provided
        summary = execution_result.get("inventory_strategy", {})
        if summary and summary.get("optimization_areas"):
            validation_checks["recommendations_provided"] = True
        else:
            error_details.append("No recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_inventory_health" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "sku_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_inventory_data(self, sku_id: str, sku_info: dict[str, Any]) -> list[str]:
        """Validate inventory data.

        Args:
            sku_id: SKU identifier
            sku_info: SKU info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "sku_id": str,
            "sku_name": str,
            "current_stock": int,
            "in_transit_qty": int,
            "locked_qty": int,
            "daily_sales_avg": (int, float),
            "reorder_point": int,
            "safety_stock": int,
            "warehouse_location": str,
            "last_restock_days_ago": int,
            "supplier_lead_time_days": int,
            "stock_turn_rate": (int, float),
        }

        for field, field_type in required_fields.items():
            if field not in sku_info:
                errors.append(f"{sku_id}: missing required field {field}")
                continue

            value = sku_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{sku_id}: {field} must be {field_type}")

        # Validate ranges (non-negative)
        if "current_stock" in sku_info and sku_info["current_stock"] < 0:
            errors.append(f"{sku_id}: current_stock must be non-negative")

        if "daily_sales_avg" in sku_info and sku_info["daily_sales_avg"] < 0:
            errors.append(f"{sku_id}: daily_sales_avg must be non-negative")

        if "stock_turn_rate" in sku_info and sku_info["stock_turn_rate"] < 0:
            errors.append(f"{sku_id}: stock_turn_rate must be non-negative")

        return errors

    def _analyze_inventory_health(self, sku_id: str, sku_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze inventory health for a SKU.

        Args:
            sku_id: SKU identifier
            sku_info: SKU info dict

        Returns:
            Dict with inventory health analysis
        """
        current_stock = sku_info.get("current_stock", 0)
        in_transit = sku_info.get("in_transit_qty", 0)
        locked = sku_info.get("locked_qty", 0)
        daily_sales = sku_info.get("daily_sales_avg", 1)
        reorder_point = sku_info.get("reorder_point", 0)
        safety_stock = sku_info.get("safety_stock", 0)
        warehouse = sku_info.get("warehouse_location", "UNKNOWN")
        last_restock = sku_info.get("last_restock_days_ago", 0)
        lead_time = sku_info.get("supplier_lead_time_days", 0)
        turn_rate = sku_info.get("stock_turn_rate", 0)

        # Calculate available stock (current - locked)
        available_stock = current_stock - locked

        # Calculate days of stock available
        days_available = (available_stock / daily_sales) if daily_sales > 0 else 0

        # Calculate projected stock (including in-transit)
        projected_stock = available_stock + in_transit

        # Calculate stock status
        if available_stock <= safety_stock:
            stock_status = "CRITICAL"
            alert_level = "RED"
        elif available_stock <= reorder_point:
            stock_status = "LOW"
            alert_level = "ORANGE"
        elif available_stock <= reorder_point * 1.5:
            stock_status = "MODERATE"
            alert_level = "YELLOW"
        else:
            stock_status = "HEALTHY"
            alert_level = "GREEN"

        # Calculate coverage
        with_intransit_coverage = (projected_stock / daily_sales) if daily_sales > 0 else 0

        # Supply chain health assessment
        supply_health = self._assess_supply_chain_health(
            current_stock, in_transit, lead_time, daily_sales, last_restock
        )

        # Stock velocity assessment
        if turn_rate > 24:
            velocity = "HIGH"
            velocity_score = 90
        elif turn_rate > 12:
            velocity = "MODERATE"
            velocity_score = 70
        elif turn_rate > 6:
            velocity = "SLOW"
            velocity_score = 40
        else:
            velocity = "VERY_SLOW"
            velocity_score = 20

        # Overall health score
        health_score = self._calculate_health_score(
            days_available, alert_level, supply_health["health_score"], velocity_score
        )

        # Generate recommendations
        recommendations = self._recommend_actions(
            stock_status, alert_level, in_transit, lead_time, turn_rate
        )

        # Projected stockout risk
        if daily_sales > 0:
            days_to_stockout = available_stock / daily_sales
            stockout_risk = "HIGH" if days_to_stockout < 7 else "MODERATE" if days_to_stockout < 14 else "LOW"
        else:
            days_to_stockout = 999
            stockout_risk = "LOW"

        return {
            "sku_id": sku_id,
            "sku_name": sku_info.get("sku_name", sku_id),
            "current_stock": current_stock,
            "available_stock": available_stock,
            "in_transit_qty": in_transit,
            "locked_qty": locked,
            "daily_sales_avg": round(daily_sales, 2),
            "days_stock_available": round(days_available, 1),
            "days_stock_with_intransit": round(with_intransit_coverage, 1),
            "reorder_point": reorder_point,
            "safety_stock": safety_stock,
            "stock_status": stock_status,
            "alert_level": alert_level,
            "warehouse_location": warehouse,
            "last_restock_days_ago": last_restock,
            "supplier_lead_time_days": lead_time,
            "stock_turn_rate_annual": round(turn_rate, 1),
            "velocity": velocity,
            "velocity_score": velocity_score,
            "supply_chain_health": supply_health.get("status", "UNKNOWN"),
            "supply_chain_health_score": supply_health.get("health_score", 0),
            "days_to_potential_stockout": round(days_to_stockout, 1),
            "stockout_risk": stockout_risk,
            "health_score": round(health_score, 1),
            "recommendations": recommendations,
        }

    def _assess_supply_chain_health(self, current_stock: int, in_transit: int,
                                   lead_time: int, daily_sales: float,
                                   last_restock: int) -> dict[str, Any]:
        """Assess supply chain health.

        Args:
            current_stock: Current stock level
            in_transit: In-transit quantity
            lead_time: Supplier lead time in days
            daily_sales: Average daily sales
            last_restock: Days since last restock

        Returns:
            Dict with supply chain assessment
        """
        # Check if in-transit replenishment is adequate
        in_transit_coverage = (in_transit / daily_sales) if daily_sales > 0 else 0

        # Lead time vs restock frequency
        if last_restock > lead_time:
            pipeline_status = "DELAYED"
            pipeline_score = 20
        elif last_restock > lead_time * 0.5:
            pipeline_status = "NORMAL"
            pipeline_score = 70
        else:
            pipeline_status = "ACTIVE"
            pipeline_score = 90

        # In-transit adequacy
        if in_transit_coverage < 5:
            intransit_status = "INSUFFICIENT"
            intransit_score = 30
        elif in_transit_coverage < 15:
            intransit_status = "ADEQUATE"
            intransit_score = 70
        else:
            intransit_status = "ROBUST"
            intransit_score = 90

        # Overall supply chain health
        health_score = (pipeline_score * 0.6 + intransit_score * 0.4)

        if health_score >= 75:
            status = "HEALTHY"
        elif health_score >= 50:
            status = "MODERATE"
        else:
            status = "CONCERNING"

        return {
            "status": status,
            "health_score": round(health_score, 1),
            "pipeline_status": pipeline_status,
            "intransit_status": intransit_status,
        }

    def _calculate_health_score(self, days_available: float, alert_level: str,
                               supply_score: float, velocity_score: float) -> float:
        """Calculate overall inventory health score.

        Args:
            days_available: Days of stock available
            alert_level: Alert level (GREEN/YELLOW/ORANGE/RED)
            supply_score: Supply chain health score
            velocity_score: Stock velocity score

        Returns:
            Health score 0-100
        """
        # Alert level scoring
        alert_scores = {"GREEN": 100, "YELLOW": 60, "ORANGE": 30, "RED": 10}
        alert_score = alert_scores.get(alert_level, 50)

        # Days available scoring (target 30-60 days)
        if days_available < 7:
            days_score = 20
        elif days_available < 14:
            days_score = 40
        elif days_available < 30:
            days_score = 70
        elif days_available < 60:
            days_score = 100
        else:
            days_score = 85  # Overstocked slightly

        # Combine scores
        health_score = (alert_score * 0.3 + days_score * 0.35 + supply_score * 0.2 + velocity_score * 0.15)

        return health_score

    def _recommend_actions(self, stock_status: str, alert_level: str,
                          in_transit: int, lead_time: int, turn_rate: float) -> list[str]:
        """Recommend inventory actions.

        Args:
            stock_status: Stock status level
            alert_level: Alert level
            in_transit: In-transit quantity
            lead_time: Lead time in days
            turn_rate: Stock turn rate

        Returns:
            List of recommendations
        """
        recommendations = []

        if stock_status == "CRITICAL":
            recommendations.append("URGENT: Stock critically low - expedite inbound shipment")
            if in_transit == 0:
                recommendations.append("URGENT: No in-transit stock - place emergency order immediately")

        elif stock_status == "LOW":
            recommendations.append("Low stock: Monitor closely and expedite inbound if needed")
            if lead_time > 14:
                recommendations.append("Long lead time: Consider advance orders")

        elif stock_status == "MODERATE":
            recommendations.append("Stock at reorder point: Prepare for next replenishment cycle")

        else:  # HEALTHY
            if turn_rate < 6:
                recommendations.append("Stock moving slowly: Consider promotional pricing")
            else:
                recommendations.append("Stock levels and velocity optimal - maintain current strategy")

        # Supply chain recommendations
        if in_transit > 0:
            recommendations.append(f"Track in-transit shipment - ETA in {lead_time} days")
        else:
            recommendations.append("No in-transit stock: Establish regular replenishment cycle")

        # Optimization suggestions
        if turn_rate > 30:
            recommendations.append("Fast-moving SKU: Consider increasing safety stock")
        elif turn_rate < 3:
            recommendations.append("Slow-moving SKU: Evaluate demand forecasting accuracy")

        return recommendations

    def _generate_health_summary(self) -> dict[str, Any]:
        """Generate inventory health summary.

        Returns:
            Dict with health summary
        """
        green_skus = []
        yellow_skus = []
        orange_skus = []
        red_skus = []

        total_stock = 0
        total_in_transit = 0
        total_locked = 0
        avg_health_score = 0
        at_risk_count = 0

        for sku_id, analysis in self.analysis_results.items():
            alert = analysis.get("alert_level", "UNKNOWN")
            if alert == "GREEN":
                green_skus.append(sku_id)
            elif alert == "YELLOW":
                yellow_skus.append(sku_id)
            elif alert == "ORANGE":
                orange_skus.append(sku_id)
            else:
                red_skus.append(sku_id)

            total_stock += analysis.get("current_stock", 0)
            total_in_transit += analysis.get("in_transit_qty", 0)
            total_locked += analysis.get("locked_qty", 0)
            avg_health_score += analysis.get("health_score", 0)

            if analysis.get("alert_level") in ["ORANGE", "RED"]:
                at_risk_count += 1

        sku_count = len(self.analysis_results)
        avg_health_score = avg_health_score / sku_count if sku_count > 0 else 0

        # Overall portfolio health
        portfolio_health = "HEALTHY" if avg_health_score > 70 else "CAUTION" if avg_health_score > 50 else "AT_RISK"

        return {
            "green_alert_skus": green_skus,
            "yellow_alert_skus": yellow_skus,
            "orange_alert_skus": orange_skus,
            "red_alert_skus": red_skus,
            "alert_distribution": {
                "GREEN": len(green_skus),
                "YELLOW": len(yellow_skus),
                "ORANGE": len(orange_skus),
                "RED": len(red_skus),
            },
            "total_skus": sku_count,
            "skus_at_risk": at_risk_count,
            "total_current_stock": total_stock,
            "total_in_transit_qty": total_in_transit,
            "total_locked_qty": total_locked,
            "avg_health_score": round(avg_health_score, 1),
            "portfolio_health_status": portfolio_health,
            "monitoring_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_inventory_strategy(self) -> dict[str, Any]:
        """Summarize inventory strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_skus": 0}

        health_scores = [a.get("health_score", 0) for a in self.analysis_results.values()]
        days_available = [a.get("days_stock_available", 0) for a in self.analysis_results.values()]
        turn_rates = [a.get("stock_turn_rate_annual", 0) for a in self.analysis_results.values()]

        # Identify optimization areas
        optimization_areas = []

        red_count = len(self.health_summary.get("red_alert_skus", []))
        if red_count > 0:
            optimization_areas.append(f"{red_count} SKUs in critical condition - immediate action required")

        orange_count = len(self.health_summary.get("orange_alert_skus", []))
        if orange_count > 0:
            optimization_areas.append(f"{orange_count} SKUs with low stock - monitor closely")

        avg_days = sum(days_available) / len(days_available) if days_available else 0
        if avg_days > 90:
            optimization_areas.append("Excessive inventory levels - review demand forecasting")
        elif avg_days < 15:
            optimization_areas.append("Tight inventory - increase replenishment frequency")

        slow_movers = len([t for t in turn_rates if t < 3])
        if slow_movers > 0:
            optimization_areas.append(f"{slow_movers} slow-moving SKUs - review pricing/promotion strategy")

        if not optimization_areas:
            optimization_areas.append("Inventory portfolio well-balanced")

        return {
            "total_skus_monitored": len(self.analysis_results),
            "avg_health_score": round(sum(health_scores) / len(health_scores), 1) if health_scores else 0,
            "portfolio_health": self.health_summary.get("portfolio_health_status", "UNKNOWN"),
            "avg_days_stock_available": round(sum(days_available) / len(days_available), 1) if days_available else 0,
            "fast_movers_count": len([t for t in turn_rates if t > 24]),
            "slow_movers_count": len([t for t in turn_rates if t < 3]),
            "skus_requiring_attention": self.health_summary.get("skus_at_risk", 0),
            "optimization_areas": optimization_areas,
            "strategic_focus": "Balance stockouts, overstocking, and cash flow optimization",
        }
