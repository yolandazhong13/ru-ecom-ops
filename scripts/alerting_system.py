#!/usr/bin/env python3
"""Alerting system for workflow health, API, and validation issues.

Sends alerts via multiple channels (Feishu, email, local logging) when:
1. Module health degrades
2. API endpoints become unavailable
3. Data quality validation fails
4. SLA targets are missed
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
ALERTS_LOG = ROOT / "outputs" / "alerts.json"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    FEISHU = "feishu"
    EMAIL = "email"
    LOCAL_LOG = "local_log"
    SLACK = "slack"


@dataclass
class Alert:
    """Single alert event."""
    severity: AlertSeverity
    title: str
    description: str
    component: str  # health_tracking, api_monitoring, data_quality, etc.
    timestamp: str
    context: dict[str, Any]
    acknowledged: bool = False
    resolution: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "component": self.component,
            "timestamp": self.timestamp,
            "context": self.context,
            "acknowledged": self.acknowledged,
            "resolution": self.resolution,
        }

    def to_feishu_message(self) -> dict[str, Any]:
        """Format alert as Feishu Rich Text Card.

        Returns:
            Feishu card dict
        """
        color_map = {
            AlertSeverity.INFO: "blue",
            AlertSeverity.WARNING: "orange",
            AlertSeverity.CRITICAL: "red",
        }
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }

        color = color_map.get(self.severity, "blue")
        emoji = emoji_map.get(self.severity, "ℹ️")

        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"{emoji} **{self.title}**",
                            "tag": "lark_md",
                        },
                    },
                    {
                        "tag": "hr",
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": self.description,
                            "tag": "lark_md",
                        },
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**Component:**\n{self.component}",
                                    "tag": "lark_md",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**Severity:**\n{self.severity.value.upper()}",
                                    "tag": "lark_md",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**Time:**\n{self.timestamp}",
                                    "tag": "lark_md",
                                },
                            },
                        ],
                    },
                ],
                "header": {
                    "template": color,
                    "title": {
                        "content": f"{emoji} {self.title}",
                        "tag": "plain_text",
                    },
                },
            },
        }


class AlertingSystem:
    """Centralized alerting system for platform monitoring."""

    def __init__(self, feishu_webhook_url: Optional[str] = None):
        """Initialize alerting system.

        Args:
            feishu_webhook_url: Feishu webhook URL for sending alerts
        """
        self.feishu_webhook_url = feishu_webhook_url
        self.alerts: list[Alert] = []
        self._load_alerts_log()

    def _load_alerts_log(self) -> None:
        """Load existing alerts from log file."""
        if ALERTS_LOG.exists():
            try:
                data = json.loads(ALERTS_LOG.read_text(encoding="utf-8"))
                for alert_data in data.get("alerts", []):
                    self.alerts.append(Alert(
                        severity=AlertSeverity(alert_data["severity"]),
                        title=alert_data["title"],
                        description=alert_data["description"],
                        component=alert_data["component"],
                        timestamp=alert_data["timestamp"],
                        context=alert_data["context"],
                        acknowledged=alert_data.get("acknowledged", False),
                        resolution=alert_data.get("resolution"),
                    ))
            except Exception:
                pass

    def send_alert(
        self,
        severity: AlertSeverity,
        title: str,
        description: str,
        component: str,
        context: Optional[dict[str, Any]] = None,
        channels: Optional[list[AlertChannel]] = None,
    ) -> Alert:
        """Send alert through configured channels.

        Args:
            severity: Alert severity level
            title: Alert title
            description: Alert description
            component: Component that triggered alert
            context: Additional context data
            channels: List of alert channels to use

        Returns:
            Alert object
        """
        if channels is None:
            channels = [AlertChannel.LOCAL_LOG]

        alert = Alert(
            severity=severity,
            title=title,
            description=description,
            component=component,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context=context or {},
        )

        self.alerts.append(alert)

        # Send through channels
        for channel in channels:
            if channel == AlertChannel.LOCAL_LOG:
                self._log_alert(alert)
            elif channel == AlertChannel.FEISHU:
                self._send_feishu_alert(alert)
            elif channel == AlertChannel.EMAIL:
                self._send_email_alert(alert)

        # Persist alerts
        self._save_alerts_log()

        return alert

    def _log_alert(self, alert: Alert) -> None:
        """Log alert to console and file.

        Args:
            alert: Alert to log
        """
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }
        emoji = emoji_map.get(alert.severity, "ℹ️")

        print(f"\n{emoji} [{alert.component.upper()}] {alert.title}")
        print(f"   Severity: {alert.severity.value.upper()}")
        print(f"   {alert.description}")
        if alert.context:
            print(f"   Context: {json.dumps(alert.context, ensure_ascii=False)}")

    def _send_feishu_alert(self, alert: Alert) -> None:
        """Send alert via Feishu webhook.

        Args:
            alert: Alert to send
        """
        if not self.feishu_webhook_url:
            print(f"[Alerting] Feishu webhook not configured, skipping")
            return

        # In production, would use requests library to POST to webhook
        print(f"[Alerting] Would send Feishu alert: {alert.title}")

    def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email.

        Args:
            alert: Alert to send
        """
        # In production, would use smtplib to send email
        print(f"[Alerting] Would send email alert: {alert.title}")

    def acknowledge_alert(self, alert_index: int, resolution: str) -> bool:
        """Mark alert as acknowledged with resolution.

        Args:
            alert_index: Index of alert to acknowledge
            resolution: Resolution description

        Returns:
            True if acknowledged, False if index invalid
        """
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].acknowledged = True
            self.alerts[alert_index].resolution = resolution
            self._save_alerts_log()
            return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        """Get all unacknowledged alerts.

        Returns:
            List of active (unacknowledged) alerts
        """
        return [a for a in self.alerts if not a.acknowledged]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        """Get alerts by severity level.

        Args:
            severity: Severity level

        Returns:
            List of alerts at that severity
        """
        return [a for a in self.alerts if a.severity == severity]

    def _save_alerts_log(self) -> None:
        """Persist alerts to JSON file."""
        ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_alerts": len(self.alerts),
            "active_alerts": len(self.get_active_alerts()),
            "alerts": [a.to_dict() for a in self.alerts],
        }

        ALERTS_LOG.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def print_alert_summary(self) -> None:
        """Print summary of active alerts."""
        active = self.get_active_alerts()

        if not active:
            print("\n✓ No active alerts - all systems nominal\n")
            return

        print(f"\n⚠️  ACTIVE ALERTS ({len(active)} total)\n")

        by_severity = {}
        for alert in active:
            if alert.severity not in by_severity:
                by_severity[alert.severity] = []
            by_severity[alert.severity].append(alert)

        for severity in [AlertSeverity.CRITICAL, AlertSeverity.WARNING, AlertSeverity.INFO]:
            if severity in by_severity:
                alerts = by_severity[severity]
                emoji_map = {
                    AlertSeverity.INFO: "ℹ️",
                    AlertSeverity.WARNING: "⚠️",
                    AlertSeverity.CRITICAL: "🚨",
                }
                emoji = emoji_map[severity]
                print(f"{emoji} {severity.value.upper()} ({len(alerts)}):")
                for i, alert in enumerate(alerts):
                    print(f"  [{i}] {alert.title}")
                    print(f"      {alert.description}")
                print()


def main() -> None:
    """Demo alerting system."""
    alerting = AlertingSystem()

    print("[Alerting] Sending sample alerts...")

    # Sample alerts
    alerting.send_alert(
        severity=AlertSeverity.INFO,
        title="Pricing Update Completed",
        description="Successfully updated prices for 2 SKUs with 45%+ margin",
        component="pricing_handler",
        context={"skus_updated": 2, "total_margin": 212.5},
        channels=[AlertChannel.LOCAL_LOG],
    )

    alerting.send_alert(
        severity=AlertSeverity.WARNING,
        title="API Latency Elevated",
        description="Ozon RU /v1/product/attributes/update endpoint P95 latency: 450ms (target: 500ms)",
        component="api_integration",
        context={"endpoint": "/v1/product/attributes/update", "p95_ms": 450, "target_ms": 500},
        channels=[AlertChannel.LOCAL_LOG],
    )

    alerting.send_alert(
        severity=AlertSeverity.CRITICAL,
        title="Data Quality Validation Failed",
        description="Inventory aggregation validation failed: row_count decreased from 10 to 8",
        component="data_quality",
        context={"rows_before": 10, "rows_after": 8, "schema": "inventory_aggregation"},
        channels=[AlertChannel.LOCAL_LOG],
    )

    print(f"\n[Alerting] Alerts sent: {len(alerting.alerts)}")
    alerting.print_alert_summary()

    # Save alerts
    alerting._save_alerts_log()
    print(f"\n[Alerting] ✓ Alerts saved to: {ALERTS_LOG}")


if __name__ == "__main__":
    main()
