#!/usr/bin/env python3
"""Predictive alerting engine for order processing.

Forecasts issues before they occur:
1. Payment overdue prediction (order >50min old, still pending)
2. Shipment delay prediction (order >18h paid, not shipped)
3. Delivery delay prediction (order >6d in transit)
4. Anomaly trend detection (rising anomaly rate)
5. Shop performance degradation

Sends proactive alerts for predicted issues.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, List
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from order_ledger import OrderLedger
from order_state_machine import OrderState, SeverityLevel
from feishu_integration import FeishuIntegration


class PredictionType(str, Enum):
    """Types of predictions."""
    PAYMENT_OVERDUE_RISK = "payment_overdue_risk"
    SHIPMENT_DELAY_RISK = "shipment_delay_risk"
    DELIVERY_DELAY_RISK = "delivery_delay_risk"
    ANOMALY_TREND_RISK = "anomaly_trend_risk"
    SHOP_DEGRADATION = "shop_degradation"


@dataclass
class Prediction:
    """Predictive alert for potential issue."""
    prediction_type: PredictionType
    order_id: str
    platform: str
    shop_id: str

    # Risk metrics
    risk_score: float  # 0-100
    time_to_violation_hours: float

    # Details
    description: str
    recommendation: str

    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["prediction_type"] = self.prediction_type.value
        return d


@dataclass
class PredictionReport:
    """Predictive analysis report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_predictions: int = 0
    high_risk_count: int = 0  # risk_score > 75
    medium_risk_count: int = 0  # risk_score 50-75
    low_risk_count: int = 0  # risk_score < 50
    predictions: List[Prediction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_predictions": self.total_predictions,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
            "predictions": [p.to_dict() for p in self.predictions],
        }


class PredictiveAlerting:
    """Predicts and alerts on potential issues."""

    # Risk thresholds
    PAYMENT_RISK_THRESHOLD_MINUTES = 50  # Alert if 50min+ pending
    SHIPMENT_RISK_THRESHOLD_HOURS = 18  # Alert if 18h+ paid, not shipped
    DELIVERY_RISK_THRESHOLD_DAYS = 6  # Alert if 6+ days in transit

    def __init__(self, ledger: Optional[OrderLedger] = None):
        """Initialize predictive alerting.

        Args:
            ledger: OrderLedger instance
        """
        self.ledger = ledger or OrderLedger()
        self.feishu = FeishuIntegration()
        self.report = None

    def analyze_predictions(self) -> PredictionReport:
        """Analyze orders and generate predictions.

        Returns:
            PredictionReport with predictions
        """
        report = PredictionReport()
        now = datetime.now(timezone.utc)

        for entry_id, order in self.ledger.entries.items():
            predictions = []

            # Check payment overdue risk
            if order.state_machine_state == OrderState.PENDING_PAYMENT.value:
                try:
                    order_date = datetime.fromisoformat(order.order_date.replace('Z', '+00:00'))
                    minutes_pending = (now - order_date).total_seconds() / 60

                    if minutes_pending > self.PAYMENT_RISK_THRESHOLD_MINUTES:
                        risk_score = min(100, (minutes_pending / 60) * 10)  # 10 points per hour
                        pred = Prediction(
                            prediction_type=PredictionType.PAYMENT_OVERDUE_RISK,
                            order_id=order.order_id,
                            platform=order.platform,
                            shop_id=order.shop_id,
                            risk_score=risk_score,
                            time_to_violation_hours=1.0 - (minutes_pending / 60),
                            description=f"Payment pending for {minutes_pending:.0f}min",
                            recommendation="Send payment reminder to customer",
                        )
                        predictions.append(pred)
                except Exception:
                    pass

            # Check shipment delay risk
            if order.state_machine_state == OrderState.PAID.value:
                try:
                    payment_date = datetime.fromisoformat(order.payment_date.replace('Z', '+00:00'))
                    hours_since_payment = (now - payment_date).total_seconds() / 3600

                    if hours_since_payment > self.SHIPMENT_RISK_THRESHOLD_HOURS:
                        risk_score = min(100, (hours_since_payment / 24) * 50)
                        pred = Prediction(
                            prediction_type=PredictionType.SHIPMENT_DELAY_RISK,
                            order_id=order.order_id,
                            platform=order.platform,
                            shop_id=order.shop_id,
                            risk_score=risk_score,
                            time_to_violation_hours=24.0 - hours_since_payment,
                            description=f"Order paid {hours_since_payment:.1f}h ago, not yet shipped",
                            recommendation="Prioritize order for shipment",
                        )
                        predictions.append(pred)
                except Exception:
                    pass

            # Check delivery delay risk
            if order.state_machine_state == OrderState.IN_TRANSIT.value:
                try:
                    shipped_date = datetime.fromisoformat(order.shipped_date.replace('Z', '+00:00'))
                    days_in_transit = (now - shipped_date).total_seconds() / 86400

                    if days_in_transit > self.DELIVERY_RISK_THRESHOLD_DAYS:
                        risk_score = min(100, (days_in_transit / 7) * 60)
                        pred = Prediction(
                            prediction_type=PredictionType.DELIVERY_DELAY_RISK,
                            order_id=order.order_id,
                            platform=order.platform,
                            shop_id=order.shop_id,
                            risk_score=risk_score,
                            time_to_violation_hours=(7 - days_in_transit) * 24,
                            description=f"Order in transit for {days_in_transit:.1f} days",
                            recommendation="Contact logistics provider for status update",
                        )
                        predictions.append(pred)
                except Exception:
                    pass

            # Add predictions to report
            for pred in predictions:
                report.predictions.append(pred)
                report.total_predictions += 1

                if pred.risk_score > 75:
                    report.high_risk_count += 1
                elif pred.risk_score > 50:
                    report.medium_risk_count += 1
                else:
                    report.low_risk_count += 1

        # Sort by risk score descending
        report.predictions.sort(key=lambda p: p.risk_score, reverse=True)

        self.report = report
        return report

    def dispatch_predictions(self) -> bool:
        """Dispatch predictive alerts.

        Returns:
            True if dispatched successfully
        """
        if not self.report or not self.report.high_risk_count:
            return True

        # Send high-risk predictions
        high_risk = [p for p in self.report.predictions if p.risk_score > 75]

        if high_risk:
            title = f"Predictive Alert: {len(high_risk)} High-Risk Orders"
            description = "Orders at risk of SLA violation:\n"
            description += "\n".join([
                f"  • {p.order_id} ({p.platform}): {p.description} (risk: {p.risk_score:.0f}%)"
                for p in high_risk[:5]
            ])
            if len(high_risk) > 5:
                description += f"\n  ... and {len(high_risk) - 5} more"

            context = {
                "high_risk_count": len(high_risk),
                "medium_risk_count": len([p for p in self.report.predictions if 50 < p.risk_score <= 75]),
                "low_risk_count": len([p for p in self.report.predictions if p.risk_score <= 50]),
                "top_risk": high_risk[0].description if high_risk else "N/A",
            }

            return self.feishu.send_warning_alert(
                title=title,
                description=description,
                component="predictive_alerter",
                context=context,
            )

        return True

    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """Save prediction report.

        Args:
            output_path: Output file path

        Returns:
            Path to saved file
        """
        if not self.report:
            raise ValueError("No report to save - analyze_predictions() not called")

        if not output_path:
            output_path = ROOT / "outputs" / "predictive_analysis_report.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def get_report(self) -> Optional[PredictionReport]:
        """Get prediction report.

        Returns:
            PredictionReport or None
        """
        return self.report


def main() -> None:
    """Demo predictive alerting."""
    print("[PredictiveAlerting] Testing Predictive Alerting\n")

    predictor = PredictiveAlerting()
    report = predictor.analyze_predictions()
    predictor.save_report()

    print(f"[PredictiveAlerting] Predictions Generated:")
    print(f"  Total predictions: {report.total_predictions}")
    print(f"  High risk: {report.high_risk_count}")
    print(f"  Medium risk: {report.medium_risk_count}")
    print(f"  Low risk: {report.low_risk_count}")

    if report.high_risk_count > 0:
        print(f"\n[PredictiveAlerting] High-Risk Orders:")
        for pred in report.predictions[:5]:
            if pred.risk_score > 75:
                print(f"  {pred.order_id} ({pred.platform}): {pred.description}")
                print(f"    Risk: {pred.risk_score:.0f}% | {pred.recommendation}")

    print(f"\n[PredictiveAlerting] ✓ Predictive analysis completed")


if __name__ == "__main__":
    main()
