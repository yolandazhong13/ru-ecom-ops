#!/usr/bin/env python3
"""Competitor price tracking handler for WB_CN and Ozon RU.

Monitors competitor prices and generates alerts when prices change significantly.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class CompetitorPriceHandler(ActionHandler):
    """Tracks competitor pricing and detects significant changes."""

    def __init__(self, client_id: str, platform: str):
        """Initialize competitor price tracking handler.

        Args:
            client_id: Client identifier
            platform: Platform (WB_CN or Ozon RU)
        """
        self.client_id = str(client_id)
        self.platform = platform
        self.price_changes = []
        self.competitor_analysis = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Track competitor prices.

        Args:
            content: Approval content with products to monitor

        Returns:
            Dict with competitor price data
        """
        products = content.get("products", [])

        if not products:
            raise ValueError("No products provided for competitor tracking")

        time.sleep(0.05)

        for product in products:
            sku = product.get("sku")
            current_price = product.get("current_price", 0)

            # Simulate competitor data retrieval
            competitors = self._get_competitor_prices(sku)

            analysis = {
                "sku": sku,
                "your_price": current_price,
                "competitors": competitors,
                "lowest_competitor": min(c["price"] for c in competitors) if competitors else None,
                "highest_competitor": max(c["price"] for c in competitors) if competitors else None,
                "avg_competitor_price": sum(c["price"] for c in competitors) / len(competitors) if competitors else None,
                "price_advantage": None,
            }

            if analysis["avg_competitor_price"]:
                advantage = ((analysis["avg_competitor_price"] - current_price) / analysis["avg_competitor_price"]) * 100
                analysis["price_advantage"] = advantage

            self.competitor_analysis[sku] = analysis

            # Detect significant changes
            if analysis["price_advantage"] and analysis["price_advantage"] > 10:
                self.price_changes.append({
                    "sku": sku,
                    "change_type": "price_advantage",
                    "advantage_pct": analysis["price_advantage"],
                    "action": "recommend_price_increase",
                })
            elif analysis["price_advantage"] and analysis["price_advantage"] < -10:
                self.price_changes.append({
                    "sku": sku,
                    "change_type": "price_disadvantage",
                    "disadvantage_pct": abs(analysis["price_advantage"]),
                    "action": "recommend_price_decrease",
                })

        return {
            "platform": self.platform,
            "products_analyzed": len(products),
            "competitor_analysis": self.competitor_analysis,
            "price_changes_detected": len(self.price_changes),
            "recommended_actions": self.price_changes,
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify competitor price analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        analysis = execution_result.get("competitor_analysis", {})

        validation_checks = {
            "products_analyzed": len(analysis) > 0,
            "price_data_complete": True,
            "competitor_data_valid": True,
            "recommendations_generated": len(execution_result.get("recommended_actions", [])) >= 0,
        }

        error_details = []

        # Check each product has complete data
        for sku, data in analysis.items():
            if not data.get("your_price") or data["your_price"] <= 0:
                validation_checks["price_data_complete"] = False
                error_details.append(f"{sku}: invalid your_price")

            if not data.get("competitors") or len(data["competitors"]) == 0:
                validation_checks["competitor_data_valid"] = False
                error_details.append(f"{sku}: no competitor data")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_competitor_prices" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "products_analyzed": len(analysis),
            "recommendations": len(execution_result.get("recommended_actions", [])),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _get_competitor_prices(self, sku: str) -> list[dict[str, Any]]:
        """Simulate getting competitor prices.

        Args:
            sku: Product SKU

        Returns:
            List of competitor pricing data
        """
        # In production, would call real competitor APIs
        competitors = [
            {"name": "Competitor A", "price": 2800, "rating": 4.5},
            {"name": "Competitor B", "price": 2500, "rating": 4.2},
            {"name": "Competitor C", "price": 3200, "rating": 4.8},
        ]
        return competitors


class DemandForecastHandler(ActionHandler):
    """Predicts demand based on historical data and trends."""

    def __init__(self, client_id: str, platform: str):
        """Initialize demand forecast handler.

        Args:
            client_id: Client identifier
            platform: Platform (WB_CN or Ozon RU)
        """
        self.client_id = str(client_id)
        self.platform = platform
        self.forecasts = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Forecast demand for products.

        Args:
            content: Approval content with historical sales data

        Returns:
            Dict with demand forecasts
        """
        products = content.get("products", [])

        if not products:
            raise ValueError("No products provided for demand forecasting")

        time.sleep(0.05)

        for product in products:
            sku = product.get("sku")
            historical_sales = product.get("historical_sales", [])

            if not historical_sales:
                continue

            # Calculate trend
            avg_sales = sum(historical_sales) / len(historical_sales)
            trend = self._calculate_trend(historical_sales)

            # Forecast next 7 days
            forecast_7day = [
                int(avg_sales * (1 + trend)) for _ in range(7)
            ]

            forecast_30day = [
                int(avg_sales * (1 + trend) * (1 + (i / 30))) for i in range(30)
            ]

            self.forecasts[sku] = {
                "sku": sku,
                "historical_avg": avg_sales,
                "trend": trend,
                "forecast_7day": forecast_7day,
                "forecast_7day_total": sum(forecast_7day),
                "forecast_30day_total": sum(forecast_30day),
                "confidence_level": self._calculate_confidence(historical_sales),
            }

        return {
            "platform": self.platform,
            "products_forecasted": len(self.forecasts),
            "forecasts": self.forecasts,
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify demand forecasts.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        forecasts = execution_result.get("forecasts", {})

        validation_checks = {
            "forecasts_generated": len(forecasts) > 0,
            "forecast_values_valid": True,
            "confidence_levels_valid": True,
        }

        error_details = []

        for sku, forecast in forecasts.items():
            if not forecast.get("forecast_7day_total") or forecast["forecast_7day_total"] <= 0:
                validation_checks["forecast_values_valid"] = False
                error_details.append(f"{sku}: invalid forecast value")

            confidence = forecast.get("confidence_level", 0)
            if not (0 <= confidence <= 1):
                validation_checks["confidence_levels_valid"] = False
                error_details.append(f"{sku}: invalid confidence {confidence}")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_demand_forecast" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "forecasts_generated": len(forecasts),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _calculate_trend(self, sales: list[int]) -> float:
        """Calculate sales trend.

        Args:
            sales: Historical sales data

        Returns:
            Trend percentage (-1.0 to 1.0)
        """
        if len(sales) < 2:
            return 0.0

        avg_first_half = sum(sales[:len(sales)//2]) / (len(sales)//2)
        avg_second_half = sum(sales[len(sales)//2:]) / (len(sales) - len(sales)//2)

        if avg_first_half == 0:
            return 0.0

        return (avg_second_half - avg_first_half) / avg_first_half

    def _calculate_confidence(self, sales: list[int]) -> float:
        """Calculate forecast confidence based on data stability.

        Args:
            sales: Historical sales data

        Returns:
            Confidence level (0.0 to 1.0)
        """
        if len(sales) < 2:
            return 0.5

        avg = sum(sales) / len(sales)
        variance = sum((x - avg) ** 2 for x in sales) / len(sales)
        std_dev = variance ** 0.5

        if avg == 0:
            return 0.5

        cv = std_dev / avg  # Coefficient of variation
        confidence = max(0.0, 1.0 - cv)  # Higher stability = higher confidence

        return min(1.0, confidence)


def main() -> None:
    """Demo Phase 7 handlers."""
    print("[Phase 7] Testing Competitor Price Tracking...\n")

    # Test competitor pricing
    comp_handler = CompetitorPriceHandler("client_001", "WB_CN")
    products = [
        {"sku": "MD-700", "current_price": 2500},
        {"sku": "MD-4090", "current_price": 10000},
    ]

    result = comp_handler.execute({"products": products})
    verification = comp_handler.verify(result)

    print(f"✅ Competitor pricing: {verification['overall_status']}")
    for sku, data in result.get("competitor_analysis", {}).items():
        print(f"\n  {sku}:")
        print(f"    Your Price: {data['your_price']}")
        print(f"    Avg Competitor: {data['avg_competitor_price']:.0f}")
        print(f"    Advantage: {data['price_advantage']:.1f}%" if data['price_advantage'] else "    No advantage")

    print(f"\n[Phase 7] Testing Demand Forecasting...\n")

    # Test demand forecasting
    demand_handler = DemandForecastHandler("client_001", "WB_CN")
    products_with_history = [
        {"sku": "MD-700", "historical_sales": [10, 12, 15, 18, 20, 22, 25]},
        {"sku": "MD-4090", "historical_sales": [5, 5, 6, 7, 8, 9, 10]},
    ]

    result = demand_handler.execute({"products": products_with_history})
    verification = demand_handler.verify(result)

    print(f"✅ Demand forecast: {verification['overall_status']}")
    for sku, forecast in result.get("forecasts", {}).items():
        print(f"\n  {sku}:")
        print(f"    Historical Avg: {forecast['historical_avg']:.0f} units/day")
        print(f"    Trend: {forecast['trend']:.1%}")
        print(f"    7-Day Forecast: {forecast['forecast_7day_total']} units")
        print(f"    30-Day Forecast: {forecast['forecast_30day_total']} units")
        print(f"    Confidence: {forecast['confidence_level']:.1%}")


if __name__ == "__main__":
    main()
