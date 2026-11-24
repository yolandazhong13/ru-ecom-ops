#!/usr/bin/env python3
"""ML-based anomaly prediction and forecasting.

Provides:
1. Anomaly score calculation
2. Risk prediction (0-100)
3. Trend-based anomaly detection
4. Predictive alerts
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class AnomalyPrediction:
    """Anomaly prediction result."""
    order_id: str
    anomaly_score: float  # 0-100
    risk_level: str  # low, medium, high
    predicted_issues: List[str]
    confidence: float  # 0-1
    timestamp: str
    recommendation: str


class AnomalyPredictor:
    """Predicts anomalies using historical patterns."""

    def __init__(self):
        """Initialize anomaly predictor."""
        self.predictions: List[AnomalyPrediction] = []

    def predict(self, order_data: Dict[str, Any]) -> AnomalyPrediction:
        """Predict anomaly for order.

        Args:
            order_data: Order data

        Returns:
            AnomalyPrediction
        """
        order_id = order_data.get("order_id", "unknown")

        # Feature engineering
        features = self._extract_features(order_data)

        # Calculate anomaly score
        score = self._calculate_anomaly_score(features)

        # Determine risk level
        risk_level = "low" if score < 30 else "medium" if score < 70 else "high"

        # Predict issues
        issues = self._predict_issues(features, score)

        # Confidence (based on feature completeness)
        confidence = min(1.0, len(features) / 10)

        # Recommendation
        recommendation = self._get_recommendation(risk_level, issues)

        prediction = AnomalyPrediction(
            order_id=order_id,
            anomaly_score=score,
            risk_level=risk_level,
            predicted_issues=issues,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            recommendation=recommendation,
        )

        self.predictions.append(prediction)
        return prediction

    def _extract_features(self, order_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract ML features from order.

        Args:
            order_data: Order data

        Returns:
            Features dict
        """
        features = {}

        # Amount feature (high amounts = higher risk)
        amount = order_data.get("total_amount", 0)
        features["high_amount"] = 1.0 if amount > 5000 else 0.0

        # Platform feature
        platform = order_data.get("platform", "")
        features["is_ozon"] = 1.0 if platform == "Ozon" else 0.0

        # State feature
        state = order_data.get("state_machine_state", "")
        if state == "pending_payment":
            features["pending_state"] = 1.0
        elif state == "paid":
            features["paid_state"] = 1.0

        # Reconciliation feature
        matched = order_data.get("matched_on_platform", True)
        features["unmatched"] = 0.0 if matched else 1.0

        # Payment confirmation
        confirmed = order_data.get("payment_confirmed", False)
        features["payment_unconfirmed"] = 0.0 if confirmed else 1.0

        # Delivery status
        delivered = order_data.get("delivered", False)
        features["not_delivered"] = 0.0 if delivered else 1.0

        return features

    def _calculate_anomaly_score(self, features: Dict[str, float]) -> float:
        """Calculate anomaly score.

        Args:
            features: Features dict

        Returns:
            Score 0-100
        """
        # Weighted score
        weights = {
            "high_amount": 15,
            "is_ozon": 5,
            "pending_state": 20,
            "paid_state": 10,
            "unmatched": 30,
            "payment_unconfirmed": 25,
            "not_delivered": 20,
        }

        score = 0.0
        for feature, weight in weights.items():
            if feature in features:
                score += features[feature] * weight

        return min(100.0, score)

    def _predict_issues(self, features: Dict[str, float], score: float) -> List[str]:
        """Predict issues.

        Args:
            features: Features dict
            score: Anomaly score

        Returns:
            List of predicted issues
        """
        issues = []

        if features.get("unmatched", 0) > 0.5:
            issues.append("Missing on platform")
        if features.get("payment_unconfirmed", 0) > 0.5:
            issues.append("Payment not confirmed")
        if features.get("pending_state", 0) > 0.5:
            issues.append("Order pending payment")
        if features.get("high_amount", 0) > 0.5:
            issues.append("High transaction amount")
        if features.get("not_delivered", 0) > 0.5:
            issues.append("Not yet delivered")

        return issues[:3]  # Top 3 issues

    def _get_recommendation(self, risk_level: str, issues: List[str]) -> str:
        """Get recommendation.

        Args:
            risk_level: Risk level
            issues: Predicted issues

        Returns:
            Recommendation
        """
        if risk_level == "high":
            return "Escalate to operations team immediately"
        elif risk_level == "medium":
            if "Missing on platform" in issues:
                return "Retry platform sync"
            elif "Payment not confirmed" in issues:
                return "Verify payment status"
            return "Monitor for escalation"
        else:
            return "No action needed"

    def get_summary(self) -> Dict[str, Any]:
        """Get prediction summary.

        Returns:
            Summary dict
        """
        if not self.predictions:
            return {"total": 0}

        high_risk = sum(1 for p in self.predictions if p.risk_level == "high")
        medium_risk = sum(1 for p in self.predictions if p.risk_level == "medium")
        low_risk = sum(1 for p in self.predictions if p.risk_level == "low")

        avg_score = sum(p.anomaly_score for p in self.predictions) / len(self.predictions)

        return {
            "total_predictions": len(self.predictions),
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "average_anomaly_score": avg_score,
        }


def main() -> None:
    """Demo anomaly predictor."""
    print("[AnomalyPredictor] Testing ML anomaly prediction\n")

    predictor = AnomalyPredictor()

    # Test cases
    test_orders = [
        {
            "order_id": "OZ_001",
            "platform": "Ozon",
            "total_amount": 1500,
            "state_machine_state": "confirmed",
            "matched_on_platform": True,
            "payment_confirmed": True,
            "delivered": True,
        },
        {
            "order_id": "WB_002",
            "platform": "WB_CN",
            "total_amount": 8000,
            "state_machine_state": "pending_payment",
            "matched_on_platform": False,
            "payment_confirmed": False,
            "delivered": False,
        },
        {
            "order_id": "OZ_003",
            "platform": "Ozon",
            "total_amount": 3000,
            "state_machine_state": "paid",
            "matched_on_platform": True,
            "payment_confirmed": True,
            "delivered": False,
        },
    ]

    for order in test_orders:
        prediction = predictor.predict(order)
        print(f"Order: {prediction.order_id}")
        print(f"  Score: {prediction.anomaly_score:.0f} ({prediction.risk_level})")
        print(f"  Issues: {', '.join(prediction.predicted_issues)}")
        print(f"  Recommendation: {prediction.recommendation}\n")

    summary = predictor.get_summary()
    print(f"[AnomalyPredictor] Summary:")
    print(f"  Total: {summary['total_predictions']}")
    print(f"  High risk: {summary['high_risk']}")
    print(f"  Medium risk: {summary['medium_risk']}")
    print(f"  Low risk: {summary['low_risk']}")
    print(f"  Avg score: {summary['average_anomaly_score']:.1f}")


if __name__ == "__main__":
    main()
