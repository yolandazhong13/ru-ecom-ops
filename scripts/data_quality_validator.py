#!/usr/bin/env python3
"""Data quality validation schemas for workflow execution outputs.

Validates execution results against JSON schemas to ensure data integrity,
consistency, and compliance with business rules.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_REPORTS_DIR = ROOT / "outputs" / "validation_reports"


class ValidationStatus(str, Enum):
    """Data validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass
class ValidationRule:
    """Single data validation rule."""
    name: str
    description: str
    field_path: str  # JSONPath to field
    rule_type: str  # "required", "type", "format", "range", "custom"
    condition: str  # Human-readable condition
    severity: str = "error"  # "error" or "warning"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of validating data against a schema."""
    schema_name: str
    data_type: str  # e.g., "execution_result", "aggregated_inventory"
    validation_status: ValidationStatus
    passed_rules: int = 0
    failed_rules: int = 0
    warnings: int = 0
    errors: list[str] = field(default_factory=list)
    warnings_list: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_rules(self) -> int:
        """Total number of validation rules."""
        return self.passed_rules + self.failed_rules

    @property
    def success_rate(self) -> float:
        """Percentage of rules that passed."""
        if self.total_rules == 0:
            return 100.0
        return (self.passed_rules / self.total_rules) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        data = asdict(self)
        data["total_rules"] = self.total_rules
        data["success_rate"] = self.success_rate
        return data


class DataQualityValidator:
    """Validates data quality across workflow execution outputs."""

    # Define validation schemas
    SCHEMAS = {
        "execution_result": [
            ValidationRule(
                name="task_id_required",
                description="task_id must be present",
                field_path="task_id",
                rule_type="required",
                condition="task_id is not empty",
            ),
            ValidationRule(
                name="action_type_required",
                description="action_type must be present",
                field_path="action_type",
                rule_type="required",
                condition="action_type in ['inventory_update', 'listing_update', 'pricing_update']",
            ),
            ValidationRule(
                name="platform_required",
                description="platform must be present",
                field_path="platform",
                rule_type="required",
                condition="platform in ['WB_CN', 'Ozon RU']",
            ),
            ValidationRule(
                name="execution_status_valid",
                description="execution_status must be valid",
                field_path="execution_status",
                rule_type="enum",
                condition="execution_status in ['executed', 'failed', 'blocked', 'awaiting_confirmation']",
            ),
            ValidationRule(
                name="p02_status_valid",
                description="p02_status must be valid",
                field_path="p02_status",
                rule_type="enum",
                condition="p02_status in ['awaiting_confirmation', 'confirmed', 'verified']",
            ),
            ValidationRule(
                name="verification_present",
                description="verification must be present for executed tasks",
                field_path="verification",
                rule_type="conditional",
                condition="if execution_status=='executed' then verification is not null",
            ),
        ],
        "inventory_aggregation": [
            ValidationRule(
                name="sku_valid",
                description="SKU must match known product list",
                field_path="sku",
                rule_type="enum",
                condition="sku in ['MD-700', 'MD-700 BLACK', 'MD-4090', 'MD-4090 PRO', 'TX-850', 'TX-850 PRO']",
            ),
            ValidationRule(
                name="quantities_non_negative",
                description="All quantities must be non-negative",
                field_path="quantities",
                rule_type="range",
                condition="available_qty >= 0, in_transit_qty >= 0, locked_qty >= 0",
            ),
            ValidationRule(
                name="row_count_stable",
                description="Row count must not decrease",
                field_path="row_count",
                rule_type="comparison",
                condition="row_count_after >= row_count_before",
            ),
            ValidationRule(
                name="columns_present",
                description="All required columns must be present",
                field_path="columns",
                rule_type="required",
                condition="columns include sku, platform, location, available_qty, in_transit_qty, locked_qty",
                severity="error",
            ),
        ],
        "listing_update": [
            ValidationRule(
                name="offer_ids_present",
                description="Offer IDs must be present",
                field_path="offer_ids",
                rule_type="required",
                condition="offer_ids list is not empty",
            ),
            ValidationRule(
                name="prices_valid",
                description="Prices must be positive numbers",
                field_path="prices",
                rule_type="type",
                condition="price > 0, old_price >= 0, min_price > 0",
            ),
            ValidationRule(
                name="verification_exists",
                description="Post-execution verification must be present",
                field_path="verification",
                rule_type="required",
                condition="verification.per_offer_verification is not null",
            ),
        ],
    }

    def __init__(self):
        """Initialize data quality validator."""
        self.results: list[ValidationResult] = []
        VALIDATION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def validate_execution_result(self, data: dict[str, Any]) -> ValidationResult:
        """Validate execution result against schema.

        Args:
            data: Execution result dict

        Returns:
            ValidationResult with pass/fail status and details
        """
        rules = self.SCHEMAS.get("execution_result", [])
        return self._validate_against_rules(data, "execution_result", "execution_result", rules)

    def validate_inventory_aggregation(self, data: dict[str, Any]) -> ValidationResult:
        """Validate inventory aggregation result against schema.

        Args:
            data: Inventory aggregation data

        Returns:
            ValidationResult with pass/fail status and details
        """
        rules = self.SCHEMAS.get("inventory_aggregation", [])
        return self._validate_against_rules(data, "inventory_aggregation", "inventory_aggregation", rules)

    def validate_listing_update(self, data: dict[str, Any]) -> ValidationResult:
        """Validate listing update result against schema.

        Args:
            data: Listing update data

        Returns:
            ValidationResult with pass/fail status and details
        """
        rules = self.SCHEMAS.get("listing_update", [])
        return self._validate_against_rules(data, "listing_update", "listing_update", rules)

    def _validate_against_rules(
        self,
        data: dict[str, Any],
        schema_name: str,
        data_type: str,
        rules: list[ValidationRule],
    ) -> ValidationResult:
        """Validate data against a set of rules.

        Args:
            data: Data to validate
            schema_name: Name of schema being used
            data_type: Type of data being validated
            rules: List of validation rules

        Returns:
            ValidationResult
        """
        result = ValidationResult(
            schema_name=schema_name,
            data_type=data_type,
            validation_status=ValidationStatus.UNKNOWN,
        )

        for rule in rules:
            try:
                passed = self._evaluate_rule(data, rule)
                if passed:
                    result.passed_rules += 1
                else:
                    result.failed_rules += 1
                    error_msg = f"{rule.name}: {rule.description}"
                    if rule.severity == "error":
                        result.errors.append(error_msg)
                    else:
                        result.warnings_list.append(error_msg)
                        result.warnings += 1
            except Exception as e:
                result.failed_rules += 1
                result.errors.append(f"{rule.name}: {str(e)}")

        # Determine overall status
        if result.failed_rules > 0:
            result.validation_status = ValidationStatus.INVALID
        elif result.warnings > 0:
            result.validation_status = ValidationStatus.WARNING
        else:
            result.validation_status = ValidationStatus.VALID

        self.results.append(result)
        return result

    def _evaluate_rule(self, data: dict[str, Any], rule: ValidationRule) -> bool:
        """Evaluate a single validation rule against data.

        Args:
            data: Data to validate
            rule: Validation rule to evaluate

        Returns:
            True if rule passes, False otherwise
        """
        if rule.rule_type == "required":
            value = self._get_field(data, rule.field_path)
            return value is not None and value != ""

        elif rule.rule_type == "enum":
            value = self._get_field(data, rule.field_path)
            # Parse allowed values from condition string
            allowed = self._parse_enum_values(rule.condition)
            return value in allowed if allowed else True

        elif rule.rule_type == "type":
            value = self._get_field(data, rule.field_path)
            # Simple type checking
            return isinstance(value, (int, float)) and value > 0

        elif rule.rule_type == "range":
            # For numeric range validation
            if "available_qty" in rule.field_path or "quantities" in rule.field_path:
                for qty_field in ["available_qty", "in_transit_qty", "locked_qty"]:
                    value = self._get_field(data, qty_field)
                    if value is not None and isinstance(value, (int, float)):
                        if value < 0:
                            return False
            return True

        elif rule.rule_type == "comparison":
            if "row_count" in rule.field_path:
                before = self._get_field(data, "row_count_before")
                after = self._get_field(data, "row_count_after")
                if before is not None and after is not None:
                    return after >= before
            return True

        elif rule.rule_type == "conditional":
            # Handle conditional rules
            if "verification" in rule.condition:
                execution_status = self._get_field(data, "execution_status")
                verification = self._get_field(data, "verification")
                if execution_status == "executed":
                    return verification is not None
            return True

        return True

    def _get_field(self, data: dict[str, Any], field_path: str) -> Any:
        """Get field value from data using dot notation path.

        Args:
            data: Data dict
            field_path: Path to field (e.g., "verification.all_valid")

        Returns:
            Field value or None
        """
        parts = field_path.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def _parse_enum_values(self, condition: str) -> list[str]:
        """Parse enum values from condition string.

        Args:
            condition: Condition string like "sku in ['MD-700', 'MD-4090']"

        Returns:
            List of allowed values
        """
        try:
            # Simple parsing for "in [...]" conditions
            if " in [" in condition:
                start = condition.index("[") + 1
                end = condition.index("]")
                values_str = condition[start:end]
                values = [v.strip().strip("'\"") for v in values_str.split(",")]
                return values
        except Exception:
            pass
        return []

    def get_validation_report(self) -> dict[str, Any]:
        """Get comprehensive validation report.

        Returns:
            Report with all validation results and summary
        """
        total_validations = len(self.results)
        valid_count = sum(1 for r in self.results if r.validation_status == ValidationStatus.VALID)
        invalid_count = sum(1 for r in self.results if r.validation_status == ValidationStatus.INVALID)
        warning_count = sum(1 for r in self.results if r.validation_status == ValidationStatus.WARNING)

        total_rules = sum(r.total_rules for r in self.results)
        total_passed = sum(r.passed_rules for r in self.results)
        total_failed = sum(r.failed_rules for r in self.results)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_validations": total_validations,
                "valid": valid_count,
                "invalid": invalid_count,
                "warning": warning_count,
                "overall_pass_rate": (valid_count / total_validations * 100) if total_validations > 0 else 0,
            },
            "rule_statistics": {
                "total_rules": total_rules,
                "passed": total_passed,
                "failed": total_failed,
                "pass_rate": (total_passed / total_rules * 100) if total_rules > 0 else 0,
            },
            "results": [r.to_dict() for r in self.results[-100:]],  # Last 100 validations
        }

    def save_validation_report(self, report_name: str = "validation_report.json") -> Path:
        """Save validation report to file.

        Args:
            report_name: Report filename

        Returns:
            Path to saved report
        """
        report_path = VALIDATION_REPORTS_DIR / report_name
        report = self.get_validation_report()

        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return report_path


def main() -> None:
    """Demo data quality validation."""
    validator = DataQualityValidator()

    print(f"[Validation] Data Quality Validator initialized")
    print(f"[Validation] Available schemas: {list(validator.SCHEMAS.keys())}")

    # Example: Validate inventory aggregation
    sample_inventory = {
        "sku": "MD-700",
        "platform": "WB_CN",
        "location": "WB_CN_Online",
        "available_qty": 131,
        "in_transit_qty": 0,
        "locked_qty": 0,
        "row_count_before": 0,
        "row_count_after": 6,
    }

    result = validator.validate_inventory_aggregation(sample_inventory)
    print(f"\n[Validation] Sample inventory validation:")
    print(f"  Schema: {result.schema_name}")
    print(f"  Status: {result.validation_status.value}")
    print(f"  Rules: {result.passed_rules} passed, {result.failed_rules} failed")
    print(f"  Pass Rate: {result.success_rate:.1f}%")

    # Example: Validate execution result
    sample_execution = {
        "task_id": "test-inventory-executor-20261120",
        "action_type": "inventory_update",
        "platform": "WB_CN",
        "execution_status": "executed",
        "p02_status": "verified",
        "verification": {"all_valid": True},
    }

    result = validator.validate_execution_result(sample_execution)
    print(f"\n[Validation] Sample execution result validation:")
    print(f"  Schema: {result.schema_name}")
    print(f"  Status: {result.validation_status.value}")
    print(f"  Rules: {result.passed_rules} passed, {result.failed_rules} failed")
    print(f"  Pass Rate: {result.success_rate:.1f}%")

    # Save report
    report_path = validator.save_validation_report()
    print(f"\n[Validation] ✓ Validation report saved: {report_path}")


if __name__ == "__main__":
    main()
