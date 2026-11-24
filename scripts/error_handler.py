#!/usr/bin/env python3
"""Error handling with retry logic and fallbacks.

Provides:
1. Automatic retries with exponential backoff
2. Error classification
3. Graceful degradation
4. Circuit breaker pattern
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar, Optional, Any
from datetime import datetime, timezone, timedelta
from enum import Enum

T = TypeVar("T")


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    TRANSIENT = "transient"  # Retry
    PERMANENT = "permanent"  # Don't retry
    DEGRADED = "degraded"  # Try fallback


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
    ):
        """Initialize retry config.

        Args:
            max_retries: Maximum retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            timeout_seconds: Time before attempting reset
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False

    def call(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result or None if circuit open
        """
        # Check if circuit should be reset
        if self.is_open:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed > self.timeout_seconds:
                    print(f"[CircuitBreaker] Attempting reset after {elapsed:.0f}s")
                    self.is_open = False
                    self.failures = 0
                else:
                    print(f"[CircuitBreaker] Circuit open, failing fast")
                    return None

        try:
            result = func(*args, **kwargs)
            self.failures = 0  # Reset on success
            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.failures >= self.failure_threshold:
                self.is_open = True
                print(f"[CircuitBreaker] Opening circuit after {self.failures} failures")

            raise


def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig = RetryConfig(),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """Execute function with retry logic.

    Args:
        func: Function to execute
        config: Retry configuration
        on_retry: Callback on retry attempt

    Returns:
        Function result

    Raises:
        Last exception if all retries exhausted
    """
    delay = config.initial_delay
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            return func()

        except Exception as e:
            last_exception = e

            if attempt < config.max_retries:
                if on_retry:
                    on_retry(attempt + 1, e)

                print(f"[Retry] Attempt {attempt + 1}/{config.max_retries}, waiting {delay:.1f}s")
                time.sleep(delay)
                delay = min(delay * config.multiplier, config.max_delay)
            else:
                print(f"[Retry] Max retries exceeded")

    raise last_exception


class ErrorHandler:
    """Comprehensive error handling."""

    def __init__(self):
        """Initialize error handler."""
        self.errors_seen = 0
        self.circuit_breakers = {}

    def classify_error(self, exception: Exception) -> ErrorSeverity:
        """Classify error for retry decision.

        Args:
            exception: Exception to classify

        Returns:
            Error severity
        """
        error_msg = str(exception).lower()

        # Transient errors (should retry)
        transient_keywords = [
            "timeout",
            "connection",
            "temporary",
            "unavailable",
            "try again",
        ]
        if any(keyword in error_msg for keyword in transient_keywords):
            return ErrorSeverity.TRANSIENT

        # Permanent errors (don't retry)
        permanent_keywords = [
            "not found",
            "invalid",
            "forbidden",
            "unauthorized",
            "syntax",
        ]
        if any(keyword in error_msg for keyword in permanent_keywords):
            return ErrorSeverity.PERMANENT

        # Degraded (try fallback)
        return ErrorSeverity.DEGRADED

    def handle_with_retry(
        self,
        func: Callable[..., T],
        fallback: Optional[Callable[..., T]] = None,
    ) -> Optional[T]:
        """Handle function execution with retry and fallback.

        Args:
            func: Primary function
            fallback: Fallback function if primary fails

        Returns:
            Result from primary or fallback, or None
        """
        config = RetryConfig()

        try:
            return retry_with_backoff(func, config)

        except Exception as e:
            self.errors_seen += 1
            severity = self.classify_error(e)

            print(f"[ErrorHandler] {severity.value}: {str(e)}")

            if severity == ErrorSeverity.TRANSIENT:
                print(f"[ErrorHandler] Transient error - no fallback available")
                return None

            elif fallback:
                print(f"[ErrorHandler] Trying fallback")
                try:
                    return fallback()
                except Exception as fallback_error:
                    print(f"[ErrorHandler] Fallback also failed: {fallback_error}")
                    return None

            return None

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker.

        Args:
            name: Circuit breaker name

        Returns:
            CircuitBreaker instance
        """
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker()
        return self.circuit_breakers[name]


def main() -> None:
    """Demo error handling."""
    print("[ErrorHandler] Testing error handling\n")

    handler = ErrorHandler()

    # Test 1: Successful retry
    print("[Test 1] Function that succeeds on retry:")
    attempt_count = [0]

    def flaky_function():
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise ConnectionError("Network timeout")
        return "Success!"

    result = handler.handle_with_retry(flaky_function)
    print(f"  Result: {result}\n")

    # Test 2: Permanent error
    print("[Test 2] Permanent error (no retry):")

    def invalid_request():
        raise ValueError("Invalid order ID format")

    result = handler.handle_with_retry(invalid_request)
    print(f"  Result: {result}\n")

    # Test 3: Circuit breaker
    print("[Test 3] Circuit breaker:")
    circuit = handler.get_circuit_breaker("api")

    def failing_api():
        raise Exception("API unavailable")

    for i in range(7):
        result = circuit.call(failing_api)
        if result is None:
            print(f"  Call {i + 1}: Failed (circuit handling)")

    print(f"\n✓ Error handling demo completed")
    print(f"✓ Total errors seen: {handler.errors_seen}")


if __name__ == "__main__":
    main()
