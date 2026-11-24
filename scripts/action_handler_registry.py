#!/usr/bin/env python3
"""ActionHandler Registry - Central registration and routing for all workflow handlers.

Maintains handler registry with action_type@platform format keys.
Enables UnifiedActionExecutor to route actions to correct handler implementations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Type

from unified_action_executor import ActionHandler

# Import all handler implementations
from inventory_replenishment_handler import InventoryReplenishmentActionHandler
from returns_profit_handler import ReturnsProfitActionHandler
from finance_cash_handler import FinanceCashActionHandler
from supplier_evaluation_handler import SupplierEvaluationActionHandler
from pricing_optimization_handler import PricingOptimizationActionHandler
from promotional_campaign_handler import PromotionalCampaignActionHandler
from customer_retention_handler import CustomerRetentionActionHandler
from social_engagement_handler import SocialEngagementActionHandler
from inventory_health_handler import InventoryHealthActionHandler
from competitor_analysis_handler import CompetitorAnalysisActionHandler

ROOT = Path(__file__).resolve().parents[1]


class ActionHandlerRegistry:
    """Central registry for all ActionHandler implementations.

    Maintains mapping of action_type@platform keys to handler classes.
    Provides lookup and instantiation of handlers for workflow execution.
    """

    def __init__(self):
        """Initialize the ActionHandler registry."""
        self._registry: dict[str, Type[ActionHandler]] = {}
        self._handler_metadata: dict[str, dict[str, Any]] = {}
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Initialize all handler registrations."""
        # Inventory & Supply Chain Handlers
        self.register(
            "inventory_replenishment@WB_CN",
            InventoryReplenishmentActionHandler,
            {
                "name": "Inventory Replenishment",
                "description": "Analyzes inventory levels and recommends replenishment quantities",
                "category": "supply_chain",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

        self.register(
            "inventory_health@WB_CN",
            InventoryHealthActionHandler,
            {
                "name": "Inventory Health Monitoring",
                "description": "Real-time monitoring of stock levels and supply chain health",
                "category": "supply_chain",
                "schedule": "daily_pipeline",
                "approval_level": "P0-2",
            },
        )

        # Financial & Performance Handlers
        self.register(
            "finance_cash@WB_CN",
            FinanceCashActionHandler,
            {
                "name": "Financial & Cash Flow Management",
                "description": "Analyzes cash position, burn rate, runway, and financial health",
                "category": "financial",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

        self.register(
            "returns_profit@WB_CN",
            ReturnsProfitActionHandler,
            {
                "name": "Returns & Profitability Tracking",
                "description": "Analyzes return rates, root causes, and profitability impact",
                "category": "quality",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

        # Supplier & Pricing Handlers
        self.register(
            "supplier_evaluation@WB_CN",
            SupplierEvaluationActionHandler,
            {
                "name": "Supplier Evaluation & Tiering",
                "description": "Scores suppliers on performance, quality, delivery, and cost",
                "category": "procurement",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

        self.register(
            "pricing_optimization@WB_CN",
            PricingOptimizationActionHandler,
            {
                "name": "Pricing Optimization & Strategy",
                "description": "Analyzes competitive positioning and recommends optimal pricing",
                "category": "revenue",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

        # Marketing & Engagement Handlers
        self.register(
            "promotional_campaign@WB_CN",
            PromotionalCampaignActionHandler,
            {
                "name": "Promotional Campaign Management",
                "description": "Tracks campaign performance, ROI, and engagement metrics",
                "category": "marketing",
                "schedule": "daily_pipeline",
                "approval_level": "P0-2",
            },
        )

        self.register(
            "social_engagement@WB_CN",
            SocialEngagementActionHandler,
            {
                "name": "Social Media Engagement Analysis",
                "description": "Tracks social posts, engagement rates, sentiment, and content performance",
                "category": "marketing",
                "schedule": "social_watch",
                "approval_level": "P0-2",
            },
        )

        # Customer & Competitive Handlers
        self.register(
            "customer_retention@WB_CN",
            CustomerRetentionActionHandler,
            {
                "name": "Customer Retention & Loyalty",
                "description": "Analyzes customer lifecycle, churn risk, and retention strategies",
                "category": "customer_success",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

        self.register(
            "competitor_analysis@WB_CN",
            CompetitorAnalysisActionHandler,
            {
                "name": "Competitive Analysis & Intelligence",
                "description": "Tracks competitor performance and provides strategic insights",
                "category": "strategy",
                "schedule": "weekly_pipeline",
                "approval_level": "P0-2",
            },
        )

    def register(
        self,
        action_key: str,
        handler_class: Type[ActionHandler],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a handler with the registry.

        Args:
            action_key: Key in format "action_type@platform"
            handler_class: ActionHandler class to register
            metadata: Optional metadata about the handler
        """
        if not isinstance(action_key, str) or "@" not in action_key:
            raise ValueError(f"Invalid action_key format: {action_key} (must be 'action_type@platform')")

        self._registry[action_key] = handler_class
        self._handler_metadata[action_key] = metadata or {}

    def get_handler(self, action_key: str) -> Type[ActionHandler] | None:
        """Get handler class for an action key.

        Args:
            action_key: Key in format "action_type@platform"

        Returns:
            Handler class or None if not found
        """
        return self._registry.get(action_key)

    def instantiate_handler(self, action_key: str, client_id: str, data: dict[str, Any]) -> ActionHandler | None:
        """Instantiate a handler with client and data.

        Args:
            action_key: Key in format "action_type@platform"
            client_id: Client identifier
            data: Input data for handler

        Returns:
            Instantiated handler or None if handler not found
        """
        handler_class = self.get_handler(action_key)
        if not handler_class:
            return None

        # Handlers expect client_id as first arg and data dict as second
        return handler_class(client_id, data)

    def get_metadata(self, action_key: str) -> dict[str, Any]:
        """Get metadata for a handler.

        Args:
            action_key: Key in format "action_type@platform"

        Returns:
            Metadata dict
        """
        return self._handler_metadata.get(action_key, {})

    def list_handlers(self) -> list[dict[str, Any]]:
        """List all registered handlers.

        Returns:
            List of handler info dicts
        """
        result = []
        for action_key, handler_class in self._registry.items():
            metadata = self._handler_metadata.get(action_key, {})
            result.append({
                "action_key": action_key,
                "handler_class": handler_class.__name__,
                "name": metadata.get("name", action_key),
                "description": metadata.get("description", ""),
                "category": metadata.get("category", ""),
                "schedule": metadata.get("schedule", ""),
                "approval_level": metadata.get("approval_level", "P0-2"),
            })
        return result

    def list_handlers_by_schedule(self, schedule: str) -> list[str]:
        """Get all handlers for a specific schedule.

        Args:
            schedule: Schedule name (e.g., 'weekly_pipeline', 'daily_pipeline')

        Returns:
            List of action keys scheduled for this schedule
        """
        return [
            action_key
            for action_key, metadata in self._handler_metadata.items()
            if metadata.get("schedule") == schedule
        ]

    def list_handlers_by_category(self, category: str) -> list[str]:
        """Get all handlers for a specific category.

        Args:
            category: Category name (e.g., 'supply_chain', 'financial')

        Returns:
            List of action keys in this category
        """
        return [
            action_key
            for action_key, metadata in self._handler_metadata.items()
            if metadata.get("category") == category
        ]

    def to_json(self) -> str:
        """Export registry as JSON.

        Returns:
            JSON string representation of registry
        """
        return json.dumps(self.list_handlers(), indent=2)

    def save_to_file(self, filepath: str | Path) -> None:
        """Save registry to JSON file.

        Args:
            filepath: Path to save registry to
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())


# Global registry instance
_registry: ActionHandlerRegistry | None = None


def get_registry() -> ActionHandlerRegistry:
    """Get or create global ActionHandlerRegistry instance.

    Returns:
        Global ActionHandlerRegistry
    """
    global _registry
    if _registry is None:
        _registry = ActionHandlerRegistry()
    return _registry


if __name__ == "__main__":
    # Demo: List all registered handlers
    registry = get_registry()

    print("=" * 80)
    print("ACTION HANDLER REGISTRY - Registered Handlers")
    print("=" * 80)

    for handler_info in registry.list_handlers():
        print(f"\n{handler_info['name']}")
        print(f"  Action Key: {handler_info['action_key']}")
        print(f"  Handler: {handler_info['handler_class']}")
        print(f"  Category: {handler_info['category']}")
        print(f"  Schedule: {handler_info['schedule']}")
        print(f"  Description: {handler_info['description']}")

    print("\n" + "=" * 80)
    print("HANDLERS BY SCHEDULE")
    print("=" * 80)

    schedules = ["weekly_pipeline", "daily_pipeline", "social_watch"]
    for schedule in schedules:
        handlers = registry.list_handlers_by_schedule(schedule)
        print(f"\n{schedule}:")
        for handler_key in handlers:
            metadata = registry.get_metadata(handler_key)
            print(f"  - {metadata.get('name')}")

    print("\n" + "=" * 80)
    print("HANDLERS BY CATEGORY")
    print("=" * 80)

    categories = set(
        h["category"] for h in registry.list_handlers() if h["category"]
    )
    for category in sorted(categories):
        handlers = registry.list_handlers_by_category(category)
        print(f"\n{category}:")
        for handler_key in handlers:
            metadata = registry.get_metadata(handler_key)
            print(f"  - {metadata.get('name')}")
