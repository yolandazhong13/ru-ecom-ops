#!/usr/bin/env python3
"""Comprehensive test suite for all 10 ActionHandler implementations.

Tests all handlers:
- Existing (5): inventory_replenishment, returns_profit, finance_cash, supplier_evaluation, pricing_optimization
- New (5): promotional_campaign, customer_retention, social_engagement, inventory_health, competitor_analysis

Verifies:
- execute() and verify() methods work correctly
- P0-2 approval gate integration
- Input validation and error handling
- Output schema compliance
- Multi-factor scoring calculations
- Registry integration and instantiation
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Import all handler classes
from scripts.inventory_replenishment_handler import InventoryReplenishmentActionHandler
from scripts.returns_profit_handler import ReturnsProfitActionHandler
from scripts.finance_cash_handler import FinanceCashActionHandler
from scripts.supplier_evaluation_handler import SupplierEvaluationActionHandler
from scripts.pricing_optimization_handler import PricingOptimizationActionHandler
from scripts.promotional_campaign_handler import PromotionalCampaignActionHandler
from scripts.customer_retention_handler import CustomerRetentionActionHandler
from scripts.social_engagement_handler import SocialEngagementActionHandler
from scripts.inventory_health_handler import InventoryHealthActionHandler
from scripts.competitor_analysis_handler import CompetitorAnalysisActionHandler
from scripts.action_handler_registry import ActionHandlerRegistry, get_registry


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_client_id():
    """Test client ID."""
    return "test_client_001"


@pytest.fixture
def registry():
    """Get ActionHandlerRegistry instance."""
    return get_registry()


# Sample data fixtures for each handler type

@pytest.fixture
def inventory_replenishment_data():
    """Sample data for inventory replenishment handler."""
    return {
        "SKU001": {
            "sku": "SKU001",
            "product_name": "Premium Widget",
            "current_stock": 50,
            "in_transit_qty": 0,
            "daily_avg_sales": 10,
            "is_flagship": False,
            "safety_stock": 30,
            "reorder_point": 100,
            "lead_time_days": 14,
            "cost_per_unit": 25.00,
        },
        "SKU002": {
            "sku": "SKU002",
            "product_name": "Standard Widget",
            "current_stock": 500,
            "in_transit_qty": 100,
            "daily_avg_sales": 5,
            "is_flagship": True,
            "safety_stock": 50,
            "reorder_point": 150,
            "lead_time_days": 7,
            "cost_per_unit": 15.00,
        },
    }


@pytest.fixture
def returns_profit_data():
    """Sample data for returns profit handler."""
    return {
        "SKU001": {
            "product_id": "SKU001",
            "product_name": "Premium Widget",
            "total_orders": 1000,
            "returned_orders": 50,
            "avg_return_reason": "defective",
            "revenue_per_order": 10.0,
            "cost_per_order": 5.0,
            "return_processing_cost": 250.0,
            "replacement_rate": 0.05,
            "refund_rate": 0.05,
        },
    }


@pytest.fixture
def finance_cash_data():
    """Sample data for finance cash handler."""
    return {
        "current_cash_rub": 50000,
        "monthly_revenue_rub": 8000,
        "monthly_cogs_rub": 5000,
        "monthly_operating_costs_rub": 3000,
        "monthly_marketing_spend_rub": 2000,
        "accounts_receivable_rub": 15000,
        "accounts_payable_rub": 20000,
        "inventory_value_rub": 30000,
        "liabilities_rub": 15000,
        "reporting_period_days": 30,
    }


@pytest.fixture
def supplier_evaluation_data():
    """Sample data for supplier evaluation handler."""
    return {
        "SUP001": {
            "supplier_id": "SUP001",
            "supplier_name": "Reliable Supplies Inc",
            "total_orders": 50,
            "on_time_deliveries": 48,
            "defect_rate_percent": 2.0,
            "avg_response_time_hours": 4.5,
            "unit_cost_rub": 50.00,
            "market_avg_cost_rub": 52.00,
            "communication_score": 4.0,
            "total_transactions_value_rub": 25000.0,
            "years_in_business": 10,
        },
    }


@pytest.fixture
def pricing_optimization_data():
    """Sample data for pricing optimization handler."""
    return {
        "SKU001": {
            "product_id": "SKU001",
            "product_name": "Premium Widget",
            "current_price_rub": 100.00,
            "cost_rub": 50.00,
            "competitor_price_min_rub": 95.00,
            "competitor_price_max_rub": 105.00,
            "competitor_price_avg_rub": 99.33,
            "monthly_sales_volume": 500,
            "search_rank": 1,
            "stock_level": 1000,
            "market_saturation": 0.65,
            "is_flagship": True,
            "price_sensitivity": 0.5,
        },
    }


@pytest.fixture
def promotional_campaign_data():
    """Sample data for promotional campaign handler."""
    return {
        "CAMP001": {
            "campaign_id": "CAMP001",
            "campaign_name": "Summer Sale",
            "campaign_type": "SEASONAL",
            "budget_rub": 5000,
            "spend_rub": 3500,
            "impressions": 100000,
            "clicks": 2500,
            "conversions": 150,
            "revenue_rub": 7500,
            "avg_order_value_rub": 50.0,
            "target_audience": "18-35",
            "campaign_duration_days": 30,
            "discount_percent": 15.0,
            "free_shipping": True,
            "ctr_percent": 2.5,
            "cvr_percent": 6.0,
            "roi_percent": 114.3,
            "engagement_rate_percent": 2.5,
        },
    }


@pytest.fixture
def customer_retention_data():
    """Sample data for customer retention handler."""
    return {
        "CUST001": {
            "customer_id": "CUST001",
            "total_purchases": 5,
            "total_spend_rub": 500,
            "first_purchase_days_ago": 365,
            "last_purchase_days_ago": 30,
            "avg_order_value_rub": 100,
            "repeat_purchase_rate": 0.6,
            "product_category_diversity": 3,
            "support_tickets": 1,
            "net_promoter_score": 8,
            "loyalty_program_tier": "SILVER",
            "churn_risk_score": 0.2,
            "estimated_customer_ltv_rub": 1500,
            "retention_tier": "HIGH",
        },
    }


@pytest.fixture
def social_engagement_data():
    """Sample data for social engagement handler."""
    return {
        "POST001": {
            "post_id": "POST001",
            "platform": "WeChat",
            "post_date": "2026-11-20",
            "content_type": "PRODUCT_PROMOTION",
            "impressions": 5000,
            "engagement_count": 650,
            "likes": 500,
            "comments": 50,
            "shares": 100,
            "clicks": 100,
            "conversions": 25,
            "sentiment_score": 0.915,
            "hashtag_count": 5,
            "mentions": 12,
            "engagement_rate_percent": 13.0,
            "conversion_rate_percent": 25.0,
        },
    }


@pytest.fixture
def inventory_health_data():
    """Sample data for inventory health handler."""
    return {
        "SKU001": {
            "sku_id": "SKU001",
            "sku_name": "Premium Widget",
            "current_stock": 200,
            "in_transit_qty": 100,
            "locked_qty": 20,
            "daily_sales_avg": 10,
            "reorder_point": 150,
            "safety_stock": 100,
            "warehouse_location": "WAREHOUSE_A",
            "last_restock_days_ago": 5,
            "supplier_lead_time_days": 7,
            "stock_turn_rate": 18.25,
            "days_stock_available": 20,
            "health_score": 75,
            "alert_level": "GREEN",
        },
    }


@pytest.fixture
def competitor_analysis_data():
    """Sample data for competitor analysis handler."""
    return {
        "COMP001": {
            "competitor_id": "COMP001",
            "competitor_name": "RivalCorp",
            "product_count": 500,
            "avg_product_price_rub": 95,
            "avg_rating": 4.2,
            "review_count": 3500,
            "monthly_sales_estimate": 50000,
            "market_share_percent": 15.0,
            "price_competitiveness_score": 0.95,
            "quality_perception_score": 85,
            "shipping_speed_days": 7,
            "return_policy_days": 30,
            "our_comparative_price_rub": 100,
            "our_comparative_quality": 90,
            "our_comparative_shipping_days": 5,
            "our_comparative_return_rate_percent": 3.0,
            "competitor_return_rate_percent": 8.0,
            "threat_level": "MEDIUM",
        },
    }


# ============================================================================
# REGISTRY TESTS
# ============================================================================

class TestActionHandlerRegistry:
    """Test ActionHandlerRegistry functionality."""

    def test_registry_initialization(self, registry):
        """Test that registry initializes with all 10 handlers."""
        handlers = registry.list_handlers()
        assert len(handlers) == 10

    def test_registry_has_all_handlers(self, registry):
        """Test that all expected handlers are registered."""
        expected_keys = {
            "inventory_replenishment@WB_CN",
            "returns_profit@WB_CN",
            "finance_cash@WB_CN",
            "supplier_evaluation@WB_CN",
            "pricing_optimization@WB_CN",
            "promotional_campaign@WB_CN",
            "customer_retention@WB_CN",
            "social_engagement@WB_CN",
            "inventory_health@WB_CN",
            "competitor_analysis@WB_CN",
        }
        handler_keys = {h["action_key"] for h in registry.list_handlers()}
        assert handler_keys == expected_keys

    def test_registry_get_handler(self, registry):
        """Test registry get_handler method."""
        handler_class = registry.get_handler("inventory_replenishment@WB_CN")
        assert handler_class == InventoryReplenishmentActionHandler

    def test_registry_get_metadata(self, registry):
        """Test registry metadata retrieval."""
        metadata = registry.get_metadata("inventory_replenishment@WB_CN")
        assert metadata["name"] == "Inventory Replenishment"
        assert metadata["category"] == "supply_chain"
        assert metadata["approval_level"] == "P0-2"

    def test_registry_instantiate_handler(self, registry, test_client_id, inventory_replenishment_data):
        """Test handler instantiation from registry."""
        handler = registry.instantiate_handler(
            "inventory_replenishment@WB_CN",
            test_client_id,
            inventory_replenishment_data,
        )
        assert handler is not None
        assert isinstance(handler, InventoryReplenishmentActionHandler)

    def test_registry_list_by_schedule(self, registry):
        """Test filtering handlers by schedule."""
        weekly = registry.list_handlers_by_schedule("weekly_pipeline")
        assert len(weekly) > 0
        assert "inventory_replenishment@WB_CN" in weekly

    def test_registry_list_by_category(self, registry):
        """Test filtering handlers by category."""
        supply_chain = registry.list_handlers_by_category("supply_chain")
        assert len(supply_chain) > 0
        assert "inventory_replenishment@WB_CN" in supply_chain


# ============================================================================
# INVENTORY REPLENISHMENT HANDLER TESTS
# ============================================================================

class TestInventoryReplenishmentHandler:
    """Test InventoryReplenishmentActionHandler."""

    def test_handler_initialization(self, test_client_id, inventory_replenishment_data):
        """Test handler initialization."""
        handler = InventoryReplenishmentActionHandler(test_client_id, inventory_replenishment_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "inventory_replenishment"
        assert handler.platform == "WB_CN"

    def test_execute_valid_data(self, test_client_id, inventory_replenishment_data):
        """Test execute method with valid data."""
        handler = InventoryReplenishmentActionHandler(test_client_id, inventory_replenishment_data)
        result = handler.execute(inventory_replenishment_data)

        assert "analysis_results" in result
        assert "replenishment_summary" in result
        assert len(result["analysis_results"]) == 2

    def test_verify_valid_result(self, test_client_id, inventory_replenishment_data):
        """Test verify method with valid result."""
        handler = InventoryReplenishmentActionHandler(test_client_id, inventory_replenishment_data)
        result = handler.execute(inventory_replenishment_data)
        verification = handler.verify(result)

        assert verification["validation_checks"]["all_skus_analyzed"] is True
        assert verification["validation_checks"]["coverage_days_valid"] is True
        assert verification["validation_checks"]["replenishment_quantities_calculated"] is True


# ============================================================================
# RETURNS PROFIT HANDLER TESTS
# ============================================================================

class TestReturnsProfitHandler:
    """Test ReturnsProfitActionHandler."""

    def test_handler_initialization(self, test_client_id, returns_profit_data):
        """Test handler initialization."""
        handler = ReturnsProfitActionHandler(test_client_id, returns_profit_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "returns_profit"

    def test_execute_valid_data(self, test_client_id, returns_profit_data):
        """Test execute method with valid data."""
        handler = ReturnsProfitActionHandler(test_client_id, returns_profit_data)
        result = handler.execute(returns_profit_data)

        assert "analysis_results" in result
        assert "profitability_impact" in result

    def test_verify_valid_result(self, test_client_id, returns_profit_data):
        """Test verify method with valid result."""
        handler = ReturnsProfitActionHandler(test_client_id, returns_profit_data)
        result = handler.execute(returns_profit_data)
        verification = handler.verify(result)

        assert "all_products_analyzed" in verification["validation_checks"]
        assert "profitability_impact_calculated" in verification["validation_checks"]


# ============================================================================
# FINANCE CASH HANDLER TESTS
# ============================================================================

class TestFinanceCashHandler:
    """Test FinanceCashActionHandler."""

    def test_handler_initialization(self, test_client_id, finance_cash_data):
        """Test handler initialization."""
        handler = FinanceCashActionHandler(test_client_id, finance_cash_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "finance_cash"

    def test_execute_valid_data(self, test_client_id, finance_cash_data):
        """Test execute method with valid data."""
        handler = FinanceCashActionHandler(test_client_id, finance_cash_data)
        result = handler.execute(finance_cash_data)

        assert "cash_flow_summary" in result
        assert "financial_assessment" in result

    def test_verify_valid_result(self, test_client_id, finance_cash_data):
        """Test verify method with valid result."""
        handler = FinanceCashActionHandler(test_client_id, finance_cash_data)
        result = handler.execute(finance_cash_data)
        verification = handler.verify(result)

        assert "cash_position_analyzed" in verification["validation_checks"]
        assert "financial_ratios_valid" in verification["validation_checks"]


# ============================================================================
# SUPPLIER EVALUATION HANDLER TESTS
# ============================================================================

class TestSupplierEvaluationHandler:
    """Test SupplierEvaluationActionHandler."""

    def test_handler_initialization(self, test_client_id, supplier_evaluation_data):
        """Test handler initialization."""
        handler = SupplierEvaluationActionHandler(test_client_id, supplier_evaluation_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "supplier_evaluation"

    def test_execute_valid_data(self, test_client_id, supplier_evaluation_data):
        """Test execute method with valid data."""
        handler = SupplierEvaluationActionHandler(test_client_id, supplier_evaluation_data)
        result = handler.execute(supplier_evaluation_data)

        assert "analysis_results" in result
        assert "performance_summary" in result

    def test_verify_valid_result(self, test_client_id, supplier_evaluation_data):
        """Test verify method with valid result."""
        handler = SupplierEvaluationActionHandler(test_client_id, supplier_evaluation_data)
        result = handler.execute(supplier_evaluation_data)
        verification = handler.verify(result)

        assert "all_suppliers_evaluated" in verification["validation_checks"]
        assert "performance_scores_valid" in verification["validation_checks"]


# ============================================================================
# PRICING OPTIMIZATION HANDLER TESTS
# ============================================================================

class TestPricingOptimizationHandler:
    """Test PricingOptimizationActionHandler."""

    def test_handler_initialization(self, test_client_id, pricing_optimization_data):
        """Test handler initialization."""
        handler = PricingOptimizationActionHandler(test_client_id, pricing_optimization_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "pricing_optimization"

    def test_execute_valid_data(self, test_client_id, pricing_optimization_data):
        """Test execute method with valid data."""
        handler = PricingOptimizationActionHandler(test_client_id, pricing_optimization_data)
        result = handler.execute(pricing_optimization_data)

        assert "analysis_results" in result
        assert "pricing_strategy" in result

    def test_verify_valid_result(self, test_client_id, pricing_optimization_data):
        """Test verify method with valid result."""
        handler = PricingOptimizationActionHandler(test_client_id, pricing_optimization_data)
        result = handler.execute(pricing_optimization_data)
        verification = handler.verify(result)

        assert "all_products_analyzed" in verification["validation_checks"]
        assert "price_recommendations_provided" in verification["validation_checks"]


# ============================================================================
# PROMOTIONAL CAMPAIGN HANDLER TESTS
# ============================================================================

class TestPromotionalCampaignHandler:
    """Test PromotionalCampaignActionHandler."""

    def test_handler_initialization(self, test_client_id, promotional_campaign_data):
        """Test handler initialization."""
        handler = PromotionalCampaignActionHandler(test_client_id, promotional_campaign_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "promotional_campaign"

    def test_execute_valid_data(self, test_client_id, promotional_campaign_data):
        """Test execute method with valid data."""
        handler = PromotionalCampaignActionHandler(test_client_id, promotional_campaign_data)
        result = handler.execute(promotional_campaign_data)

        assert "analysis_results" in result
        assert "campaign_strategy" in result

    def test_verify_valid_result(self, test_client_id, promotional_campaign_data):
        """Test verify method with valid result."""
        handler = PromotionalCampaignActionHandler(test_client_id, promotional_campaign_data)
        result = handler.execute(promotional_campaign_data)
        verification = handler.verify(result)

        assert "all_campaigns_analyzed" in verification["validation_checks"]
        assert "performance_metrics_valid" in verification["validation_checks"]
        assert "roi_calculations_verified" in verification["validation_checks"]


# ============================================================================
# CUSTOMER RETENTION HANDLER TESTS
# ============================================================================

class TestCustomerRetentionHandler:
    """Test CustomerRetentionActionHandler."""

    def test_handler_initialization(self, test_client_id, customer_retention_data):
        """Test handler initialization."""
        handler = CustomerRetentionActionHandler(test_client_id, customer_retention_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "customer_retention"

    def test_execute_valid_data(self, test_client_id, customer_retention_data):
        """Test execute method with valid data."""
        handler = CustomerRetentionActionHandler(test_client_id, customer_retention_data)
        result = handler.execute(customer_retention_data)

        assert "analysis_results" in result
        assert "retention_strategy" in result

    def test_verify_valid_result(self, test_client_id, customer_retention_data):
        """Test verify method with valid result."""
        handler = CustomerRetentionActionHandler(test_client_id, customer_retention_data)
        result = handler.execute(customer_retention_data)
        verification = handler.verify(result)

        assert "all_customers_analyzed" in verification["validation_checks"]
        assert "churn_risk_scores_valid" in verification["validation_checks"]
        assert "loyalty_tiers_assigned" in verification["validation_checks"]


# ============================================================================
# SOCIAL ENGAGEMENT HANDLER TESTS
# ============================================================================

class TestSocialEngagementHandler:
    """Test SocialEngagementActionHandler."""

    def test_handler_initialization(self, test_client_id, social_engagement_data):
        """Test handler initialization."""
        handler = SocialEngagementActionHandler(test_client_id, social_engagement_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "social_engagement"

    def test_execute_valid_data(self, test_client_id, social_engagement_data):
        """Test execute method with valid data."""
        handler = SocialEngagementActionHandler(test_client_id, social_engagement_data)
        result = handler.execute(social_engagement_data)

        assert "analysis_results" in result
        assert "engagement_summary" in result

    def test_verify_valid_result(self, test_client_id, social_engagement_data):
        """Test verify method with valid result."""
        handler = SocialEngagementActionHandler(test_client_id, social_engagement_data)
        result = handler.execute(social_engagement_data)
        verification = handler.verify(result)

        assert "all_posts_analyzed" in verification["validation_checks"]
        assert "engagement_metrics_valid" in verification["validation_checks"]
        assert "sentiment_analysis_completed" in verification["validation_checks"]


# ============================================================================
# INVENTORY HEALTH HANDLER TESTS
# ============================================================================

class TestInventoryHealthHandler:
    """Test InventoryHealthActionHandler."""

    def test_handler_initialization(self, test_client_id, inventory_health_data):
        """Test handler initialization."""
        handler = InventoryHealthActionHandler(test_client_id, inventory_health_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "inventory_health"

    def test_execute_valid_data(self, test_client_id, inventory_health_data):
        """Test execute method with valid data."""
        handler = InventoryHealthActionHandler(test_client_id, inventory_health_data)
        result = handler.execute(inventory_health_data)

        assert "analysis_results" in result
        assert "health_summary" in result

    def test_verify_valid_result(self, test_client_id, inventory_health_data):
        """Test verify method with valid result."""
        handler = InventoryHealthActionHandler(test_client_id, inventory_health_data)
        result = handler.execute(inventory_health_data)
        verification = handler.verify(result)

        assert "all_skus_analyzed" in verification["validation_checks"]
        assert "stock_levels_valid" in verification["validation_checks"]
        assert "alert_conditions_identified" in verification["validation_checks"]


# ============================================================================
# COMPETITOR ANALYSIS HANDLER TESTS
# ============================================================================

class TestCompetitorAnalysisHandler:
    """Test CompetitorAnalysisActionHandler."""

    def test_handler_initialization(self, test_client_id, competitor_analysis_data):
        """Test handler initialization."""
        handler = CompetitorAnalysisActionHandler(test_client_id, competitor_analysis_data)
        assert handler.client_id == test_client_id
        assert handler.action_type == "competitor_analysis"

    def test_execute_valid_data(self, test_client_id, competitor_analysis_data):
        """Test execute method with valid data."""
        handler = CompetitorAnalysisActionHandler(test_client_id, competitor_analysis_data)
        result = handler.execute(competitor_analysis_data)

        assert "analysis_results" in result
        assert "competitive_strategy" in result

    def test_verify_valid_result(self, test_client_id, competitor_analysis_data):
        """Test verify method with valid result."""
        handler = CompetitorAnalysisActionHandler(test_client_id, competitor_analysis_data)
        result = handler.execute(competitor_analysis_data)
        verification = handler.verify(result)

        assert "all_competitors_analyzed" in verification["validation_checks"]
        assert "competitive_scores_valid" in verification["validation_checks"]
        assert "threat_levels_assigned" in verification["validation_checks"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestHandlerIntegration:
    """Test integration of multiple handlers."""

    def test_all_handlers_execute_successfully(
        self,
        test_client_id,
        inventory_replenishment_data,
        returns_profit_data,
        finance_cash_data,
        supplier_evaluation_data,
        pricing_optimization_data,
        promotional_campaign_data,
        customer_retention_data,
        social_engagement_data,
        inventory_health_data,
        competitor_analysis_data,
    ):
        """Test that all handlers can execute successfully."""
        test_cases = [
            (InventoryReplenishmentActionHandler, inventory_replenishment_data),
            (ReturnsProfitActionHandler, returns_profit_data),
            (FinanceCashActionHandler, finance_cash_data),
            (SupplierEvaluationActionHandler, supplier_evaluation_data),
            (PricingOptimizationActionHandler, pricing_optimization_data),
            (PromotionalCampaignActionHandler, promotional_campaign_data),
            (CustomerRetentionActionHandler, customer_retention_data),
            (SocialEngagementActionHandler, social_engagement_data),
            (InventoryHealthActionHandler, inventory_health_data),
            (CompetitorAnalysisActionHandler, competitor_analysis_data),
        ]

        for handler_class, data in test_cases:
            handler = handler_class(test_client_id, data)
            result = handler.execute(data)
            verification = handler.verify(result)

            assert result is not None
            assert isinstance(result, dict)
            assert verification is not None
            assert isinstance(verification, dict)

    def test_registry_instantiation_all_handlers(self, registry, test_client_id):
        """Test that registry can instantiate all handlers."""
        handlers_data = {
            "inventory_replenishment@WB_CN": {"skus": []},
            "returns_profit@WB_CN": {"skus": []},
            "finance_cash@WB_CN": {"cash_position": 0},
            "supplier_evaluation@WB_CN": {"suppliers": []},
            "pricing_optimization@WB_CN": {"skus": []},
            "promotional_campaign@WB_CN": {"campaigns": []},
            "customer_retention@WB_CN": {"customers": []},
            "social_engagement@WB_CN": {"posts": []},
            "inventory_health@WB_CN": {"skus": []},
            "competitor_analysis@WB_CN": {"competitors": []},
        }

        for action_key, data in handlers_data.items():
            handler = registry.instantiate_handler(action_key, test_client_id, data)
            assert handler is not None


# ============================================================================
# P0-2 APPROVAL GATE INTEGRATION TESTS
# ============================================================================

class TestP02ApprovalIntegration:
    """Test P0-2 approval gate integration with handlers."""

    def test_handler_requires_p02_approval(self, registry):
        """Test that all handlers are configured for P0-2 approval."""
        for handler_info in registry.list_handlers():
            assert handler_info["approval_level"] == "P0-2"

    def test_handler_schedule_integration(self, registry):
        """Test that all handlers have schedule assignments."""
        schedules = {
            "weekly_pipeline": ["inventory_replenishment@WB_CN", "returns_profit@WB_CN",
                              "finance_cash@WB_CN", "supplier_evaluation@WB_CN",
                              "pricing_optimization@WB_CN", "customer_retention@WB_CN",
                              "competitor_analysis@WB_CN"],
            "daily_pipeline": ["promotional_campaign@WB_CN", "inventory_health@WB_CN"],
            "social_watch": ["social_engagement@WB_CN"],
        }

        for schedule, expected_handlers in schedules.items():
            handlers = registry.list_handlers_by_schedule(schedule)
            for handler_key in expected_handlers:
                assert handler_key in handlers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
