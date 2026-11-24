#!/usr/bin/env python3
"""Rate limiting for API protection.

Provides:
1. Token bucket rate limiting
2. Per-endpoint limits
3. Burst protection
4. Rate limit headers
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple
from collections import defaultdict


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 1000, burst_size: int = 100):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Allowed requests per minute
            burst_size: Burst capacity
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests_per_second = requests_per_minute / 60.0

        # Track tokens per client
        self.tokens: Dict[str, float] = defaultdict(lambda: burst_size)
        self.last_refill: Dict[str, datetime] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed.

        Args:
            client_id: Client identifier (IP, API key, etc)

        Returns:
            True if request allowed
        """
        now = datetime.now(timezone.utc)

        # Refill tokens based on elapsed time
        if client_id in self.last_refill:
            elapsed = (now - self.last_refill[client_id]).total_seconds()
            tokens_to_add = elapsed * self.requests_per_second
            self.tokens[client_id] = min(
                self.burst_size,
                self.tokens[client_id] + tokens_to_add,
            )
        else:
            self.tokens[client_id] = self.burst_size

        self.last_refill[client_id] = now

        # Deduct token if available
        if self.tokens[client_id] >= 1:
            self.tokens[client_id] -= 1
            return True

        return False

    def get_remaining_tokens(self, client_id: str) -> int:
        """Get remaining tokens for client.

        Args:
            client_id: Client identifier

        Returns:
            Number of remaining tokens
        """
        return max(0, int(self.tokens.get(client_id, 0)))

    def get_rate_limit_headers(self, client_id: str) -> Dict[str, str]:
        """Get rate limit headers for response.

        Args:
            client_id: Client identifier

        Returns:
            Headers dict
        """
        return {
            "X-RateLimit-Limit": str(int(self.requests_per_minute)),
            "X-RateLimit-Remaining": str(self.get_remaining_tokens(client_id)),
            "X-RateLimit-Reset": str(int((datetime.now(timezone.utc) + timedelta(minutes=1)).timestamp())),
        }


class PerEndpointLimiter:
    """Per-endpoint rate limiting."""

    def __init__(self):
        """Initialize per-endpoint limiter."""
        self.limiters: Dict[str, RateLimiter] = {}

    def get_limiter(self, endpoint: str, rpm: int = 1000) -> RateLimiter:
        """Get limiter for endpoint.

        Args:
            endpoint: API endpoint path
            rpm: Requests per minute limit

        Returns:
            RateLimiter instance
        """
        if endpoint not in self.limiters:
            self.limiters[endpoint] = RateLimiter(requests_per_minute=rpm)
        return self.limiters[endpoint]

    def is_allowed(self, endpoint: str, client_id: str, rpm: int = 1000) -> bool:
        """Check if request allowed for endpoint.

        Args:
            endpoint: API endpoint
            client_id: Client identifier
            rpm: Requests per minute limit

        Returns:
            True if allowed
        """
        limiter = self.get_limiter(endpoint, rpm)
        return limiter.is_allowed(client_id)

    def get_headers(self, endpoint: str, client_id: str, rpm: int = 1000) -> Dict[str, str]:
        """Get rate limit headers.

        Args:
            endpoint: API endpoint
            client_id: Client identifier
            rpm: Requests per minute limit

        Returns:
            Headers dict
        """
        limiter = self.get_limiter(endpoint, rpm)
        return limiter.get_rate_limit_headers(client_id)


def main() -> None:
    """Demo rate limiting."""
    print("[RateLimiter] Testing rate limiting\n")

    limiter = RateLimiter(requests_per_minute=10, burst_size=5)

    print("[Test 1] Basic rate limiting (10 req/min, burst 5):")
    client = "user_123"

    for i in range(12):
        allowed = limiter.is_allowed(client)
        remaining = limiter.get_remaining_tokens(client)
        status = "✓" if allowed else "✗"
        print(f"  Request {i + 1}: {status} (remaining: {remaining})")

    # Per-endpoint limiting
    print("\n[Test 2] Per-endpoint rate limiting:")
    ep_limiter = PerEndpointLimiter()

    for i in range(5):
        # API endpoints with different limits
        allowed_orders = ep_limiter.is_allowed("/api/orders", "user_123", rpm=5)
        allowed_metrics = ep_limiter.is_allowed("/api/metrics", "user_123", rpm=20)

        print(f"  Request {i + 1}:")
        print(f"    /api/orders: {'✓' if allowed_orders else '✗'}")
        print(f"    /api/metrics: {'✓' if allowed_metrics else '✗'}")

    print(f"\n✓ Rate limiting demo completed")


if __name__ == "__main__":
    main()
