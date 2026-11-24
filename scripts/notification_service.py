#!/usr/bin/env python3
"""Notification service for email and Slack alerts.

Sends notifications:
1. Email alerts
2. Slack messages (webhook)
3. Alert digests
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    P0_CRITICAL = "P0"
    P1_WARNING = "P1"
    P2_INFO = "P2"


class NotificationService:
    """Sends notifications via multiple channels."""

    def __init__(self, slack_webhook: Optional[str] = None, email_config: Optional[Dict] = None):
        """Initialize notification service.

        Args:
            slack_webhook: Slack webhook URL
            email_config: Email configuration dict
        """
        self.slack_webhook = slack_webhook
        self.email_config = email_config or {}
        self.notifications_sent = 0

    def send_alert(
        self,
        order_id: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.P2_INFO,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send alert via all configured channels.

        Args:
            order_id: Order ID
            message: Alert message
            severity: Severity level
            details: Additional details

        Returns:
            True if sent successfully
        """
        alert_data = {
            "order_id": order_id,
            "message": message,
            "severity": severity.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }

        success = True

        # Try Slack
        if self.slack_webhook:
            if not self._send_slack(alert_data):
                success = False

        # Try email (mock)
        if self.email_config:
            if not self._send_email(alert_data):
                success = False

        # Always log
        self._log_alert(alert_data)

        if success:
            self.notifications_sent += 1

        return success

    def _send_slack(self, alert_data: Dict[str, Any]) -> bool:
        """Send Slack message.

        Args:
            alert_data: Alert data

        Returns:
            True if sent
        """
        try:
            # In production, use requests library
            # For now, just log that we would send
            emoji = "🔴" if alert_data["severity"] == "P0" else "🟡" if alert_data["severity"] == "P1" else "🟢"

            print(f"[Slack] {emoji} {alert_data['severity']}: {alert_data['order_id']} - {alert_data['message']}")
            return True

        except Exception as e:
            print(f"[Slack] Error: {e}")
            return False

    def _send_email(self, alert_data: Dict[str, Any]) -> bool:
        """Send email notification.

        Args:
            alert_data: Alert data

        Returns:
            True if sent
        """
        try:
            # In production, use smtplib
            # For now, just log
            subject = f"[{alert_data['severity']}] Order Alert: {alert_data['order_id']}"
            print(f"[Email] To: {self.email_config.get('to', 'admin@example.com')}")
            print(f"[Email] Subject: {subject}")
            print(f"[Email] Body: {alert_data['message']}")
            return True

        except Exception as e:
            print(f"[Email] Error: {e}")
            return False

    def _log_alert(self, alert_data: Dict[str, Any]) -> None:
        """Log alert locally.

        Args:
            alert_data: Alert data
        """
        log_path = ROOT / "data" / "alerts.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a") as f:
            f.write(json.dumps(alert_data) + "\n")

    def send_digest(self, alerts: list[Dict[str, Any]]) -> bool:
        """Send alert digest.

        Args:
            alerts: List of alerts

        Returns:
            True if sent
        """
        if not alerts:
            return True

        digest = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_alerts": len(alerts),
            "p0_count": sum(1 for a in alerts if a.get("severity") == "P0"),
            "p1_count": sum(1 for a in alerts if a.get("severity") == "P1"),
            "p2_count": sum(1 for a in alerts if a.get("severity") == "P2"),
            "alerts": alerts,
        }

        print(f"\n[Digest] Daily Alert Summary:")
        print(f"  Total: {digest['total_alerts']}")
        print(f"  🔴 P0: {digest['p0_count']}")
        print(f"  🟡 P1: {digest['p1_count']}")
        print(f"  🟢 P2: {digest['p2_count']}\n")

        return True

    def get_stats(self) -> Dict[str, int]:
        """Get notification statistics.

        Returns:
            Statistics dict
        """
        return {
            "notifications_sent": self.notifications_sent,
        }


def main() -> None:
    """Demo notification service."""
    print("[NotificationService] Testing notification service\n")

    # Initialize with mock config
    notify = NotificationService(
        slack_webhook="https://hooks.slack.com/mock",
        email_config={"to": "admin@example.com"},
    )

    # Send test alerts
    notify.send_alert(
        "OZ_123456",
        "Payment confirmation delayed",
        AlertSeverity.P1_WARNING,
        {"reason": "Platform API timeout"},
    )

    notify.send_alert(
        "WB_654321",
        "Order reconciliation failed",
        AlertSeverity.P0_CRITICAL,
        {"discrepancy": "Missing on platform"},
    )

    notify.send_alert(
        "OZ_111111",
        "Shipment tracking updated",
        AlertSeverity.P2_INFO,
    )

    stats = notify.get_stats()
    print(f"\n[NotificationService] ✓ Notifications sent: {stats['notifications_sent']}")


if __name__ == "__main__":
    main()
