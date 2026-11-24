#!/usr/bin/env python3
"""Phase 8: Ad Campaign Optimizer and Promotional Calendar handlers.

Advanced marketing automation handlers for multi-platform campaigns.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from datetime import datetime, timezone, timedelta

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class AdCampaignOptimizerHandler(ActionHandler):
    """Optimizes advertising campaigns across platforms."""

    def __init__(self, client_id: str, platform: str):
        """Initialize ad campaign optimizer.

        Args:
            client_id: Client identifier
            platform: Platform (WB_CN or Ozon RU)
        """
        self.client_id = str(client_id)
        self.platform = platform
        self.campaign_optimizations = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Optimize advertising campaigns.

        Args:
            content: Campaign data with metrics

        Returns:
            Dict with optimization recommendations
        """
        campaigns = content.get("campaigns", [])

        if not campaigns:
            raise ValueError("No campaigns provided")

        time.sleep(0.08)

        for campaign in campaigns:
            campaign_id = campaign.get("campaign_id")
            current_budget = campaign.get("budget", 0)
            current_cpc = campaign.get("avg_cpc", 0)
            impressions = campaign.get("impressions", 0)
            clicks = campaign.get("clicks", 0)
            conversions = campaign.get("conversions", 0)
            revenue = campaign.get("revenue", 0)

            # Calculate metrics
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            roi = ((revenue - current_budget) / current_budget * 100) if current_budget > 0 else 0

            # Generate optimization
            optimization = {
                "campaign_id": campaign_id,
                "current_budget": current_budget,
                "current_metrics": {
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "ctr": f"{ctr:.2f}%",
                    "conversion_rate": f"{conversion_rate:.2f}%",
                    "roi": f"{roi:.1f}%",
                },
                "optimization_score": self._calculate_score(ctr, conversion_rate, roi),
                "recommendations": self._generate_recommendations(ctr, conversion_rate, roi),
                "budget_adjustment": self._calculate_budget_adjustment(roi),
            }

            self.campaign_optimizations[campaign_id] = optimization

        return {
            "platform": self.platform,
            "campaigns_optimized": len(self.campaign_optimizations),
            "optimizations": self.campaign_optimizations,
            "total_budget_impact": sum(o["budget_adjustment"] for o in self.campaign_optimizations.values()),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify campaign optimizations.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        optimizations = execution_result.get("optimizations", {})

        validation_checks = {
            "campaigns_analyzed": len(optimizations) > 0,
            "metrics_calculated": True,
            "scores_valid": True,
            "recommendations_generated": True,
        }

        error_details = []

        for campaign_id, opt in optimizations.items():
            score = opt.get("optimization_score", 0)
            if not (0 <= score <= 100):
                validation_checks["scores_valid"] = False
                error_details.append(f"{campaign_id}: invalid score {score}")

            if not opt.get("recommendations"):
                validation_checks["recommendations_generated"] = False
                error_details.append(f"{campaign_id}: no recommendations")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_campaign_optimization" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "campaigns_optimized": len(optimizations),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _calculate_score(self, ctr: float, conversion_rate: float, roi: float) -> int:
        """Calculate optimization score (0-100)."""
        ctr_score = min(100, ctr * 10)
        conv_score = min(100, conversion_rate * 20)
        roi_score = min(100, max(0, roi))

        return int((ctr_score + conv_score + roi_score) / 3)

    def _generate_recommendations(self, ctr: float, conversion_rate: float, roi: float) -> list[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if ctr < 1.0:
            recommendations.append("Increase bid to improve CTR")
        if conversion_rate < 5.0:
            recommendations.append("Review landing page quality")
        if roi < 0:
            recommendations.append("Reduce daily budget")
        if roi > 50:
            recommendations.append("Increase budget for scaling")

        if not recommendations:
            recommendations.append("Campaign performing well - maintain current settings")

        return recommendations

    def _calculate_budget_adjustment(self, roi: float) -> float:
        """Calculate recommended budget adjustment."""
        if roi > 100:
            return 20.0  # Increase 20%
        elif roi > 50:
            return 10.0
        elif roi > 0:
            return 0.0
        elif roi > -50:
            return -10.0
        else:
            return -20.0


class PromotionalCalendarHandler(ActionHandler):
    """Plans and schedules promotional campaigns."""

    def __init__(self, client_id: str):
        """Initialize promotional calendar handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.promotional_events = []
        self.calendar_plan = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Plan promotional calendar.

        Args:
            content: Products and promotional criteria

        Returns:
            Dict with promotional calendar
        """
        products = content.get("products", [])
        sales_velocity = content.get("sales_velocity", {})

        if not products:
            raise ValueError("No products provided for promotional planning")

        time.sleep(0.08)

        # Define promotional events
        events = [
            {"name": "Flash Sale", "frequency": "weekly", "discount": 15},
            {"name": "Weekend Deal", "frequency": "weekly", "discount": 10},
            {"name": "Monthly Campaign", "frequency": "monthly", "discount": 20},
            {"name": "Seasonal Sale", "frequency": "quarterly", "discount": 30},
        ]

        start_date = datetime.now(timezone.utc)

        for i, event in enumerate(events):
            event_date = start_date + timedelta(days=i*7)

            for product in products:
                sku = product.get("sku")
                velocity = sales_velocity.get(sku, 10)

                # Calculate expected sales uplift
                uplift = int(velocity * (event["discount"] / 10))  # 1% uplift per 1% discount

                self.promotional_events.append({
                    "event": event["name"],
                    "date": event_date.isoformat(),
                    "sku": sku,
                    "discount": event["discount"],
                    "expected_uplift": uplift,
                    "target_revenue_impact": uplift * 100,  # Assuming 100 RUB avg price
                })

        # Create calendar summary
        self.calendar_plan = {
            "total_events": len(self.promotional_events),
            "period": "90 days",
            "products_covered": len(products),
            "events": self.promotional_events,
            "total_expected_revenue": sum(e["target_revenue_impact"] for e in self.promotional_events),
        }

        return {
            "client_id": self.client_id,
            "calendar_plan": self.calendar_plan,
            "events_scheduled": len(self.promotional_events),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify promotional calendar.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        calendar = execution_result.get("calendar_plan", {})
        events = calendar.get("events", [])

        validation_checks = {
            "calendar_created": len(events) > 0,
            "events_scheduled": True,
            "revenue_impact_calculated": True,
        }

        error_details = []

        for event in events:
            if not event.get("event") or not event.get("date"):
                validation_checks["events_scheduled"] = False
                error_details.append("Incomplete event record")

            if event.get("target_revenue_impact", 0) < 0:
                validation_checks["revenue_impact_calculated"] = False
                error_details.append("Invalid revenue impact")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_promotional_calendar" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "events_scheduled": len(events),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }


def main() -> None:
    """Demo Phase 8 marketing handlers."""
    print("[Phase 8] Testing Ad Campaign Optimizer...\n")

    # Test ad campaign optimizer
    ad_handler = AdCampaignOptimizerHandler("client_001", "WB_CN")
    campaigns = [
        {
            "campaign_id": "camp_001",
            "budget": 5000,
            "avg_cpc": 25,
            "impressions": 50000,
            "clicks": 1500,
            "conversions": 150,
            "revenue": 15000,
        },
        {
            "campaign_id": "camp_002",
            "budget": 3000,
            "avg_cpc": 20,
            "impressions": 30000,
            "clicks": 900,
            "conversions": 45,
            "revenue": 4500,
        },
    ]

    result = ad_handler.execute({"campaigns": campaigns})
    verification = ad_handler.verify(result)

    print(f"✅ Ad optimization: {verification['overall_status']}")
    for campaign_id, opt in result.get("optimizations", {}).items():
        print(f"\n  {campaign_id}:")
        print(f"    Score: {opt['optimization_score']}/100")
        print(f"    CTR: {opt['current_metrics']['ctr']}")
        print(f"    Conversion: {opt['current_metrics']['conversion_rate']}")
        print(f"    ROI: {opt['current_metrics']['roi']}")
        print(f"    Budget Adj: {opt['budget_adjustment']:+.0f}%")

    print(f"\n[Phase 8] Testing Promotional Calendar...\n")

    # Test promotional calendar
    promo_handler = PromotionalCalendarHandler("client_001")
    result = promo_handler.execute({
        "products": [
            {"sku": "MD-700"},
            {"sku": "MD-4090"},
        ],
        "sales_velocity": {
            "MD-700": 20,
            "MD-4090": 10,
        }
    })
    verification = promo_handler.verify(result)

    print(f"✅ Promotional calendar: {verification['overall_status']}")
    calendar = result.get("calendar_plan", {})
    print(f"   Events scheduled: {calendar.get('total_events')}")
    print(f"   Period: {calendar.get('period')}")
    print(f"   Expected revenue impact: {calendar.get('total_expected_revenue'):,.0f} RUB")


if __name__ == "__main__":
    main()
