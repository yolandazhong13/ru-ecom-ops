#!/usr/bin/env python3
"""Simple input validation and sanitization."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


class ValidationError(Exception):
    """Validation error."""
    pass


class DataValidator:
    """Validates and sanitizes input data."""

    @staticmethod
    def validate_order(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order data.

        Args:
            data: Order data

        Returns:
            Validated data

        Raises:
            ValidationError if invalid
        """
        errors = []

        # Check required fields
        required_fields = ["order_id", "platform", "shop_id", "total_amount", "currency"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Field '{field}' is required")

        if errors:
            raise ValidationError("; ".join(errors))

        # Validate types and values
        if not isinstance(data["order_id"], str) or not re.match(r"^[A-Z0-9_]+$", data["order_id"]):
            raise ValidationError("order_id must be alphanumeric uppercase with underscores")

        if data["platform"] not in ["WB_CN", "Ozon"]:
            raise ValidationError("platform must be 'WB_CN' or 'Ozon'")

        if not isinstance(data["shop_id"], str) or len(data["shop_id"]) > 20:
            raise ValidationError("shop_id must be string, max 20 chars")

        if not isinstance(data["total_amount"], (int, float)) or data["total_amount"] <= 0:
            raise ValidationError("total_amount must be positive number")

        if data["currency"] not in ["RUB", "USD", "EUR"]:
            raise ValidationError("currency must be RUB, USD, or EUR")

        return data

    @staticmethod
    def validate_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate query parameters.

        Args:
            params: Query params

        Returns:
            Validated params

        Raises:
            ValidationError if invalid
        """
        validated = {}

        # Limit
        if "limit" in params:
            try:
                limit = int(params["limit"])
                if limit < 1 or limit > 1000:
                    raise ValidationError("limit must be 1-1000")
                validated["limit"] = limit
            except (ValueError, TypeError):
                raise ValidationError("limit must be integer")

        # Offset
        if "offset" in params:
            try:
                offset = int(params["offset"])
                if offset < 0:
                    raise ValidationError("offset must be >= 0")
                validated["offset"] = offset
            except (ValueError, TypeError):
                raise ValidationError("offset must be integer")

        # Sort
        if "sort" in params:
            if params["sort"] not in ["asc", "desc"]:
                raise ValidationError("sort must be 'asc' or 'desc'")
            validated["sort"] = params["sort"]

        return validated

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string.

        Args:
            value: String to sanitize

        Returns:
            Sanitized string
        """
        # Strip whitespace
        value = value.strip()
        # Remove null bytes
        value = value.replace("\x00", "")
        # Remove control characters
        value = "".join(c for c in value if ord(c) >= 32 or c in "\n\t\r")
        return value


def main() -> None:
    """Demo validation."""
    print("[DataValidator] Testing validation\n")

    validator = DataValidator()

    # Test 1: Valid order
    print("[Test 1] Valid order:")
    try:
        order = {
            "order_id": "OZ_123456",
            "platform": "Ozon",
            "shop_id": "6182781",
            "total_amount": 1500.00,
            "currency": "RUB",
        }
        validated = validator.validate_order(order)
        print(f"  ✓ Valid\n")
    except ValidationError as e:
        print(f"  ✗ {e}\n")

    # Test 2: Invalid platform
    print("[Test 2] Invalid platform:")
    try:
        order = {
            "order_id": "WB_123",
            "platform": "Invalid",
            "shop_id": "123",
            "total_amount": 1000,
            "currency": "RUB",
        }
        validator.validate_order(order)
        print(f"  ✓ Valid\n")
    except ValidationError as e:
        print(f"  ✗ {e}\n")

    # Test 3: Valid query params
    print("[Test 3] Valid query params:")
    try:
        params = {"limit": "50", "offset": "10"}
        validated = validator.validate_query_params(params)
        print(f"  ✓ Valid: {validated}\n")
    except ValidationError as e:
        print(f"  ✗ {e}\n")

    # Test 4: Invalid limit
    print("[Test 4] Invalid limit:")
    try:
        params = {"limit": "2000"}
        validator.validate_query_params(params)
        print(f"  ✓ Valid\n")
    except ValidationError as e:
        print(f"  ✗ {e}\n")

    print("✓ Validation demo completed")


if __name__ == "__main__":
    main()
