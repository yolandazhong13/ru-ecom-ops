#!/usr/bin/env python3
"""Phase 9: Customer Feedback and Custom Metrics handlers (final modules)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class CustomerFeedbackHandler(ActionHandler):
    """Aggregates and analyzes customer feedback."""

    def __init__(self, client_id: str):
        """Initialize customer feedback handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.feedback_analysis = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Analyze customer feedback.

        Args:
            content: Customer feedback data

        Returns:
            Dict with feedback analysis
        """
        feedback_items = content.get("feedback", [])

        if not feedback_items:
            raise ValueError("No feedback provided")

        time.sleep(0.06)

        sentiments = {"positive": 0, "neutral": 0, "negative": 0}
        categories = {}

        for feedback in feedback_items:
            sku = feedback.get("sku")
            text = feedback.get("text", "")
            rating = feedback.get("rating", 3)
            category = feedback.get("category", "general")

            # Determine sentiment
            sentiment = "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
            sentiments[sentiment] += 1

            # Track by category
            if category not in categories:
                categories[category] = {"count": 0, "avg_rating": 0, "issues": []}

            categories[category]["count"] += 1
            categories[category]["issues"].append(text[:100])

        # Calculate averages
        for category, data in categories.items():
            data["avg_rating"] = sum(f["rating"] for f in feedback_items if f.get("category") == category) / data["count"]

        sentiment_score = ((sentiments["positive"] * 100 + sentiments["neutral"] * 50) /
                          (sentiments["positive"] + sentiments["neutral"] + sentiments["negative"] + 1))

        self.feedback_analysis = {
            "total_feedback": len(feedback_items),
            "sentiment_distribution": sentiments,
            "sentiment_score": f"{sentiment_score:.1f}/100",
            "categories": categories,
            "top_issue": max(categories.items(), key=lambda x: x[1]["count"])[0] if categories else "none",
        }

        return {
            "client_id": self.client_id,
            "feedback_analysis": self.feedback_analysis,
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify feedback analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        analysis = execution_result.get("feedback_analysis", {})

        validation_checks = {
            "feedback_analyzed": analysis.get("total_feedback", 0) > 0,
            "sentiments_calculated": "sentiment_distribution" in analysis,
            "categories_identified": len(analysis.get("categories", {})) > 0,
            "score_valid": True,
        }

        error_details = []

        try:
            score = float(analysis.get("sentiment_score", "0").split("/")[0])
            if not (0 <= score <= 100):
                validation_checks["score_valid"] = False
                error_details.append("Invalid sentiment score")
        except:
            validation_checks["score_valid"] = False
            error_details.append("Could not parse sentiment score")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_feedback_analysis" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "feedback_items": analysis.get("total_feedback", 0),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }


class CustomMetricsHandler(ActionHandler):
    """Processes custom client-specific metrics."""

    def __init__(self, client_id: str):
        """Initialize custom metrics handler.

        Args:
            client_id: Client identifier
        """
        self.client_id = str(client_id)
        self.custom_metrics = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Process custom metrics.

        Args:
            content: Custom metric definitions and data

        Returns:
            Dict with processed metrics
        """
        metrics_config = content.get("metrics", {})

        if not metrics_config:
            raise ValueError("No metrics provided")

        time.sleep(0.06)

        for metric_name, metric_data in metrics_config.items():
            metric_type = metric_data.get("type", "gauge")
            value = metric_data.get("value", 0)
            threshold = metric_data.get("threshold", None)
            unit = metric_data.get("unit", "")

            # Evaluate threshold
            status = "NORMAL"
            if threshold:
                if metric_data.get("comparison") == "greater_than":
                    status = "ALERT" if value > threshold else "NORMAL"
                elif metric_data.get("comparison") == "less_than":
                    status = "ALERT" if value < threshold else "NORMAL"

            self.custom_metrics[metric_name] = {
                "name": metric_name,
                "type": metric_type,
                "value": value,
                "unit": unit,
                "threshold": threshold,
                "status": status,
                "timestamp": metric_data.get("timestamp", ""),
            }

        return {
            "client_id": self.client_id,
            "metrics_processed": len(self.custom_metrics),
            "metrics": self.custom_metrics,
            "alert_count": sum(1 for m in self.custom_metrics.values() if m["status"] == "ALERT"),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Verify custom metrics processing.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict
        """
        metrics = execution_result.get("metrics", {})

        validation_checks = {
            "metrics_processed": len(metrics) > 0,
            "values_valid": True,
            "status_assigned": True,
        }

        error_details = []

        for metric_name, metric in metrics.items():
            if metric.get("status") not in ["NORMAL", "ALERT"]:
                validation_checks["status_assigned"] = False
                error_details.append(f"{metric_name}: invalid status")

            if metric.get("value") is None:
                validation_checks["values_valid"] = False
                error_details.append(f"{metric_name}: no value")

        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_custom_metrics" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "metrics_processed": len(metrics),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }


def main() -> None:
    """Demo Phase 9 final handlers."""
    print("[Phase 9] Testing Customer Feedback...\n")

    # Test feedback
    feedback_handler = CustomerFeedbackHandler("client_001")
    result = feedback_handler.execute({
        "feedback": [
            {"sku": "MD-700", "text": "Great product quality", "rating": 5, "category": "quality"},
            {"sku": "MD-700", "text": "Fast delivery", "rating": 4, "category": "logistics"},
            {"sku": "MD-4090", "text": "Packaging damage", "rating": 2, "category": "packaging"},
            {"sku": "MD-4090", "text": "Product as described", "rating": 3, "category": "accuracy"},
        ]
    })
    verification = feedback_handler.verify(result)

    print(f"✅ Feedback Analysis: {verification['overall_status']}")
    analysis = result.get("feedback_analysis", {})
    print(f"   Total Feedback: {analysis['total_feedback']}")
    print(f"   Sentiment Score: {analysis['sentiment_score']}")
    print(f"   Distribution: {analysis['sentiment_distribution']}")

    print(f"\n[Phase 9] Testing Custom Metrics...\n")

    # Test custom metrics
    custom_handler = CustomMetricsHandler("client_001")
    result = custom_handler.execute({
        "metrics": {
            "revenue_per_day": {"type": "gauge", "value": 50000, "unit": "RUB", "threshold": 40000, "comparison": "less_than"},
            "inventory_turnover": {"type": "gauge", "value": 2.5, "unit": "times", "threshold": 2.0, "comparison": "greater_than"},
            "customer_satisfaction": {"type": "gauge", "value": 85, "unit": "%", "threshold": 80, "comparison": "greater_than"},
        }
    })
    verification = custom_handler.verify(result)

    print(f"✅ Custom Metrics: {verification['overall_status']}")
    print(f"   Processed: {result['metrics_processed']}")
    print(f"   Alerts: {result['alert_count']}")

    for metric_name, metric in result.get("metrics", {}).items():
        print(f"\n  {metric_name}: {metric['value']} {metric['unit']} [{metric['status']}]")


if __name__ == "__main__":
    main()
