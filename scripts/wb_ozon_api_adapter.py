#!/usr/bin/env python3
"""Unified WB and Ozon API adapter for order data retrieval.

Abstracts platform-specific API differences and provides a common interface
for fetching orders, order details, and tracking information from both
Wildberries (WB) and Ozon platforms.

Supported operations:
1. Fetch active orders with state and tracking info
2. Fetch order details (items, amounts, timestamps)
3. Fetch shipping/delivery status
4. Fetch payment confirmation status
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List
import hashlib

ROOT = Path(__file__).resolve().parents[1]


class PlatformType(str, Enum):
    """Supported e-commerce platforms."""
    WB_CN = "WB_CN"
    OZON = "Ozon"


class OrderRetrievalStatus(str, Enum):
    """Status of order data retrieval operation."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    API_UNAVAILABLE = "api_unavailable"
    RATE_LIMITED = "rate_limited"


@dataclass
class PlatformOrderData:
    """Unified order data structure from platform API."""
    order_id: str
    platform: str
    shop_id: str

    # Order timing
    order_date: str  # ISO timestamp
    payment_date: Optional[str] = None
    shipped_date: Optional[str] = None
    delivery_date: Optional[str] = None

    # Order amount and SKU
    total_amount: float = 0.0
    currency: str = "RUB"
    sku: Optional[str] = None
    items: List[dict[str, Any]] = field(default_factory=list)

    # Order state from platform (may differ from state machine)
    platform_state: str = ""

    # Tracking info
    tracking_number: Optional[str] = None
    shipping_provider: Optional[str] = None

    # Payment and delivery confirmation
    payment_confirmed: bool = False
    delivered: bool = False
    signature_confirmed: bool = False

    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    api_response_hash: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class APIRetrievalResult:
    """Result of API data retrieval operation."""
    platform: str
    shop_id: str
    status: OrderRetrievalStatus
    orders_retrieved: int = 0
    orders_failed: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: Optional[str] = None
    duration_ms: int = 0
    rate_limit_remaining: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


class PlatformAPIAdapter(ABC):
    """Abstract base class for platform-specific API adapters."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with platform API."""
        pass

    @abstractmethod
    def fetch_active_orders(self, limit: int = 100) -> tuple[List[PlatformOrderData], Optional[str]]:
        """Fetch active orders from platform.

        Args:
            limit: Maximum number of orders to fetch

        Returns:
            Tuple of (orders list, error message if any)
        """
        pass

    @abstractmethod
    def fetch_order_detail(self, order_id: str) -> tuple[Optional[PlatformOrderData], Optional[str]]:
        """Fetch detailed information for a specific order.

        Args:
            order_id: Platform-specific order ID

        Returns:
            Tuple of (order data, error message if any)
        """
        pass

    @abstractmethod
    def fetch_tracking_info(self, order_id: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Fetch tracking and delivery status for an order.

        Args:
            order_id: Platform-specific order ID

        Returns:
            Tuple of (tracking data, error message if any)
        """
        pass


class WBAPIAdapter(PlatformAPIAdapter):
    """Wildberries (WB) API adapter."""

    def __init__(self, api_key: Optional[str] = None, shop_id: str = "250146669"):
        """Initialize WB API adapter.

        Args:
            api_key: WB API authentication key
            shop_id: Shop ID for WB (default: 250146669)
        """
        self.api_key = api_key or self._load_api_key("WB")
        self.shop_id = shop_id
        self.authenticated = False
        self.base_url = "https://api.wildberries.ru"
        self.rate_limit_remaining = None

    def _load_api_key(self, platform: str) -> Optional[str]:
        """Load API key from config file or environment."""
        config_file = ROOT / ".wb_config"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
                return config.get("api_key")
            except Exception:
                pass
        return None

    def authenticate(self) -> bool:
        """Authenticate with WB API.

        Returns:
            True if authentication successful
        """
        if self.api_key:
            self.authenticated = True
            return True
        return False

    def fetch_active_orders(self, limit: int = 100) -> tuple[List[PlatformOrderData], Optional[str]]:
        """Fetch active orders from WB.

        In production, this would call: /api/v3/orders (WB API endpoint)
        Status filter: 0 (new), 1 (waiting for approval), 2 (confirmed), etc.
        """
        if not self.authenticated:
            return [], "Not authenticated with WB"

        # Mock implementation - in production would call actual WB API
        # WB endpoint: GET /api/v3/orders?limit={limit}&status=0,1,2
        orders = []

        # Example: Mock orders from WB
        mock_orders = [
            {
                "id": "WB_12345678",
                "created_at": "2026-11-23T10:00:00+00:00",
                "total_price": 1500.0,
                "status": "new",
                "items": [{"sku": "SKU-001", "quantity": 1}],
            },
            {
                "id": "WB_12345679",
                "created_at": "2026-11-23T11:30:00+00:00",
                "total_price": 2500.0,
                "status": "confirmed",
                "items": [{"sku": "SKU-002", "quantity": 2}],
                "tracking": "ABC123456789",
            },
        ]

        for order_data in mock_orders[:limit]:
            orders.append(PlatformOrderData(
                order_id=order_data["id"],
                platform=PlatformType.WB_CN.value,
                shop_id=self.shop_id,
                order_date=order_data["created_at"],
                total_amount=order_data["total_price"],
                currency="RUB",
                sku=order_data["items"][0]["sku"] if order_data["items"] else None,
                items=order_data["items"],
                platform_state=order_data["status"],
                tracking_number=order_data.get("tracking"),
            ))

        return orders, None

    def fetch_order_detail(self, order_id: str) -> tuple[Optional[PlatformOrderData], Optional[str]]:
        """Fetch detailed order information from WB.

        WB endpoint: GET /api/v3/orders/{orderId}
        """
        if not self.authenticated:
            return None, "Not authenticated with WB"

        # Mock implementation
        mock_detail = {
            "id": order_id,
            "created_at": "2026-11-23T10:00:00+00:00",
            "paid_at": "2026-11-23T10:05:00+00:00",
            "total_price": 1500.0,
            "status": "confirmed",
            "items": [
                {"sku": "SKU-001", "quantity": 1, "price": 1500.0}
            ],
        }

        order = PlatformOrderData(
            order_id=mock_detail["id"],
            platform=PlatformType.WB_CN.value,
            shop_id=self.shop_id,
            order_date=mock_detail["created_at"],
            payment_date=mock_detail.get("paid_at"),
            total_amount=mock_detail["total_price"],
            currency="RUB",
            sku=mock_detail["items"][0]["sku"] if mock_detail["items"] else None,
            items=mock_detail["items"],
            platform_state=mock_detail["status"],
            payment_confirmed=bool(mock_detail.get("paid_at")),
        )

        return order, None

    def fetch_tracking_info(self, order_id: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Fetch tracking info from WB.

        WB endpoint: GET /api/v3/orders/{orderId}/tracking
        """
        if not self.authenticated:
            return None, "Not authenticated with WB"

        # Mock implementation
        tracking = {
            "tracking_number": "ABC123456789",
            "status": "in_transit",
            "last_checkpoint": "2026-11-23T15:00:00+00:00",
            "estimated_delivery": "2026-11-25T23:59:59+00:00",
        }

        return tracking, None


class OzonAPIAdapter(PlatformAPIAdapter):
    """Ozon API adapter."""

    def __init__(self, api_key: Optional[str] = None, client_id: str = "6182781"):
        """Initialize Ozon API adapter.

        Args:
            api_key: Ozon API authentication key
            client_id: Ozon Client ID (default: 6182781)
        """
        self.api_key = api_key or self._load_api_key("Ozon")
        self.client_id = client_id
        self.authenticated = False
        self.base_url = "https://api.ozon.ru"
        self.rate_limit_remaining = None

    def _load_api_key(self, platform: str) -> Optional[str]:
        """Load API key from config file or environment."""
        config_file = ROOT / ".ozon_config"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
                return config.get("api_key")
            except Exception:
                pass
        return None

    def authenticate(self) -> bool:
        """Authenticate with Ozon API.

        Returns:
            True if authentication successful
        """
        if self.api_key:
            self.authenticated = True
            return True
        return False

    def fetch_active_orders(self, limit: int = 100) -> tuple[List[PlatformOrderData], Optional[str]]:
        """Fetch active orders from Ozon.

        Ozon endpoint: POST /v1/orders/list
        Filter: status IN ["new", "awaiting_approval", "awaiting_payment"]
        """
        if not self.authenticated:
            return [], "Not authenticated with Ozon"

        # Mock implementation - in production would call actual Ozon API
        orders = []

        # Example: Mock orders from Ozon
        mock_orders = [
            {
                "order_id": "OZON_87654321",
                "created_at": "2026-11-23T09:30:00+00:00",
                "price": 2000.0,
                "status": "awaiting_approval",
                "items": [{"sku": "SKU-003"}],
            },
            {
                "order_id": "OZON_87654322",
                "created_at": "2026-11-23T12:00:00+00:00",
                "price": 3000.0,
                "status": "awaiting_payment",
                "items": [{"sku": "SKU-004"}],
            },
        ]

        for order_data in mock_orders[:limit]:
            orders.append(PlatformOrderData(
                order_id=order_data["order_id"],
                platform=PlatformType.OZON.value,
                shop_id=self.client_id,
                order_date=order_data["created_at"],
                total_amount=order_data["price"],
                currency="RUB",
                sku=order_data["items"][0]["sku"] if order_data["items"] else None,
                items=order_data["items"],
                platform_state=order_data["status"],
            ))

        return orders, None

    def fetch_order_detail(self, order_id: str) -> tuple[Optional[PlatformOrderData], Optional[str]]:
        """Fetch detailed order information from Ozon.

        Ozon endpoint: POST /v1/orders/detail
        """
        if not self.authenticated:
            return None, "Not authenticated with Ozon"

        # Mock implementation
        mock_detail = {
            "order_id": order_id,
            "created_at": "2026-11-23T09:30:00+00:00",
            "paid_at": None,  # Not paid yet
            "total_price": 2000.0,
            "status": "awaiting_payment",
            "items": [
                {"sku": "SKU-003", "quantity": 1, "price": 2000.0}
            ],
        }

        order = PlatformOrderData(
            order_id=mock_detail["order_id"],
            platform=PlatformType.OZON.value,
            shop_id=self.client_id,
            order_date=mock_detail["created_at"],
            payment_date=mock_detail.get("paid_at"),
            total_amount=mock_detail["total_price"],
            currency="RUB",
            sku=mock_detail["items"][0]["sku"] if mock_detail["items"] else None,
            items=mock_detail["items"],
            platform_state=mock_detail["status"],
            payment_confirmed=bool(mock_detail.get("paid_at")),
        )

        return order, None

    def fetch_tracking_info(self, order_id: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Fetch tracking info from Ozon.

        Ozon endpoint: POST /v1/orders/detail
        """
        if not self.authenticated:
            return None, "Not authenticated with Ozon"

        # Mock implementation
        tracking = {
            "tracking_number": "OZON_TRK_987654321",
            "status": "new",
            "last_checkpoint": None,
            "estimated_delivery": "2026-11-26T23:59:59+00:00",
        }

        return tracking, None


class UnifiedAPIGateway:
    """Unified gateway managing multiple platform adapters."""

    def __init__(self):
        """Initialize unified API gateway."""
        self.adapters: dict[str, PlatformAPIAdapter] = {}
        self.retrieval_history: list[APIRetrievalResult] = []
        self._initialize_adapters()

    def _initialize_adapters(self) -> None:
        """Initialize all platform adapters."""
        # Initialize WB adapters for both shops
        self.adapters["WB_CN_250146669_1"] = WBAPIAdapter(shop_id="250146669")
        self.adapters["WB_CN_250146669_2"] = WBAPIAdapter(shop_id="250146669")

        # Initialize Ozon adapters
        self.adapters["Ozon_6182781"] = OzonAPIAdapter(client_id="6182781")
        self.adapters["Ozon_3521307"] = OzonAPIAdapter(client_id="3521307")

    def authenticate_all(self) -> dict[str, bool]:
        """Attempt authentication with all platform adapters.

        Returns:
            Dict mapping adapter name to authentication status
        """
        results = {}
        for name, adapter in self.adapters.items():
            results[name] = adapter.authenticate()
        return results

    def fetch_all_orders(self) -> dict[str, List[PlatformOrderData]]:
        """Fetch active orders from all platforms.

        Returns:
            Dict mapping platform/shop to orders list
        """
        all_orders = {}

        for adapter_name, adapter in self.adapters.items():
            start_time = time.time()
            orders, error = adapter.fetch_active_orders()
            duration_ms = int((time.time() - start_time) * 1000)

            platform, shop_id = self._parse_adapter_name(adapter_name)

            if error:
                result = APIRetrievalResult(
                    platform=platform,
                    shop_id=shop_id,
                    status=OrderRetrievalStatus.FAILED,
                    error_message=error,
                    duration_ms=duration_ms,
                )
            else:
                result = APIRetrievalResult(
                    platform=platform,
                    shop_id=shop_id,
                    status=OrderRetrievalStatus.SUCCESS if orders else OrderRetrievalStatus.PARTIAL,
                    orders_retrieved=len(orders),
                    duration_ms=duration_ms,
                )

            self.retrieval_history.append(result)
            all_orders[adapter_name] = orders

        return all_orders

    def _parse_adapter_name(self, adapter_name: str) -> tuple[str, str]:
        """Parse adapter name to extract platform and shop_id.

        Format examples: "WB_CN_250146669_1", "Ozon_6182781"
        """
        parts = adapter_name.split("_")
        if parts[0] == "WB":
            platform = "WB_CN"
            shop_id = parts[2]
        else:
            platform = parts[0]
            shop_id = parts[1]

        return platform, shop_id

    def get_retrieval_summary(self) -> dict[str, Any]:
        """Get summary of recent API retrieval operations.

        Returns:
            Summary with success/failure counts and timing
        """
        if not self.retrieval_history:
            return {
                "total_operations": 0,
                "successful": 0,
                "failed": 0,
                "partial": 0,
                "total_orders_retrieved": 0,
            }

        total_ops = len(self.retrieval_history)
        successful = sum(1 for r in self.retrieval_history if r.status == OrderRetrievalStatus.SUCCESS)
        failed = sum(1 for r in self.retrieval_history if r.status == OrderRetrievalStatus.FAILED)
        partial = sum(1 for r in self.retrieval_history if r.status == OrderRetrievalStatus.PARTIAL)
        total_orders = sum(r.orders_retrieved for r in self.retrieval_history)

        return {
            "total_operations": total_ops,
            "successful": successful,
            "failed": failed,
            "partial": partial,
            "total_orders_retrieved": total_orders,
            "average_duration_ms": sum(r.duration_ms for r in self.retrieval_history) / total_ops if total_ops > 0 else 0,
        }


def main() -> None:
    """Demo unified API gateway usage."""
    print("[APIAdapter] Testing Unified WB/Ozon API Gateway\n")

    gateway = UnifiedAPIGateway()

    # Authenticate with all platforms
    print("[APIAdapter] Authenticating with all platforms...")
    auth_results = gateway.authenticate_all()
    for adapter_name, authenticated in auth_results.items():
        status = "✓" if authenticated else "✗"
        print(f"  {status} {adapter_name}")

    # Fetch orders from all platforms
    print(f"\n[APIAdapter] Fetching orders from all platforms...")
    all_orders = gateway.fetch_all_orders()

    total_orders = sum(len(orders) for orders in all_orders.values())
    print(f"  Total orders retrieved: {total_orders}")

    for adapter_name, orders in all_orders.items():
        if orders:
            print(f"\n[APIAdapter] Orders from {adapter_name}:")
            for order in orders:
                print(f"  - {order.order_id}: {order.total_amount} {order.currency} "
                      f"(state: {order.platform_state})")

    # Display retrieval summary
    print(f"\n[APIAdapter] Retrieval Summary:")
    summary = gateway.get_retrieval_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}")
        else:
            print(f"  {key}: {value}")

    print(f"\n[APIAdapter] ✓ Unified API Gateway initialized successfully")


if __name__ == "__main__":
    main()
