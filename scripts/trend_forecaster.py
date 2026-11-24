#!/usr/bin/env python3
"""Trend forecasting using time series patterns.

Provides:
1. Revenue trend forecasting
2. Order volume prediction
3. Anomaly rate trending
4. Seasonality detection
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TrendForecast:
    """Trend forecast result."""
    metric: str  # revenue, orders, anomalies
    current_value: float
    predicted_values: List[float]  # Next 7 days
    trend: str  # up, down, stable
    confidence: float
    forecast_date: str


class TrendForecaster:
    """Forecasts trends using historical data."""

    def __init__(self):
        """Initialize trend forecaster."""
        self.historical_data: Dict[str, List[float]] = {
            "revenue": [],
            "orders": [],
            "anomalies": [],
        }

    def add_historical_point(self, metric: str, value: float) -> None:
        """Add historical data point.

        Args:
            metric: Metric name
            value: Value
        """
        if metric in self.historical_data:
            self.historical_data[metric].append(value)

    def forecast(self, metric: str, days_ahead: int = 7) -> TrendForecast:
        """Forecast metric.

        Args:
            metric: Metric to forecast
            days_ahead: Days to forecast

        Returns:
            TrendForecast
        """
        data = self.historical_data.get(metric, [])

        if not data:
            # Return default if no data
            return TrendForecast(
                metric=metric,
                current_value=0,
                predicted_values=[0] * days_ahead,
                trend="stable",
                confidence=0,
                forecast_date=datetime.now(timezone.utc).isoformat(),
            )

        current_value = data[-1] if data else 0

        # Simple trend detection: compare last 3 values
        trend = self._detect_trend(data)

        # Generate predictions using simple linear extrapolation
        predictions = self._extrapolate(data, days_ahead)

        # Calculate confidence based on data consistency
        confidence = self._calculate_confidence(data)

        return TrendForecast(
            metric=metric,
            current_value=current_value,
            predicted_values=predictions,
            trend=trend,
            confidence=confidence,
            forecast_date=datetime.now(timezone.utc).isoformat(),
        )

    def _detect_trend(self, data: List[float]) -> str:
        """Detect trend from recent data.

        Args:
            data: Historical data

        Returns:
            Trend: up, down, or stable
        """
        if len(data) < 3:
            return "stable"

        recent = data[-3:]
        avg_first_half = sum(recent[:2]) / 2
        last_value = recent[-1]

        change_pct = (last_value - avg_first_half) / avg_first_half if avg_first_half > 0 else 0

        if change_pct > 0.1:
            return "up"
        elif change_pct < -0.1:
            return "down"
        else:
            return "stable"

    def _extrapolate(self, data: List[float], days: int) -> List[float]:
        """Extrapolate data forward.

        Args:
            data: Historical data
            days: Days to extrapolate

        Returns:
            Predicted values
        """
        if len(data) < 2:
            return [data[-1] if data else 0] * days

        # Simple linear regression
        avg_last_3 = sum(data[-3:]) / min(3, len(data))

        # Calculate trend (simple slope)
        if len(data) >= 2:
            slope = (data[-1] - data[-2]) / max(1, data[-2]) if data[-2] != 0 else 0
        else:
            slope = 0

        predictions = []
        current = avg_last_3

        for i in range(days):
            current = current * (1 + slope * 0.1)  # Dampen trend
            predictions.append(current)

        return predictions

    def _calculate_confidence(self, data: List[float]) -> float:
        """Calculate forecast confidence.

        Args:
            data: Historical data

        Returns:
            Confidence 0-1
        """
        if len(data) < 3:
            return 0.3

        # Confidence based on data consistency
        variance = self._calculate_variance(data[-7:]) if len(data) >= 7 else self._calculate_variance(data)
        mean = sum(data[-7:]) / min(7, len(data))

        if mean == 0:
            return 0.5

        cv = variance / mean  # Coefficient of variation
        confidence = max(0.1, min(1.0, 1.0 - cv))

        return confidence

    def _calculate_variance(self, data: List[float]) -> float:
        """Calculate variance.

        Args:
            data: Data

        Returns:
            Variance
        """
        if len(data) < 2:
            return 0

        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5  # Return std dev


def main() -> None:
    """Demo trend forecasting."""
    print("[TrendForecaster] Testing trend forecasting\n")

    forecaster = TrendForecaster()

    # Add historical data
    print("[TrendForecaster] Adding historical data:")

    # Revenue trend: increasing
    for i in range(14):
        value = 10000 + (i * 500)  # Increasing
        forecaster.add_historical_point("revenue", value)

    # Orders: stable
    for i in range(14):
        value = 50 + (i % 3)  # Small fluctuation
        forecaster.add_historical_point("orders", value)

    # Anomalies: decreasing
    for i in range(14):
        value = max(2, 10 - (i * 0.5))  # Decreasing
        forecaster.add_historical_point("anomalies", value)

    print("  ✓ 14 days of historical data loaded\n")

    # Forecast
    print("[TrendForecaster] Forecasts for next 7 days:")

    for metric in ["revenue", "orders", "anomalies"]:
        forecast = forecaster.forecast(metric, days_ahead=7)

        print(f"\n{metric.upper()}:")
        print(f"  Current: {forecast.current_value:.0f}")
        print(f"  Trend: {forecast.trend}")
        print(f"  Confidence: {forecast.confidence:.0%}")
        print(f"  Predictions:")
        for day, value in enumerate(forecast.predicted_values, 1):
            print(f"    Day {day}: {value:.0f}")


if __name__ == "__main__":
    main()
