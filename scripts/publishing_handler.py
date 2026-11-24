#!/usr/bin/env python3
"""Concrete ActionHandler for publishing listings to WB_CN platform.

Implements publishing workflow with:
1. Pre-publish validation and compliance
2. Listing batch processing
3. Publishing status tracking
4. Post-publish verification
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class PublishingError(Exception):
    """Raised when publishing operations fail."""
    pass


class PublishingActionHandler(ActionHandler):
    """Handles listing publishing to WB_CN platform.

    Manages batch publishing of product listings with pre-publish validation,
    platform submission, and post-publish verification.
    """

    def __init__(
        self,
        client_id: str,
        publishing_data: dict[str, dict],
    ):
        """Initialize publishing handler.

        Args:
            client_id: WB_CN client identifier
            publishing_data: Dict mapping product_id to publishing info:
                {
                    "MD-700": {
                        "sku": "wb1xx5bipa",
                        "category": "2000",
                        "price_rub": 2500,
                        "stock_quantity": 150,
                        "ready_for_publishing": True,
                        "has_all_required_fields": True,
                        "compliance_approved": True
                    }
                }
        """
        self.client_id = str(client_id)
        self.publishing_data = publishing_data
        self.validation_results = {}
        self.publishing_status = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute listing publishing workflow.

        Args:
            content: Approval content with publishing criteria

        Returns:
            Dict with publishing results and status
        """
        # Validate publishing data
        validation_errors = []
        for product_id, product_info in self.publishing_data.items():
            errors = self._validate_publishing_input(product_id, product_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise PublishingError(f"Publishing validation failed: {validation_errors}")

        # Pre-publish checks for each product
        for product_id, product_info in self.publishing_data.items():
            check = self._perform_prepublish_check(product_id, product_info)
            self.validation_results[product_id] = check

        # Simulate publishing and track status
        self.publishing_status = self._simulate_publishing()

        return {
            "publishing_data": self.publishing_data,
            "validation_results": self.validation_results,
            "publishing_status": self.publishing_status,
            "product_count": len(self.publishing_data),
            "publishing_summary": self._summarize_publishing(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of publishing workflow.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with publishing checks
        """
        validation_checks = {
            "all_products_checked": False,
            "publishing_status_valid": False,
            "compliance_verified": False,
            "batch_submission_recorded": False,
            "post_publish_verification_enabled": False,
        }

        error_details = []

        # Check 1: All products checked
        validation_results = execution_result.get("validation_results", {})
        publishing_data = execution_result.get("publishing_data", {})
        if len(validation_results) == len(publishing_data) and len(publishing_data) > 0:
            validation_checks["all_products_checked"] = True

        # Check 2: Publishing status valid
        publishing_status = execution_result.get("publishing_status", {})
        status_values = ["submitted", "queued", "failed", "not_ready"]
        statuses_valid = all(
            validation_results[pid].get("publishing_status") in status_values
            for pid in validation_results
        )
        if statuses_valid:
            validation_checks["publishing_status_valid"] = True
        else:
            error_details.append("Invalid publishing status values")

        # Check 3: Compliance verified
        compliance_complete = True
        for product_id, check in validation_results.items():
            if not check.get("compliance_check_passed"):
                compliance_complete = False
                error_details.append(f"{product_id}: compliance check failed")
        validation_checks["compliance_verified"] = compliance_complete

        # Check 4: Batch submission recorded
        summary = execution_result.get("publishing_summary", {})
        if summary and summary.get("batch_id") and summary.get("total_submitted") >= 0:
            validation_checks["batch_submission_recorded"] = True
        else:
            error_details.append("Batch submission not recorded")

        # Check 5: Post-publish verification enabled
        if publishing_status and publishing_status.get("post_publish_check_enabled"):
            validation_checks["post_publish_verification_enabled"] = True
        else:
            error_details.append("Post-publish verification not configured")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_publishing_workflow" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "product_count": len(validation_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_publishing_input(self, product_id: str, product_info: dict[str, Any]) -> list[str]:
        """Validate publishing input for a product.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "sku": str,
            "category": str,
            "price_rub": (int, float),
            "stock_quantity": int,
            "ready_for_publishing": bool,
            "has_all_required_fields": bool,
            "compliance_approved": bool,
        }

        for field, field_type in required_fields.items():
            if field not in product_info:
                errors.append(f"{product_id}: missing required field {field}")
                continue

            value = product_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{product_id}: {field} must be {field_type}")

        # Validate ranges
        if "price_rub" in product_info:
            price = product_info["price_rub"]
            if price <= 0:
                errors.append(f"{product_id}: price_rub must be positive")

        if "stock_quantity" in product_info:
            stock = product_info["stock_quantity"]
            if stock < 0:
                errors.append(f"{product_id}: stock_quantity must be non-negative")

        return errors

    def _perform_prepublish_check(self, product_id: str, product_info: dict[str, Any]) -> dict[str, Any]:
        """Perform pre-publish checks for a product.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            Dict with pre-publish check results
        """
        checks = {
            "data_complete": False,
            "compliance_check_passed": False,
            "pricing_valid": False,
            "inventory_valid": False,
            "ready_to_publish": False,
        }

        # Check 1: Data completeness
        checks["data_complete"] = product_info.get("has_all_required_fields", False)

        # Check 2: Compliance
        checks["compliance_check_passed"] = product_info.get("compliance_approved", False)

        # Check 3: Pricing validation
        price = product_info.get("price_rub", 0)
        checks["pricing_valid"] = price > 0

        # Check 4: Inventory validation
        stock = product_info.get("stock_quantity", 0)
        checks["inventory_valid"] = stock >= 0

        # Check 5: Overall readiness
        all_checks_pass = all(checks.values())
        checks["ready_to_publish"] = all_checks_pass and product_info.get("ready_for_publishing", False)

        # Determine publishing status
        if checks["ready_to_publish"]:
            publishing_status = "submitted"
        elif checks["compliance_check_passed"]:
            publishing_status = "queued"
        elif checks["data_complete"]:
            publishing_status = "not_ready"
        else:
            publishing_status = "failed"

        return {
            "product_id": product_id,
            "sku": product_info.get("sku", product_id),
            "category": product_info.get("category", "unknown"),
            "price_rub": product_info.get("price_rub", 0),
            "stock_quantity": product_info.get("stock_quantity", 0),
            "prepublish_checks": checks,
            "publishing_status": publishing_status,
            "issues": self._identify_issues(checks, product_info),
        }

    def _identify_issues(self, checks: dict[str, bool], product_info: dict[str, Any]) -> list[str]:
        """Identify issues preventing publishing.

        Args:
            checks: Pre-publish checks dict
            product_info: Product info dict

        Returns:
            List of identified issues
        """
        issues = []

        if not checks.get("data_complete"):
            issues.append("Missing required listing fields")

        if not checks.get("compliance_check_passed"):
            issues.append("Compliance approval pending")

        if not checks.get("pricing_valid"):
            issues.append("Invalid pricing configuration")

        if not checks.get("inventory_valid"):
            issues.append("Invalid inventory quantity")

        if not product_info.get("ready_for_publishing"):
            issues.append("Product not marked ready for publishing")

        return issues

    def _simulate_publishing(self) -> dict[str, Any]:
        """Simulate publishing batch submission.

        Returns:
            Dict with publishing batch status
        """
        # Count products by status
        submitted_count = sum(
            1 for v in self.validation_results.values()
            if v.get("publishing_status") == "submitted"
        )
        queued_count = sum(
            1 for v in self.validation_results.values()
            if v.get("publishing_status") == "queued"
        )
        not_ready_count = sum(
            1 for v in self.validation_results.values()
            if v.get("publishing_status") == "not_ready"
        )
        failed_count = sum(
            1 for v in self.validation_results.values()
            if v.get("publishing_status") == "failed"
        )

        # Generate batch ID
        import hashlib
        batch_seed = json.dumps(self.publishing_data, sort_keys=True).encode()
        batch_id = "batch_" + hashlib.sha256(batch_seed).hexdigest()[:12]

        return {
            "batch_id": batch_id,
            "total_submitted": submitted_count,
            "total_queued": queued_count,
            "total_not_ready": not_ready_count,
            "total_failed": failed_count,
            "batch_status": "ready_for_submission" if submitted_count > 0 else "pending_resolution",
            "post_publish_check_enabled": True,
            "submission_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_publishing(self) -> dict[str, Any]:
        """Summarize publishing workflow insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.validation_results:
            return {"total_products": 0}

        summary = self.publishing_status
        total = len(self.validation_results)
        ready_rate = (summary.get("total_submitted", 0) / total * 100) if total > 0 else 0

        # Identify blocking issues
        blocking_issues = {}
        for product_id, check in self.validation_results.items():
            issues = check.get("issues", [])
            for issue in issues:
                blocking_issues[issue] = blocking_issues.get(issue, 0) + 1

        return {
            "total_products": total,
            "ready_to_publish": summary.get("total_submitted", 0),
            "queued_for_review": summary.get("total_queued", 0),
            "not_ready": summary.get("total_not_ready", 0),
            "failed_validation": summary.get("total_failed", 0),
            "readiness_rate": round(ready_rate, 1),
            "batch_id": summary.get("batch_id"),
            "blocking_issues_summary": blocking_issues,
        }
