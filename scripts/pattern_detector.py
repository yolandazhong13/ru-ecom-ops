#!/usr/bin/env python3
"""Pattern detection and analysis.

Provides:
1. Shop behavior patterns
2. Platform patterns
3. Time-based patterns
4. Anomaly clustering
"""
from __future__ import annotations

from typing import Dict, List, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Pattern:
    """Detected pattern."""
    pattern_type: str
    description: str
    frequency: int
    affected_items: List[str]
    severity: str  # low, medium, high


class PatternDetector:
    """Detects patterns in order data."""

    def __init__(self):
        """Initialize pattern detector."""
        self.patterns: List[Pattern] = []

    def detect_shop_patterns(self, orders: List[Dict[str, Any]]) -> List[Pattern]:
        """Detect shop-level patterns.

        Args:
            orders: List of orders

        Returns:
            List of patterns
        """
        shop_metrics = defaultdict(lambda: {"total": 0, "confirmed": 0, "failed": 0})

        for order in orders:
            shop_id = order.get("shop_id", "unknown")
            shop_metrics[shop_id]["total"] += 1

            if order.get("state_machine_state") == "confirmed":
                shop_metrics[shop_id]["confirmed"] += 1
            else:
                shop_metrics[shop_id]["failed"] += 1

        patterns = []

        for shop_id, metrics in shop_metrics.items():
            if metrics["total"] > 0:
                success_rate = metrics["confirmed"] / metrics["total"]

                # Low success rate pattern
                if success_rate < 0.5 and metrics["total"] >= 3:
                    patterns.append(Pattern(
                        pattern_type="low_success_rate",
                        description=f"Shop {shop_id} has {success_rate:.0%} success rate",
                        frequency=metrics["total"],
                        affected_items=[shop_id],
                        severity="high" if success_rate < 0.3 else "medium",
                    ))

        self.patterns.extend(patterns)
        return patterns

    def detect_platform_patterns(self, orders: List[Dict[str, Any]]) -> List[Pattern]:
        """Detect platform-level patterns.

        Args:
            orders: List of orders

        Returns:
            List of patterns
        """
        platform_metrics = defaultdict(lambda: {"total": 0, "unmatched": 0})

        for order in orders:
            platform = order.get("platform", "unknown")
            platform_metrics[platform]["total"] += 1

            if not order.get("matched_on_platform", True):
                platform_metrics[platform]["unmatched"] += 1

        patterns = []

        for platform, metrics in platform_metrics.items():
            if metrics["total"] > 0:
                unmatched_rate = metrics["unmatched"] / metrics["total"]

                # High unmatched rate
                if unmatched_rate > 0.1:
                    patterns.append(Pattern(
                        pattern_type="reconciliation_issues",
                        description=f"{platform} has {unmatched_rate:.0%} unmatched orders",
                        frequency=metrics["unmatched"],
                        affected_items=[platform],
                        severity="high" if unmatched_rate > 0.3 else "medium",
                    ))

        self.patterns.extend(patterns)
        return patterns

    def detect_amount_patterns(self, orders: List[Dict[str, Any]]) -> List[Pattern]:
        """Detect transaction amount patterns.

        Args:
            orders: List of orders

        Returns:
            List of patterns
        """
        amounts = [order.get("total_amount", 0) for order in orders]

        if not amounts:
            return []

        avg_amount = sum(amounts) / len(amounts)
        high_amount_count = sum(1 for a in amounts if a > avg_amount * 2)

        patterns = []

        if high_amount_count > 0:
            high_amount_pct = high_amount_count / len(amounts)

            if high_amount_pct > 0.1:
                patterns.append(Pattern(
                    pattern_type="high_value_orders",
                    description=f"{high_amount_pct:.0%} of orders are high-value (>{avg_amount*2:.0f})",
                    frequency=high_amount_count,
                    affected_items=[],
                    severity="medium",
                ))

        self.patterns.extend(patterns)
        return patterns

    def get_summary(self) -> Dict[str, Any]:
        """Get pattern summary.

        Returns:
            Summary dict
        """
        if not self.patterns:
            return {"total_patterns": 0}

        severity_count = defaultdict(int)
        pattern_types = defaultdict(int)

        for pattern in self.patterns:
            severity_count[pattern.severity] += 1
            pattern_types[pattern.pattern_type] += 1

        return {
            "total_patterns": len(self.patterns),
            "by_severity": dict(severity_count),
            "by_type": dict(pattern_types),
        }


def main() -> None:
    """Demo pattern detection."""
    print("[PatternDetector] Testing pattern detection\n")

    detector = PatternDetector()

    # Test data
    orders = [
        {"shop_id": "shop_1", "platform": "Ozon", "total_amount": 1500, "state_machine_state": "confirmed", "matched_on_platform": True},
        {"shop_id": "shop_1", "platform": "Ozon", "total_amount": 1200, "state_machine_state": "pending", "matched_on_platform": False},
        {"shop_id": "shop_1", "platform": "Ozon", "total_amount": 1800, "state_machine_state": "pending", "matched_on_platform": False},
        {"shop_id": "shop_2", "platform": "WB_CN", "total_amount": 500, "state_machine_state": "confirmed", "matched_on_platform": True},
        {"shop_id": "shop_2", "platform": "WB_CN", "total_amount": 600, "state_machine_state": "confirmed", "matched_on_platform": True},
    ]

    print("[PatternDetector] Detecting patterns...\n")

    shop_patterns = detector.detect_shop_patterns(orders)
    platform_patterns = detector.detect_platform_patterns(orders)
    amount_patterns = detector.detect_amount_patterns(orders)

    print(f"Shop patterns: {len(shop_patterns)}")
    for p in shop_patterns:
        print(f"  - {p.description} ({p.severity})")

    print(f"\nPlatform patterns: {len(platform_patterns)}")
    for p in platform_patterns:
        print(f"  - {p.description} ({p.severity})")

    print(f"\nAmount patterns: {len(amount_patterns)}")
    for p in amount_patterns:
        print(f"  - {p.description} ({p.severity})")

    summary = detector.get_summary()
    print(f"\nSummary: {summary['total_patterns']} patterns detected")
    if summary['total_patterns'] > 0:
        print(f"  By severity: {summary['by_severity']}")
        print(f"  By type: {summary['by_type']}")


if __name__ == "__main__":
    main()
