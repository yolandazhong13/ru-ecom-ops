#!/usr/bin/env python3
"""Unified monitoring dashboard aggregating health, API, and data quality metrics.

Provides composite health scoring, cascading failure detection, real-time
monitoring, and predictive alerting across all workflow modules and platforms.

Architecture:
- Three-tier data layer: HealthTracker, APIHealthTracker, DataQualityValidator
- Unified aggregation: CompositeHealthScorer with weighted algorithm
- Anomaly detection: CascadingFailureDetector for correlated issues
- Real-time endpoints: health_endpoint, trends_endpoint, alerts_endpoint
- Feishu integration: CRITICAL/WARNING/INFO alert flows
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from collections import defaultdict
import statistics

ROOT = Path(__file__).resolve().parents[1]
HEALTH_DB = ROOT / "outputs" / "health_tracking.json"
API_HEALTH_DB = ROOT / "outputs" / "api_health_tracking.json"
VALIDATION_REPORTS_DIR = ROOT / "outputs" / "validation_reports"
UNIFIED_DASHBOARD_DB = ROOT / "outputs" / "unified_monitoring_dashboard.json"


class CompositeHealthStatus(str, Enum):
    """Composite health status across all dimensions."""
    HEALTHY = "healthy"  # score >= 90
    DEGRADED = "degraded"  # 70 <= score < 90
    UNHEALTHY = "unhealthy"  # score < 70
    UNKNOWN = "unknown"


class CascadingFailureType(str, Enum):
    """Types of cascading failures detected."""
    API_LATENCY_CASCADE = "api_latency_cascade"  # API latency → module slowdown → validation warnings
    API_ERROR_CASCADE = "api_error_cascade"  # API errors → module failures → alert spike
    QUALITY_DATA_CASCADE = "quality_data_cascade"  # Data quality violations → audit flags → SLA risk
    PLATFORM_UNAVAILABLE = "platform_unavailable"  # Platform down → all modules fail
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"  # Rate limits → queuing → slowdown


@dataclass
class CompositeDimensionScore:
    """Score for a single monitoring dimension."""
    dimension: str  # "health", "api", "quality"
    score: float  # 0-100
    metric_count: int
    healthy_count: int
    weight: float


@dataclass
class CompositeHealthScore:
    """Composite health score aggregating all dimensions."""
    timestamp: str
    health_dimension: CompositeDimensionScore
    api_dimension: CompositeDimensionScore
    quality_dimension: CompositeDimensionScore
    composite_score: float  # Weighted sum
    status: CompositeHealthStatus
    sla_compliance: dict[str, bool]  # SLA threshold checks
    module_breakdown: dict[str, dict[str, Any]]  # Per-module dimension scores
    platform_breakdown: dict[str, dict[str, Any]]  # Per-platform dimension scores


@dataclass
class CascadingFailureEvent:
    """Record of a detected cascading failure pattern."""
    failure_type: CascadingFailureType
    severity: str  # "critical", "warning", "info"
    timestamp: str
    root_cause: str  # Description of root cause
    affected_modules: list[str]
    affected_platforms: list[str]
    correlation_evidence: dict[str, Any]  # Metrics supporting correlation
    recommended_action: str


@dataclass
class TrendPoint:
    """Single point in a trend timeline."""
    timestamp: str
    composite_score: float
    health_score: float
    api_score: float
    quality_score: float
    status: CompositeHealthStatus
    cascading_failures_count: int


@dataclass
class UnifiedMonitoringReport:
    """Complete unified monitoring report."""
    timestamp: str
    composite_health: CompositeHealthScore
    cascading_failures: list[CascadingFailureEvent]
    trends: list[TrendPoint]  # Last 24 hours
    trending_degradation: bool
    predicted_unhealthy_in_1h: bool
    predicted_unhealthy_in_4h: bool
    alerts_to_send: list[dict[str, Any]]


class CompositeHealthScorer:
    """Computes composite health across health, API, and quality dimensions."""

    # Weights for weighted composite score
    HEALTH_WEIGHT = 0.4  # Module execution reliability
    API_WEIGHT = 0.35    # Integration stability
    QUALITY_WEIGHT = 0.25  # Output correctness

    # SLA Thresholds
    SLA_HEALTH_SUCCESS_RATE = 99.0  # >= 99% success
    SLA_HEALTH_ERROR_RATE = 1.0     # <= 1% error
    SLA_API_AVAILABILITY = 99.0     # >= 99% available
    SLA_API_LATENCY_P95 = 1000.0    # <= 1000ms p95
    SLA_QUALITY_PASS_RATE = 95.0    # >= 95% validation pass
    SLA_COMPOSITE_SCORE = 90.0      # >= 90 composite score
    SLA_CASCADING_FAILURES = 0      # Zero cascading failures

    def __init__(self):
        """Initialize scorer."""
        self.health_metrics: dict[str, Any] = {}
        self.api_metrics: dict[str, Any] = {}
        self.quality_metrics: dict[str, Any] = {}
        self._load_all_metrics()

    def _load_all_metrics(self) -> None:
        """Load metrics from all three data sources."""
        self._load_health_metrics()
        self._load_api_metrics()
        self._load_quality_metrics()

    def _load_health_metrics(self) -> None:
        """Load health tracking metrics."""
        if HEALTH_DB.exists():
            try:
                data = json.loads(HEALTH_DB.read_text(encoding="utf-8"))
                self.health_metrics = data
            except Exception:
                self.health_metrics = {}

    def _load_api_metrics(self) -> None:
        """Load API health tracking metrics."""
        if API_HEALTH_DB.exists():
            try:
                data = json.loads(API_HEALTH_DB.read_text(encoding="utf-8"))
                self.api_metrics = data
            except Exception:
                self.api_metrics = {}

    def _load_quality_metrics(self) -> None:
        """Load data quality validation results."""
        if VALIDATION_REPORTS_DIR.exists():
            try:
                report_file = VALIDATION_REPORTS_DIR / "validation_report.json"
                if report_file.exists():
                    data = json.loads(report_file.read_text(encoding="utf-8"))
                    self.quality_metrics = data
            except Exception:
                self.quality_metrics = {}

    def compute_health_dimension_score(self) -> CompositeDimensionScore:
        """Compute health dimension score (module execution reliability)."""
        aggregated = self.health_metrics.get("aggregated", {})

        if not aggregated:
            return CompositeDimensionScore(
                dimension="health",
                score=50.0,
                metric_count=0,
                healthy_count=0,
                weight=self.HEALTH_WEIGHT
            )

        total_modules = len(aggregated)
        healthy_modules = sum(
            1 for m in aggregated.values()
            if m.get("status") == "healthy"
        )

        # Score based on percentage of healthy modules
        # With bonus/penalty for overall success rate
        summary = self.health_metrics.get("summary", {})
        success_rate = summary.get("overall_success_rate", 0.0)

        # Base score: healthy ratio (0-100)
        base_score = (healthy_modules / total_modules * 100) if total_modules > 0 else 0.0

        # Adjust by success rate
        if success_rate >= self.SLA_HEALTH_SUCCESS_RATE:
            final_score = min(100.0, base_score + 10)  # Bonus for SLA compliance
        elif success_rate < 80:
            final_score = max(0.0, base_score - 20)  # Penalty for low success
        else:
            final_score = base_score

        return CompositeDimensionScore(
            dimension="health",
            score=final_score,
            metric_count=total_modules,
            healthy_count=healthy_modules,
            weight=self.HEALTH_WEIGHT
        )

    def compute_api_dimension_score(self) -> CompositeDimensionScore:
        """Compute API dimension score (integration stability)."""
        aggregated = self.api_metrics.get("aggregated", {})

        if not aggregated:
            return CompositeDimensionScore(
                dimension="api",
                score=50.0,
                metric_count=0,
                healthy_count=0,
                weight=self.API_WEIGHT
            )

        endpoints = list(aggregated.values())
        total_endpoints = len(endpoints)

        # Collect metrics across all endpoints
        availability_scores = []
        latency_scores = []

        for endpoint in endpoints:
            # Availability: 100% - error_rate
            error_rate = endpoint.get("error_rate", 0.0)
            availability = 100.0 - error_rate
            availability_scores.append(availability)

            # Latency: check if p95 within SLA
            p95_latency = endpoint.get("p95_duration_ms", 0)
            latency_score = 100.0 if p95_latency <= self.SLA_API_LATENCY_P95 else max(0.0, 100.0 - (p95_latency - self.SLA_API_LATENCY_P95) / 10)
            latency_scores.append(latency_score)

        # Average scores
        avg_availability = statistics.mean(availability_scores) if availability_scores else 50.0
        avg_latency = statistics.mean(latency_scores) if latency_scores else 50.0

        # Composite API score: 60% availability + 40% latency
        api_score = (avg_availability * 0.6) + (avg_latency * 0.4)

        healthy_endpoints = sum(1 for s in availability_scores if s >= 99.0)

        return CompositeDimensionScore(
            dimension="api",
            score=api_score,
            metric_count=total_endpoints,
            healthy_count=healthy_endpoints,
            weight=self.API_WEIGHT
        )

    def compute_quality_dimension_score(self) -> CompositeDimensionScore:
        """Compute quality dimension score (output correctness)."""
        validation_results = self.quality_metrics.get("validation_results", [])

        if not validation_results:
            return CompositeDimensionScore(
                dimension="quality",
                score=50.0,
                metric_count=0,
                healthy_count=0,
                weight=self.QUALITY_WEIGHT
            )

        total_validations = len(validation_results)
        passed_validations = sum(
            1 for v in validation_results
            if v.get("validation_status") == "valid"
        )

        # Calculate overall pass rate
        pass_rate = (passed_validations / total_validations * 100) if total_validations > 0 else 0.0

        # Score based on pass rate with SLA adjustment
        if pass_rate >= self.SLA_QUALITY_PASS_RATE:
            quality_score = min(100.0, pass_rate + 5)  # Bonus for exceeding SLA
        else:
            quality_score = max(0.0, pass_rate - 10)  # Penalty for below SLA

        return CompositeDimensionScore(
            dimension="quality",
            score=quality_score,
            metric_count=total_validations,
            healthy_count=passed_validations,
            weight=self.QUALITY_WEIGHT
        )

    def compute_composite_score(self) -> CompositeHealthScore:
        """Compute weighted composite health score across all dimensions."""
        health_dim = self.compute_health_dimension_score()
        api_dim = self.compute_api_dimension_score()
        quality_dim = self.compute_quality_dimension_score()

        # Weighted composite score
        composite_score = (
            (health_dim.score * health_dim.weight) +
            (api_dim.score * api_dim.weight) +
            (quality_dim.score * quality_dim.weight)
        )

        # Determine status
        if composite_score >= 90:
            status = CompositeHealthStatus.HEALTHY
        elif composite_score >= 70:
            status = CompositeHealthStatus.DEGRADED
        else:
            status = CompositeHealthStatus.UNHEALTHY

        # Check SLA compliance
        sla_compliance = {
            "health_success_rate": self.health_metrics.get("summary", {}).get("overall_success_rate", 0.0) >= self.SLA_HEALTH_SUCCESS_RATE,
            "health_error_rate": self.health_metrics.get("summary", {}).get("overall_error_rate", 100.0) <= self.SLA_HEALTH_ERROR_RATE,
            "api_availability": health_dim.score >= 99.0,
            "quality_pass_rate": quality_dim.score >= self.SLA_QUALITY_PASS_RATE,
            "composite_score": composite_score >= self.SLA_COMPOSITE_SCORE,
        }

        # Build module breakdown
        module_breakdown = self._build_module_breakdown()
        platform_breakdown = self._build_platform_breakdown()

        return CompositeHealthScore(
            timestamp=datetime.now(timezone.utc).isoformat(),
            health_dimension=health_dim,
            api_dimension=api_dim,
            quality_dimension=quality_dim,
            composite_score=composite_score,
            status=status,
            sla_compliance=sla_compliance,
            module_breakdown=module_breakdown,
            platform_breakdown=platform_breakdown
        )

    def _build_module_breakdown(self) -> dict[str, dict[str, Any]]:
        """Build per-module breakdown of dimension scores."""
        breakdown = {}
        aggregated = self.health_metrics.get("aggregated", {})

        for module_name, metrics in aggregated.items():
            breakdown[module_name] = {
                "health_status": metrics.get("status"),
                "success_rate": metrics.get("success_rate", 0.0),
                "total_executions": metrics.get("total_executions", 0),
                "last_execution": metrics.get("last_execution"),
            }

        return breakdown

    def _build_platform_breakdown(self) -> dict[str, dict[str, Any]]:
        """Build per-platform breakdown of dimension scores."""
        breakdown = defaultdict(lambda: {"modules": [], "api_endpoints": [], "status": "unknown"})

        # Add health metrics by platform
        for module_name, metrics in self.health_metrics.get("aggregated", {}).items():
            platform = metrics.get("platform", "unknown")
            breakdown[platform]["modules"].append(module_name)

        # Add API metrics by platform
        for endpoint_key, metrics in self.api_metrics.get("aggregated", {}).items():
            platform = metrics.get("platform", "unknown")
            if platform not in breakdown:
                breakdown[platform] = {"modules": [], "api_endpoints": [], "status": "unknown"}
            breakdown[platform]["api_endpoints"].append(endpoint_key)

        return dict(breakdown)


class CascadingFailureDetector:
    """Detects cascading failure patterns across health, API, and quality dimensions."""

    def __init__(self, scorer: CompositeHealthScorer):
        """Initialize detector with scorer instance."""
        self.scorer = scorer

    def detect_cascading_failures(self) -> list[CascadingFailureEvent]:
        """Detect all cascading failure patterns."""
        failures = []
        failures.extend(self._detect_api_latency_cascade())
        failures.extend(self._detect_api_error_cascade())
        failures.extend(self._detect_quality_data_cascade())
        failures.extend(self._detect_platform_unavailable())
        failures.extend(self._detect_rate_limit_cascade())
        return failures

    def _detect_api_latency_cascade(self) -> list[CascadingFailureEvent]:
        """Detect: API latency spike → module slowdown → validation warnings."""
        failures = []
        api_aggregated = self.scorer.api_metrics.get("aggregated", {})
        health_aggregated = self.scorer.health_metrics.get("aggregated", {})

        # Check for API endpoints with high latency (p95 > 1000ms)
        high_latency_endpoints = [
            (key, ep) for key, ep in api_aggregated.items()
            if ep.get("p95_duration_ms", 0) > 1000
        ]

        if high_latency_endpoints:
            # Find affected modules
            affected_modules = []
            for key, endpoint in high_latency_endpoints:
                platform = endpoint.get("platform")
                for module_name, module_metrics in health_aggregated.items():
                    if module_metrics.get("platform") == platform:
                        avg_duration = module_metrics.get("average_duration_ms", 0)
                        if avg_duration > 500:  # Elevated module latency
                            affected_modules.append(module_name)

            if affected_modules:
                failures.append(CascadingFailureEvent(
                    failure_type=CascadingFailureType.API_LATENCY_CASCADE,
                    severity="warning",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    root_cause="API endpoint latency exceeded SLA threshold (p95 > 1000ms), causing module slowdown",
                    affected_modules=affected_modules,
                    affected_platforms=[ep.get("platform") for _, ep in high_latency_endpoints],
                    correlation_evidence={
                        "api_endpoints_affected": len(high_latency_endpoints),
                        "modules_affected": len(affected_modules),
                        "highest_api_latency_ms": max(ep.get("p95_duration_ms", 0) for _, ep in high_latency_endpoints),
                    },
                    recommended_action="Investigate API endpoint performance; check upstream service health and database query performance"
                ))

        return failures

    def _detect_api_error_cascade(self) -> list[CascadingFailureEvent]:
        """Detect: API error rate increase → module failures → alert spike."""
        failures = []
        api_aggregated = self.scorer.api_metrics.get("aggregated", {})
        health_aggregated = self.scorer.health_metrics.get("aggregated", {})

        # Check for API endpoints with high error rate (>10%)
        high_error_endpoints = [
            (key, ep) for key, ep in api_aggregated.items()
            if ep.get("error_rate", 0) > 10
        ]

        if high_error_endpoints:
            affected_modules = []
            for key, endpoint in high_error_endpoints:
                platform = endpoint.get("platform")
                for module_name, module_metrics in health_aggregated.items():
                    if module_metrics.get("platform") == platform:
                        if module_metrics.get("error_rate", 0) > 5:  # Elevated module error rate
                            affected_modules.append(module_name)

            if affected_modules:
                failures.append(CascadingFailureEvent(
                    failure_type=CascadingFailureType.API_ERROR_CASCADE,
                    severity="critical",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    root_cause="API error rate spiked above threshold (>10%), cascading to module execution failures",
                    affected_modules=affected_modules,
                    affected_platforms=[ep.get("platform") for _, ep in high_error_endpoints],
                    correlation_evidence={
                        "api_endpoints_affected": len(high_error_endpoints),
                        "modules_affected": len(affected_modules),
                        "highest_api_error_rate": max(ep.get("error_rate", 0) for _, ep in high_error_endpoints),
                    },
                    recommended_action="CRITICAL: Immediately page on-call engineer; check API service status and retry queue"
                ))

        return failures

    def _detect_quality_data_cascade(self) -> list[CascadingFailureEvent]:
        """Detect: Data quality violations → audit flags → SLA risk."""
        failures = []
        quality_metrics = self.scorer.quality_metrics
        validation_results = quality_metrics.get("validation_results", [])

        # Check for validation failures
        failed_validations = [
            v for v in validation_results
            if v.get("validation_status") != "valid"
        ]

        if len(failed_validations) > len(validation_results) * 0.1:  # >10% failure rate
            failures.append(CascadingFailureEvent(
                failure_type=CascadingFailureType.QUALITY_DATA_CASCADE,
                severity="warning",
                timestamp=datetime.now(timezone.utc).isoformat(),
                root_cause=f"Data quality violations detected in {len(failed_validations)} validations (>10% failure rate)",
                affected_modules=list(set(v.get("data_type", "unknown") for v in failed_validations)),
                affected_platforms=["multi"],
                correlation_evidence={
                    "total_validations": len(validation_results),
                    "failed_validations": len(failed_validations),
                    "failure_rate_percent": (len(failed_validations) / len(validation_results) * 100),
                },
                recommended_action="Review validation rules and data transformations; audit recent schema changes"
            ))

        return failures

    def _detect_platform_unavailable(self) -> list[CascadingFailureEvent]:
        """Detect: Platform down → all modules fail."""
        failures = []
        api_aggregated = self.scorer.api_metrics.get("aggregated", {})

        # Group API endpoints by platform and check availability
        platform_availability = defaultdict(list)
        for key, endpoint in api_aggregated.items():
            platform = endpoint.get("platform")
            error_rate = endpoint.get("error_rate", 0)
            platform_availability[platform].append(error_rate)

        # Check if entire platform has >50% error rate
        for platform, error_rates in platform_availability.items():
            avg_error_rate = statistics.mean(error_rates)
            if avg_error_rate > 50:
                failures.append(CascadingFailureEvent(
                    failure_type=CascadingFailureType.PLATFORM_UNAVAILABLE,
                    severity="critical",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    root_cause=f"Platform {platform} showing >50% average error rate across all endpoints",
                    affected_modules=[],
                    affected_platforms=[platform],
                    correlation_evidence={
                        "platform": platform,
                        "average_error_rate": avg_error_rate,
                        "affected_endpoints": len(error_rates),
                    },
                    recommended_action="CRITICAL: Contact platform provider; check status page and incident reports"
                ))

        return failures

    def _detect_rate_limit_cascade(self) -> list[CascadingFailureEvent]:
        """Detect: Rate limits exceeded → queuing → slowdown."""
        failures = []
        api_aggregated = self.scorer.api_metrics.get("aggregated", {})

        # Check for endpoints with low rate_limit_remaining
        low_rate_limit = [
            (key, ep) for key, ep in api_aggregated.items()
            if ep.get("rate_limit_remaining") is not None and ep.get("rate_limit_remaining") < 100
        ]

        if low_rate_limit:
            failures.append(CascadingFailureEvent(
                failure_type=CascadingFailureType.RATE_LIMIT_EXCEEDED,
                severity="warning",
                timestamp=datetime.now(timezone.utc).isoformat(),
                root_cause=f"{len(low_rate_limit)} API endpoints approaching rate limit (<100 remaining)",
                affected_modules=[],
                affected_platforms=list(set(ep.get("platform") for _, ep in low_rate_limit)),
                correlation_evidence={
                    "affected_endpoints": len(low_rate_limit),
                    "lowest_rate_limit_remaining": min(ep.get("rate_limit_remaining", 0) for _, ep in low_rate_limit),
                },
                recommended_action="Reduce API call frequency or request rate limit increase from platform provider"
            ))

        return failures


class UnifiedMonitoringDashboard:
    """Main unified monitoring dashboard orchestrating all components."""

    def __init__(self):
        """Initialize dashboard with all components."""
        self.scorer = CompositeHealthScorer()
        self.failure_detector = CascadingFailureDetector(self.scorer)
        self.trends_history: list[TrendPoint] = []
        self._load_trends_history()

    def _load_trends_history(self) -> None:
        """Load historical trend data."""
        if UNIFIED_DASHBOARD_DB.exists():
            try:
                data = json.loads(UNIFIED_DASHBOARD_DB.read_text(encoding="utf-8"))
                trends_data = data.get("trends_history", [])
                self.trends_history = [
                    TrendPoint(**t) for t in trends_data
                ]
            except Exception:
                self.trends_history = []

    def load_all_metrics(self) -> None:
        """Load all metrics from data sources."""
        self.scorer._load_all_metrics()

    def compute_composite_health(self) -> CompositeHealthScore:
        """Compute composite health score."""
        return self.scorer.compute_composite_score()

    def detect_cascading_failures(self) -> list[CascadingFailureEvent]:
        """Detect cascading failure patterns."""
        return self.failure_detector.detect_cascading_failures()

    def compute_trends(self, hours: int = 24) -> list[TrendPoint]:
        """Get trend data for the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [t for t in self.trends_history if datetime.fromisoformat(t.timestamp) > cutoff]

    def predict_health_trajectory(self) -> dict[str, Any]:
        """Predict health trajectory for next 1 and 4 hours."""
        trends = self.compute_trends(hours=24)
        if len(trends) < 2:
            return {
                "has_sufficient_data": False,
                "predicted_unhealthy_in_1h": False,
                "predicted_unhealthy_in_4h": False,
            }

        # Simple linear regression over last 24 hours
        scores = [t.composite_score for t in trends]
        timestamps = [datetime.fromisoformat(t.timestamp) for t in trends]

        # Calculate trend slope
        if len(scores) >= 2:
            time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            score_diffs = [scores[i+1] - scores[i] for i in range(len(scores)-1)]
            avg_slope = statistics.mean([sd/td if td > 0 else 0 for sd, td in zip(score_diffs, time_diffs)])
        else:
            avg_slope = 0

        # Predict at 1h and 4h
        current_score = scores[-1] if scores else 70
        predicted_1h = current_score + (avg_slope * 3600)
        predicted_4h = current_score + (avg_slope * 14400)

        return {
            "has_sufficient_data": True,
            "current_score": current_score,
            "trend_slope_per_second": avg_slope,
            "predicted_score_1h": predicted_1h,
            "predicted_score_4h": predicted_4h,
            "predicted_unhealthy_in_1h": predicted_1h < 70,
            "predicted_unhealthy_in_4h": predicted_4h < 70,
            "trending_degradation": avg_slope < 0,
        }

    def generate_unified_report(self) -> UnifiedMonitoringReport:
        """Generate complete unified monitoring report."""
        composite_health = self.compute_composite_health()
        cascading_failures = self.detect_cascading_failures()
        trends = self.compute_trends(hours=24)
        trajectory = self.predict_health_trajectory()

        # Generate alerts
        alerts = self._generate_alerts(
            composite_health,
            cascading_failures,
            trajectory
        )

        return UnifiedMonitoringReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            composite_health=composite_health,
            cascading_failures=cascading_failures,
            trends=trends,
            trending_degradation=trajectory.get("trending_degradation", False),
            predicted_unhealthy_in_1h=trajectory.get("predicted_unhealthy_in_1h", False),
            predicted_unhealthy_in_4h=trajectory.get("predicted_unhealthy_in_4h", False),
            alerts_to_send=alerts
        )

    def _generate_alerts(
        self,
        composite_health: CompositeHealthScore,
        cascading_failures: list[CascadingFailureEvent],
        trajectory: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate alerts based on current state and predictions."""
        alerts = []

        # Critical alerts for unhealthy status
        if composite_health.status == CompositeHealthStatus.UNHEALTHY:
            for failure in cascading_failures:
                if failure.severity == "critical":
                    alerts.append({
                        "type": "CRITICAL",
                        "title": f"Cascading Failure: {failure.failure_type.value}",
                        "message": failure.root_cause,
                        "action": failure.recommended_action,
                        "modules": failure.affected_modules,
                        "platforms": failure.affected_platforms,
                    })

        # Warning alerts for degraded status
        elif composite_health.status == CompositeHealthStatus.DEGRADED:
            for failure in cascading_failures:
                if failure.severity in ("warning", "critical"):
                    alerts.append({
                        "type": "WARNING",
                        "title": f"Degradation: {failure.failure_type.value}",
                        "message": failure.root_cause,
                        "action": failure.recommended_action,
                        "modules": failure.affected_modules,
                        "platforms": failure.affected_platforms,
                    })

        # Info alerts for trending degradation
        if trajectory.get("trending_degradation"):
            alerts.append({
                "type": "INFO",
                "title": "Trending Degradation Detected",
                "message": f"Health score trending downward at {trajectory.get('trend_slope_per_second', 0):.4f} points/sec",
                "action": "Review recent deployments and API changes",
            })

        # Predictive alerts
        if trajectory.get("predicted_unhealthy_in_1h"):
            alerts.append({
                "type": "INFO",
                "title": "Predictive Alert: Unhealthy Status Expected in 1 Hour",
                "message": f"Current trajectory predicts score {trajectory.get('predicted_score_1h', 0):.1f} in 1 hour",
                "action": "Proactively investigate root causes before SLA breach",
            })

        return alerts

    def save_report(self, report: UnifiedMonitoringReport) -> None:
        """Save report to database, maintaining trend history."""
        # Create trend point
        trend = TrendPoint(
            timestamp=report.timestamp,
            composite_score=report.composite_health.composite_score,
            health_score=report.composite_health.health_dimension.score,
            api_score=report.composite_health.api_dimension.score,
            quality_score=report.composite_health.quality_dimension.score,
            status=report.composite_health.status,
            cascading_failures_count=len(report.cascading_failures),
        )

        # Add to history (keep last 7 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        self.trends_history = [
            t for t in self.trends_history
            if datetime.fromisoformat(t.timestamp) > cutoff
        ]
        self.trends_history.append(trend)

        # Save to database
        output = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "latest_report": {
                "timestamp": report.timestamp,
                "composite_health": asdict(report.composite_health),
                "cascading_failures": [asdict(f) for f in report.cascading_failures],
                "trending_degradation": report.trending_degradation,
                "predicted_unhealthy_in_1h": report.predicted_unhealthy_in_1h,
                "predicted_unhealthy_in_4h": report.predicted_unhealthy_in_4h,
                "alerts_count": len(report.alerts_to_send),
            },
            "trends_history": [asdict(t) for t in self.trends_history],
            "cascading_failures_24h": [asdict(f) for f in report.cascading_failures],
        }

        UNIFIED_DASHBOARD_DB.parent.mkdir(parents=True, exist_ok=True)
        UNIFIED_DASHBOARD_DB.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")

    def get_health_endpoint(self) -> dict[str, Any]:
        """Get health data for dashboard endpoint."""
        composite_health = self.compute_composite_health()
        return {
            "timestamp": composite_health.timestamp,
            "status": composite_health.status.value,
            "composite_score": round(composite_health.composite_score, 2),
            "health_score": round(composite_health.health_dimension.score, 2),
            "api_score": round(composite_health.api_dimension.score, 2),
            "quality_score": round(composite_health.quality_dimension.score, 2),
            "module_breakdown": composite_health.module_breakdown,
            "platform_breakdown": composite_health.platform_breakdown,
            "sla_compliance": composite_health.sla_compliance,
        }

    def get_trends_endpoint(self, hours: int = 24) -> dict[str, Any]:
        """Get trend data for dashboard endpoint."""
        trends = self.compute_trends(hours=hours)
        trajectory = self.predict_health_trajectory()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trends": [asdict(t) for t in trends],
            "trajectory": trajectory,
        }

    def get_alerts_endpoint(self) -> dict[str, Any]:
        """Get active alerts for dashboard endpoint."""
        report = self.generate_unified_report()
        self.save_report(report)

        return {
            "timestamp": report.timestamp,
            "cascading_failures": [asdict(f) for f in report.cascading_failures],
            "alerts": report.alerts_to_send,
            "alerts_count": len(report.alerts_to_send),
        }


def main():
    """Main entry point."""
    dashboard = UnifiedMonitoringDashboard()
    dashboard.load_all_metrics()

    # Generate and display report
    report = dashboard.generate_unified_report()
    dashboard.save_report(report)

    print("\n" + "="*80)
    print("UNIFIED MONITORING DASHBOARD REPORT")
    print("="*80)
    print(f"\nGenerated: {report.timestamp}")
    print(f"Status: {report.composite_health.status.value.upper()}")
    print(f"Composite Score: {report.composite_health.composite_score:.1f}/100")

    print(f"\nDimension Scores:")
    print(f"  Health:  {report.composite_health.health_dimension.score:.1f}/100")
    print(f"  API:     {report.composite_health.api_dimension.score:.1f}/100")
    print(f"  Quality: {report.composite_health.quality_dimension.score:.1f}/100")

    print(f"\nSLA Compliance:")
    for sla, compliant in report.composite_health.sla_compliance.items():
        status = "✓" if compliant else "✗"
        print(f"  {status} {sla}: {compliant}")

    print(f"\nCascading Failures Detected: {len(report.cascading_failures)}")
    for failure in report.cascading_failures:
        print(f"  - [{failure.severity.upper()}] {failure.failure_type.value}")
        print(f"    Root Cause: {failure.root_cause}")
        print(f"    Affected: {failure.affected_modules or failure.affected_platforms}")

    print(f"\nAlerts to Send: {len(report.alerts_to_send)}")
    for alert in report.alerts_to_send:
        print(f"  - [{alert['type']}] {alert['title']}")

    print(f"\nTrend Analysis:")
    print(f"  Current Trend: {'Degrading ↓' if report.trending_degradation else 'Stable/Improving ↑'}")
    print(f"  Unhealthy in 1h: {report.predicted_unhealthy_in_1h}")
    print(f"  Unhealthy in 4h: {report.predicted_unhealthy_in_4h}")

    print(f"\nReport saved to: {UNIFIED_DASHBOARD_DB}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
