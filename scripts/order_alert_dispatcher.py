#!/usr/bin/env python3
"""Order alert dispatcher for real-time anomaly notifications.

Integrates with Feishu to send alerts based on anomaly severity:
- P0 (Immediate): Critical alerts for payment overdue, missing orders
- P1 (Hourly): Warning alerts for delays, refusals
- P2 (Daily): Info alerts for minor discrepancies

Batches alerts by shop and severity for efficient delivery.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List
from enum import Enum

# Import project modules
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_anomaly_detector import (
    OrderAnomalyDetector,
    AnomalyRecord,
    AnomalyCategory,
    AnomalyDetectionResult,
)
from order_state_machine import SeverityLevel, AnomalyType
from feishu_integration import FeishuIntegration, FeishuAlertFormatter


@dataclass
class AlertDispatchLog:
    """Log entry for dispatched alert."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    alert_type: str = ""
    severity: str = ""
    recipient_count: int = 0
    anomalies_included: int = 0
    success: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class DispatchResult:
    """Result of alert dispatch operation."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_anomalies_processed: int = 0
    alerts_dispatched: int = 0
    alerts_failed: int = 0
    alerts_skipped: int = 0
    dispatch_logs: List[AlertDispatchLog] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "total_anomalies_processed": self.total_anomalies_processed,
            "alerts_dispatched": self.alerts_dispatched,
            "alerts_failed": self.alerts_failed,
            "alerts_skipped": self.alerts_skipped,
            "dispatch_logs": [log.to_dict() for log in self.dispatch_logs],
        }


class OrderAlertDispatcher:
    """Dispatches alerts based on detected anomalies."""

    def __init__(self, feishu_webhook_url: Optional[str] = None):
        """Initialize alert dispatcher.

        Args:
            feishu_webhook_url: Feishu webhook URL (optional)
        """
        self.feishu = FeishuIntegration(feishu_webhook_url)
        self.detector = OrderAnomalyDetector()
        self.dispatch_result = None

    def dispatch_alerts(self) -> DispatchResult:
        """Detect anomalies and dispatch alerts.

        Returns:
            DispatchResult with dispatch logs
        """
        result = DispatchResult()

        # Detect anomalies
        print("[AlertDispatcher] Detecting anomalies...")
        detection_result = self.detector.detect_anomalies()
        result.total_anomalies_processed = detection_result.total_anomalies_detected

        if not detection_result.anomalies:
            print("[AlertDispatcher] No anomalies detected")
            self.dispatch_result = result
            return result

        # Group anomalies by severity and shop
        p0_anomalies = [
            a for a in detection_result.anomalies
            if a.severity == SeverityLevel.P0_IMMEDIATE
        ]
        p1_anomalies = [
            a for a in detection_result.anomalies
            if a.severity == SeverityLevel.P1_HOURLY
        ]
        p2_anomalies = [
            a for a in detection_result.anomalies
            if a.severity == SeverityLevel.P2_DAILY
        ]

        # Dispatch P0 alerts (immediate)
        if p0_anomalies:
            success = self._dispatch_critical_alerts(p0_anomalies, result)
            if success:
                result.alerts_dispatched += 1
            else:
                result.alerts_failed += 1

        # Dispatch P1 alerts (hourly batch)
        if p1_anomalies:
            success = self._dispatch_warning_alerts(p1_anomalies, result)
            if success:
                result.alerts_dispatched += 1
            else:
                result.alerts_failed += 1

        # Dispatch P2 alerts (daily batch)
        if p2_anomalies:
            success = self._dispatch_info_alerts(p2_anomalies, result)
            if success:
                result.alerts_dispatched += 1
            else:
                result.alerts_failed += 1

        self.dispatch_result = result
        return result

    def _dispatch_critical_alerts(
        self,
        anomalies: List[AnomalyRecord],
        result: DispatchResult,
    ) -> bool:
        """Dispatch P0 (critical) alerts for each anomaly.

        Args:
            anomalies: List of P0 anomalies
            result: DispatchResult to update

        Returns:
            True if dispatched successfully
        """
        for anomaly in anomalies:
            try:
                title = f"{anomaly.anomaly_type.value.upper()}: {anomaly.order_id}"
                description = anomaly.description
                component = f"order_tracker@{anomaly.platform}"
                context = {
                    "order_id": anomaly.order_id,
                    "shop_id": anomaly.shop_id,
                    "platform": anomaly.platform,
                    "current_state": anomaly.current_state,
                    "anomaly_type": anomaly.anomaly_type.value,
                    "category": anomaly.category.value,
                    **anomaly.metadata,
                }

                success = self.feishu.send_critical_alert(
                    title=title,
                    description=description,
                    component=component,
                    context=context,
                )

                log = AlertDispatchLog(
                    alert_type="critical",
                    severity=SeverityLevel.P0_IMMEDIATE.value,
                    recipient_count=1,
                    anomalies_included=1,
                    success=success,
                )
                result.dispatch_logs.append(log)

                if success:
                    print(f"[AlertDispatcher] ✓ Critical alert sent for {anomaly.order_id}")
                else:
                    print(f"[AlertDispatcher] ✗ Failed to send critical alert for {anomaly.order_id}")

            except Exception as e:
                log = AlertDispatchLog(
                    alert_type="critical",
                    severity=SeverityLevel.P0_IMMEDIATE.value,
                    recipient_count=0,
                    anomalies_included=1,
                    success=False,
                    error_message=str(e),
                )
                result.dispatch_logs.append(log)
                print(f"[AlertDispatcher] ✗ Error dispatching critical alert: {e}")

        return len([l for l in result.dispatch_logs if l.success and l.severity == SeverityLevel.P0_IMMEDIATE.value]) > 0

    def _dispatch_warning_alerts(
        self,
        anomalies: List[AnomalyRecord],
        result: DispatchResult,
    ) -> bool:
        """Dispatch P1 (warning) alerts in batch.

        Args:
            anomalies: List of P1 anomalies
            result: DispatchResult to update

        Returns:
            True if dispatched successfully
        """
        try:
            # Group by shop for context
            by_shop = {}
            for anomaly in anomalies:
                if anomaly.shop_id not in by_shop:
                    by_shop[anomaly.shop_id] = []
                by_shop[anomaly.shop_id].append(anomaly)

            # Send per-shop batch alerts
            for shop_id, shop_anomalies in by_shop.items():
                title = f"Order Anomalies Detected: {shop_id}"
                description = f"{len(shop_anomalies)} warning-level anomalies detected\n"
                description += "\n".join([
                    f"  • {a.order_id}: {a.anomaly_type.value}"
                    for a in shop_anomalies[:5]
                ])
                if len(shop_anomalies) > 5:
                    description += f"\n  ... and {len(shop_anomalies) - 5} more"

                context = {
                    "shop_id": shop_id,
                    "anomaly_count": len(shop_anomalies),
                    "anomaly_types": list(set(a.anomaly_type.value for a in shop_anomalies)),
                    "platforms": list(set(a.platform for a in shop_anomalies)),
                }

                success = self.feishu.send_warning_alert(
                    title=title,
                    description=description,
                    component="order_tracker",
                    context=context,
                )

                log = AlertDispatchLog(
                    alert_type="warning",
                    severity=SeverityLevel.P1_HOURLY.value,
                    recipient_count=1,
                    anomalies_included=len(shop_anomalies),
                    success=success,
                )
                result.dispatch_logs.append(log)

                if success:
                    print(f"[AlertDispatcher] ✓ Warning alert sent for {shop_id} ({len(shop_anomalies)} anomalies)")
                else:
                    print(f"[AlertDispatcher] ✗ Failed to send warning alert for {shop_id}")

            return len([l for l in result.dispatch_logs if l.success and l.severity == SeverityLevel.P1_HOURLY.value]) > 0

        except Exception as e:
            log = AlertDispatchLog(
                alert_type="warning",
                severity=SeverityLevel.P1_HOURLY.value,
                recipient_count=0,
                anomalies_included=len(anomalies),
                success=False,
                error_message=str(e),
            )
            result.dispatch_logs.append(log)
            print(f"[AlertDispatcher] ✗ Error dispatching warning alerts: {e}")
            return False

    def _dispatch_info_alerts(
        self,
        anomalies: List[AnomalyRecord],
        result: DispatchResult,
    ) -> bool:
        """Dispatch P2 (info) alerts in daily summary.

        Args:
            anomalies: List of P2 anomalies
            result: DispatchResult to update

        Returns:
            True if dispatched successfully
        """
        try:
            title = "Daily Anomaly Summary"
            description = f"Daily anomaly report: {len(anomalies)} minor anomalies detected\n"

            # Group by category
            by_category = {}
            for anomaly in anomalies:
                cat = anomaly.category.value
                if cat not in by_category:
                    by_category[cat] = 0
                by_category[cat] += 1

            description += "\n".join([
                f"  • {cat}: {count}"
                for cat, count in by_category.items()
            ])

            context = {
                "anomaly_count": len(anomalies),
                "category_breakdown": by_category,
                "affected_shops": len(set(a.shop_id for a in anomalies)),
                "affected_platforms": list(set(a.platform for a in anomalies)),
            }

            success = self.feishu.send_info_alert(
                title=title,
                description=description,
                component="order_tracker",
            )

            log = AlertDispatchLog(
                alert_type="info",
                severity=SeverityLevel.P2_DAILY.value,
                recipient_count=1,
                anomalies_included=len(anomalies),
                success=success,
            )
            result.dispatch_logs.append(log)

            if success:
                print(f"[AlertDispatcher] ✓ Info alert sent ({len(anomalies)} anomalies)")
            else:
                print(f"[AlertDispatcher] ✗ Failed to send info alert")

            return success

        except Exception as e:
            log = AlertDispatchLog(
                alert_type="info",
                severity=SeverityLevel.P2_DAILY.value,
                recipient_count=0,
                anomalies_included=len(anomalies),
                success=False,
                error_message=str(e),
            )
            result.dispatch_logs.append(log)
            print(f"[AlertDispatcher] ✗ Error dispatching info alerts: {e}")
            return False

    def get_result(self) -> Optional[DispatchResult]:
        """Get dispatch result.

        Returns:
            DispatchResult or None
        """
        return self.dispatch_result

    def save_result(self, output_path: Optional[Path] = None) -> Path:
        """Save dispatch result to JSON.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.dispatch_result:
            raise ValueError("No result to save - dispatch_alerts() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "alert_dispatch_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.dispatch_result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path


def main() -> None:
    """Demo alert dispatcher."""
    print("[AlertDispatcher] Testing Order Alert Dispatcher\n")

    dispatcher = OrderAlertDispatcher()

    # Dispatch alerts
    print("[AlertDispatcher] Starting alert dispatch...\n")
    result = dispatcher.dispatch_alerts()

    # Display result
    print(f"\n[AlertDispatcher] Dispatch Summary:")
    print(f"  Total anomalies processed: {result.total_anomalies_processed}")
    print(f"  Alerts dispatched: {result.alerts_dispatched}")
    print(f"  Alerts failed: {result.alerts_failed}")

    # Display dispatch logs
    if result.dispatch_logs:
        print(f"\n[AlertDispatcher] Dispatch Logs:")
        for log in result.dispatch_logs:
            status = "✓" if log.success else "✗"
            print(f"  {status} {log.alert_type} ({log.severity}): {log.anomalies_included} anomalies")
            if log.error_message:
                print(f"      Error: {log.error_message}")

    # Save result
    result_path = dispatcher.save_result()
    print(f"\n[AlertDispatcher] Result saved to: {result_path}")

    print(f"\n[AlertDispatcher] ✓ Alert dispatch completed successfully")


if __name__ == "__main__":
    main()
