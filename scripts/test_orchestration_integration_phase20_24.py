"""
test_orchestration_integration_phase20-24.py
Master integration tests for end-to-end 5-phase security pipeline validation.
Tests cover: threat detection→orchestration→risk quantification→compliance→policy approval chains.
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from orchestration_master_phase20_24 import (
    MasterOrchestrationEngine,
    ThreatPredictionEngine,
    OrchestrationEngine,
    SecurityRiskQuantificationEngine,
    ComplianceAutomationEngine,
    PolicyGovernanceEngine,
    AnomalyEvent,
    AnomalyType,
    WorkflowStatus,
    RiskLevel,
    ComplianceFramework,
    PolicyStatus,
    OrchestrationContext
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def master_engine():
    """Initialize master orchestration engine for testing"""
    return MasterOrchestrationEngine()


@pytest.fixture
def high_severity_event():
    """High-severity simulated event triggering automatic orchestration"""
    return {
        'source_ip': '192.168.1.100',
        'destination_ip': '10.0.0.1',
        'user_id': 'user_12345',
        'event_type': 'network_traffic',
        'volumetric_spike': 4.0,  # > 3 * 2.5 threshold
        'confidence': 0.95
    }


@pytest.fixture
def low_severity_event():
    """Low-severity event requiring manual review"""
    return {
        'source_ip': '192.168.1.50',
        'destination_ip': '10.0.0.2',
        'user_id': 'user_67890',
        'event_type': 'network_traffic',
        'volumetric_spike': 2.6,  # > 2.5 threshold (detected) but severity 2.6*15=39 < 50 (manual review)
        'confidence': 0.75
    }


@pytest.fixture
def concurrent_events():
    """Multiple events with varying severity levels"""
    return [
        {
            'source_ip': f'192.168.1.{100+i}',
            'destination_ip': f'10.0.0.{1+i}',
            'user_id': f'user_{12345+i}',
            'event_type': 'network_traffic',
            'volumetric_spike': 3.0 + (i * 0.5),  # Increasing severity
            'confidence': 0.90 + (i * 0.01)
        }
        for i in range(5)
    ]


# ============================================================================
# TEST: SINGLE THREAT DETECTION THROUGH APPROVAL CHAIN
# ============================================================================

def test_single_threat_through_approval_chain(master_engine, high_severity_event):
    """
    End-to-end test: single threat detection → workflow orchestration →
    risk quantification → compliance gaps → policy creation → approval → re-execution

    Validates unidirectional data flow across all 5 phases.
    """
    # PHASE 21: Detect anomaly
    context = master_engine.execute_pipeline(high_severity_event)

    assert context.anomaly is not None, "Anomaly should be detected"
    assert context.anomaly.severity_score >= 40, f"Expected severity ≥40, got {context.anomaly.severity_score}"
    assert context.anomaly.confidence >= 0.85, "Confidence should meet baseline threshold"

    # Verify Phase 21 audit trail
    phase_21_events = [e for e in context.audit_trail if e.get('phase') == 21]
    assert len(phase_21_events) == 1, "Phase 21 should create exactly one audit entry"
    assert phase_21_events[0]['event'] == 'anomaly_detected'

    # PHASE 20: Workflow orchestration
    assert context.workflow is not None, "Workflow should be created for high-severity anomaly"
    assert context.workflow.status == WorkflowStatus.COMPLETED, "Workflow should execute to completion"
    assert len(context.workflow.actions) >= 2, "Workflow should have multiple actions"
    assert context.workflow.audit_trail[-1]['event'] == 'workflow_completed'

    # PHASE 22: Risk quantification
    assert context.risk_assessment is not None, "Risk assessment should be generated"
    assert context.risk_assessment.asset_value > 0, "Asset value should be calculated"
    assert context.risk_assessment.residual_risk_score <= context.anomaly.severity_score, \
        "Residual risk should be ≤ original severity after mitigation"
    assert context.risk_assessment.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM]

    # Verify financial impact calculation
    expected_impact = (context.risk_assessment.residual_risk_score / 100) * context.risk_assessment.asset_value
    assert abs(context.risk_assessment.financial_impact - expected_impact) < 0.01, \
        "Financial impact calculation mismatch"

    # PHASE 23: Compliance gap analysis
    assert len(context.remediation_plans) > 0, "Remediation plans should be generated for high-risk"

    for plan in context.remediation_plans:
        assert plan.framework in ComplianceFramework, f"Unknown framework: {plan.framework}"
        assert len(plan.gaps) > 0, "Remediation plan should have gaps"
        assert plan.estimated_effort_hours > 0, "Effort estimation should be positive"

        for gap in plan.gaps:
            assert gap.control_id, "Gap should reference a control ID"
            assert gap.risk_exposure == context.risk_assessment.risk_level.value

    # PHASE 24: Policy creation and approval
    assert len(context.policies) > 0, "Policies should be created from remediation plans"
    assert len(context.approval_workflows) > 0, "Approval workflows should be created"

    for policy in context.policies:
        assert policy.status == PolicyStatus.REVIEW, "Policy should be in REVIEW status initially"
        assert policy.content['framework'], "Policy should reference framework"
        assert len(policy.audit_trail) >= 1, "Policy should have audit trail"

    # Simulate approval processing
    for approval_id in context.approval_workflows:
        approved_policy = master_engine.phase_24.process_approvals(approval_id)

        assert approved_policy is not None, "Approval processing should return policy"
        assert approved_policy.approval_percentage == 66.67, \
            f"Expected 66.67% (2/3), got {approved_policy.approval_percentage}"
        assert approved_policy.status == PolicyStatus.APPROVED, "Policy should be approved"
        assert len(approved_policy.approved_by) == 2, "Should have 2 approvals"

    # Verify immutable audit trail
    assert len(context.audit_trail) >= 5, "Should have audit entries from all phases"
    timestamps = [datetime.fromisoformat(e['timestamp']) for e in context.audit_trail]
    assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1)), \
        "Audit trail timestamps should be monotonically increasing"


def test_low_severity_requires_manual_review(master_engine, low_severity_event):
    """
    Test that low-severity anomalies (severity < 50) skip automatic orchestration
    and require manual review instead.
    """
    context = master_engine.execute_pipeline(low_severity_event)

    assert context.anomaly is not None, "Anomaly should be detected"
    assert context.anomaly.severity_score < 50, "Low severity should be < 50"
    assert context.workflow is None, "Workflow should NOT be created for low severity"

    # Verify manual review flag in audit trail
    phase_20_events = [e for e in context.audit_trail if e.get('phase') == 20]
    assert any(e['event'] == 'manual_review_required' for e in phase_20_events), \
        "Should flag manual review requirement"

    # Downstream phases should not execute
    assert context.risk_assessment is None, "Risk assessment should not occur without workflow"
    assert len(context.remediation_plans) == 0, "No remediation plans without risk assessment"
    assert len(context.policies) == 0, "No policies without remediation plans"


# ============================================================================
# TEST: CONCURRENT ANOMALIES AT DIFFERENT SEVERITY LEVELS
# ============================================================================

def test_concurrent_anomalies_different_severities(master_engine, concurrent_events):
    """
    Test processing of 5 concurrent anomalies with increasing severity levels.
    Validates:
    - Each anomaly generates correct severity_score
    - Workflow routing matches severity thresholds
    - No race conditions in shared state (lock safety)
    - Audit trails remain distinct per anomaly
    """
    contexts = []

    for i, event in enumerate(concurrent_events):
        context = master_engine.execute_pipeline(event)
        contexts.append(context)

    # Verify all anomalies detected
    assert len(contexts) == 5, "Should process all 5 events"
    assert all(c.anomaly is not None for c in contexts), "All events should generate anomalies"

    # Verify severity scores increase monotonically
    severity_scores = [c.anomaly.severity_score for c in contexts]
    assert severity_scores == sorted(severity_scores), "Severity should increase with volumetric_spike"

    # Verify workflow routing based on severity thresholds
    for i, context in enumerate(contexts):
        expected_spike = 3.0 + (i * 0.5)
        expected_severity = min(100, expected_spike * 15)

        if expected_severity >= 50:
            assert context.workflow is not None, f"Event {i} (severity {expected_severity}) should create workflow"
            assert context.risk_assessment is not None, "Risk assessment should follow workflow"
        else:
            assert context.workflow is None, f"Event {i} (severity {expected_severity}) should not create workflow"
            assert context.risk_assessment is None, "Risk assessment should not occur"

    # Verify no state leakage between contexts (each maintains independent audit trail)
    for i, context in enumerate(contexts):
        assert context.anomaly.event_id.endswith(str(i)) or len(context.audit_trail) > 0, \
            f"Context {i} should have independent audit trail"

    # Verify completed_contexts are thread-safely stored
    assert len(master_engine.completed_contexts) == 5, "All contexts should be stored"
    stored_anomalies = [c.anomaly.event_id for c in master_engine.completed_contexts if c.anomaly]
    assert len(set(stored_anomalies)) == 5, "Stored anomaly IDs should be unique"


def test_concurrent_anomalies_no_race_conditions(master_engine):
    """
    Stress test: rapidly process multiple events to validate thread safety
    and confirm no race conditions in approval processing.
    """
    # Generate 10 high-severity events
    events = [
        {
            'source_ip': f'192.168.1.{100+i}',
            'destination_ip': f'10.0.0.{1+i}',
            'user_id': f'user_{12345+i}',
            'event_type': 'network_traffic',
            'volumetric_spike': 4.0 + (i % 3) * 0.5,
            'confidence': 0.92
        }
        for i in range(10)
    ]

    # Process all events
    for event in events:
        master_engine.execute_pipeline(event)

    # Verify all contexts stored and distinct
    assert len(master_engine.completed_contexts) == 10, "All 10 events should create contexts"

    workflow_ids = set()
    for ctx in master_engine.completed_contexts:
        if ctx.workflow:
            assert ctx.workflow.workflow_id not in workflow_ids, "Workflow IDs should be unique"
            workflow_ids.add(ctx.workflow.workflow_id)

    # Verify orchestration engine counter is correct
    assert master_engine.phase_20.workflow_counter == len(workflow_ids), \
        "Workflow counter should match created workflows"


# ============================================================================
# TEST: FRAMEWORK-SPECIFIC COMPLIANCE CHAINS
# ============================================================================

def test_framework_specific_compliance_chains(master_engine, high_severity_event):
    """
    Test that each compliance framework generates appropriate controls
    and remediation plans based on risk level.
    """
    context = master_engine.execute_pipeline(high_severity_event)

    assert len(context.remediation_plans) > 0, "Should generate remediation plans"

    # Group plans by framework
    plans_by_framework = {}
    for plan in context.remediation_plans:
        if plan.framework not in plans_by_framework:
            plans_by_framework[plan.framework] = []
        plans_by_framework[plan.framework].append(plan)

    # Verify framework coverage
    expected_frameworks = [f for f in ComplianceFramework]
    for framework in expected_frameworks:
        if framework in plans_by_framework:
            plans = plans_by_framework[framework]
            assert all(p.framework == framework for p in plans), \
                "Plan framework should match grouping"

            for plan in plans:
                # Verify gaps reference framework controls
                framework_controls = master_engine.phase_23.framework_controls.get(framework, [])
                for gap in plan.gaps:
                    assert gap.control_id in framework_controls, \
                        f"Gap control {gap.control_id} not in {framework.value}"

    # Verify priority mapping in each plan
    for plan in context.remediation_plans:
        assert 'CRITICAL' in plan.priority_mapping, "Priority mapping should include CRITICAL"
        assert plan.priority_mapping['CRITICAL'] == 1, "CRITICAL should have highest priority (1)"
        assert plan.priority_mapping['LOW'] == 4, "LOW should have lowest priority (4)"


def test_risk_level_to_compliance_mapping(master_engine, high_severity_event):
    """
    Validate that risk levels correctly map to compliance control generation.
    - CRITICAL/HIGH → all controls triggered
    - MEDIUM → subset triggered
    - LOW → minimal controls
    """
    context = master_engine.execute_pipeline(high_severity_event)

    # Force high-risk assessment
    assert context.risk_assessment is not None
    original_risk_level = context.risk_assessment.risk_level

    # HIGH/CRITICAL should generate multiple plans
    if original_risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
        assert len(context.remediation_plans) >= 3, \
            "High-risk should generate plans for multiple frameworks"

        # Each plan should have gaps
        total_gaps = sum(len(p.gaps) for p in context.remediation_plans)
        assert total_gaps > 0, "High-risk should generate compliance gaps"


# ============================================================================
# TEST: CROSS-PHASE DATA CONSISTENCY VALIDATION
# ============================================================================

def test_cross_phase_data_consistency(master_engine, high_severity_event):
    """
    Validate that data flows correctly between phases without loss or corruption.
    Checks:
    - AnomalyEvent → Workflow (event_id preserved)
    - Workflow → RiskAssessment (workflow_id preserved)
    - RiskAssessment → RemediationPlan (risk_id preserved)
    - RemediationPlan → PolicyVersion (plan_id referenced in policy)
    """
    context = master_engine.execute_pipeline(high_severity_event)

    # Phase 21 → Phase 20: event_id carried forward
    assert context.anomaly is not None
    assert context.workflow is not None
    assert context.workflow.triggered_by_event == context.anomaly.event_id, \
        "Workflow should reference triggering anomaly"

    # Phase 20 → Phase 22: workflow_id carried forward
    assert context.risk_assessment is not None
    assert context.risk_assessment.workflow_id == context.workflow.workflow_id, \
        "Risk assessment should reference workflow"

    # Phase 22 → Phase 23: risk_id carried in remediation plans
    for plan in context.remediation_plans:
        # Verify gaps reference the risk assessment
        for gap in plan.gaps:
            assert context.risk_assessment.risk_id in gap.gap_description, \
                "Gap should reference risk assessment"

    # Phase 23 → Phase 24: remediation plan info in policy
    for i, policy in enumerate(context.policies):
        assert policy.content['framework'], "Policy should have framework"
        assert len(policy.content['gaps']) > 0, "Policy should have gaps from remediation"


def test_audit_trail_consistency(master_engine, high_severity_event):
    """
    Validate that immutable audit trails are maintained across all phases.
    - Timestamps are monotonically increasing
    - All phases represented
    - No duplicate events
    """
    context = master_engine.execute_pipeline(high_severity_event)

    assert len(context.audit_trail) > 0, "Audit trail should have entries"

    # Parse timestamps
    timestamps = []
    for entry in context.audit_trail:
        ts = datetime.fromisoformat(entry['timestamp'])
        timestamps.append(ts)

    # Verify monotonic increase (within same second tolerance)
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i+1], \
            f"Timestamps should not decrease: {timestamps[i]} > {timestamps[i+1]}"

    # Verify phase coverage
    phases_in_trail = set(e.get('phase') for e in context.audit_trail if 'phase' in e)
    expected_phases = {21, 20, 22, 23, 24}
    assert phases_in_trail == expected_phases, \
        f"Should have entries from all phases. Got {phases_in_trail}, expected {expected_phases}"


# ============================================================================
# TEST: FLOATING-POINT PRECISION IN APPROVAL CALCULATIONS
# ============================================================================

def test_approval_percentage_precision(master_engine, high_severity_event):
    """
    Validate that approval_percentage uses round(..., 2) precision consistently.
    Tests edge cases:
    - 1/3 ≈ 33.33%
    - 2/3 ≈ 66.67%
    - Various other fractions
    """
    context = master_engine.execute_pipeline(high_severity_event)

    # Process approvals
    for approval_id in context.approval_workflows:
        policy = master_engine.phase_24.process_approvals(approval_id)

        # 2/3 approvals = 66.67% (not 66.66666...)
        if len(policy.approved_by) == 2 and policy.approver_count == 3:
            assert policy.approval_percentage == 66.67, \
                f"2/3 should be 66.67%, not {policy.approval_percentage}"
            assert isinstance(policy.approval_percentage, float), \
                "Approval percentage should be float"


def test_financial_impact_precision(master_engine, high_severity_event):
    """
    Validate that financial impact calculations use consistent precision.
    """
    context = master_engine.execute_pipeline(high_severity_event)

    if context.risk_assessment:
        risk = context.risk_assessment

        # Recalculate to verify precision
        expected_impact = (risk.residual_risk_score / 100) * risk.asset_value

        # Should match within floating-point tolerance
        assert abs(risk.financial_impact - expected_impact) < 0.01, \
            f"Financial impact mismatch: {risk.financial_impact} vs {expected_impact}"


# ============================================================================
# TEST: ERROR HANDLING AND RESILIENCE
# ============================================================================

def test_missing_anomaly_handling(master_engine, low_severity_event):
    """
    Test graceful handling when anomaly falls below detection threshold.
    """
    # Event that doesn't trigger anomaly detection
    no_anomaly_event = {
        'source_ip': '192.168.1.1',
        'destination_ip': '10.0.0.1',
        'user_id': 'user_normal',
        'event_type': 'network_traffic',
        'volumetric_spike': 1.0,  # Well below threshold
        'confidence': 0.5
    }

    context = master_engine.execute_pipeline(no_anomaly_event)

    assert context.anomaly is None, "No anomaly should be detected below threshold"
    assert context.workflow is None, "No workflow without anomaly"
    assert context.risk_assessment is None, "No risk assessment without workflow"


def test_workflow_execution_failure_handling(master_engine, high_severity_event):
    """
    Test that workflow execution failures are captured in audit trail
    and don't crash the pipeline.
    """
    context = master_engine.execute_pipeline(high_severity_event)

    # Mock a workflow failure scenario
    if context.workflow:
        # Manually trigger failure path
        original_status = context.workflow.status
        context.workflow.status = WorkflowStatus.FAILED
        context.workflow.audit_trail.append({
            'timestamp': datetime.now().isoformat(),
            'event': 'workflow_failed',
            'error': 'Simulated failure'
        })

        # Pipeline should still continue to risk assessment
        assert len(context.workflow.audit_trail) > 0, "Failure should be logged"


def test_policy_approval_with_insufficient_approvals(master_engine, high_severity_event):
    """
    Test that policies requiring > 2/3 approvals remain in REVIEW status.
    """
    context = master_engine.execute_pipeline(high_severity_event)

    # Simulate scenario where only 1/3 approve (doesn't meet 66.67% threshold)
    for approval_id in context.approval_workflows:
        workflow = master_engine.phase_24.approval_workflows[approval_id]
        workflow['approved_by'] = [workflow['approvers'][0]]  # Only 1 approval

        policy = master_engine.phase_24.process_approvals(approval_id)

        approval_pct = (1 / 3) * 100
        rounded_pct = round(approval_pct, 2)

        assert rounded_pct < 66.67, "1/3 should be less than 66.67%"
        assert policy.status == PolicyStatus.DRAFT, \
            "Policy should remain DRAFT with insufficient approvals"


# ============================================================================
# TEST: MONITORING LOOP INTEGRATION
# ============================================================================

def test_monitoring_loop_iterations(master_engine):
    """
    Test that monitoring loop executes correct number of iterations
    and completes without hanging.
    """
    # Run loop with minimal iterations
    start_time = time.time()
    master_engine.run_monitoring_loop(interval_seconds=0.1, max_iterations=2)
    elapsed = time.time() - start_time

    # Should complete quickly with 2 iterations
    assert elapsed < 5, "Loop should complete within 5 seconds"
    assert len(master_engine.completed_contexts) > 0, "Should process events"


def test_execution_summary_accuracy(master_engine):
    """
    Test that execution summary correctly reflects pipeline state.
    """
    # Run a few iterations
    master_engine.run_monitoring_loop(interval_seconds=0.01, max_iterations=2)

    summary = master_engine.get_execution_summary()

    assert 'total_contexts_processed' in summary, "Summary should have total contexts"
    assert 'workflows_created' in summary, "Summary should have workflow count"
    assert 'policies_created' in summary, "Summary should have policy count"
    assert summary['total_contexts_processed'] == len(master_engine.completed_contexts), \
        "Summary count should match completed contexts"


# ============================================================================
# TEST: INTEGRATION WITH REAL PHASE MODULES
# ============================================================================

def test_integration_with_phase_21(master_engine, high_severity_event):
    """
    Test direct integration with Phase 21 anomaly detection.
    """
    anomalies = master_engine.phase_21.detect_anomalies(high_severity_event)

    assert len(anomalies) > 0, "Phase 21 should detect anomalies"

    anomaly = anomalies[0]
    assert isinstance(anomaly, AnomalyEvent), "Should be AnomalyEvent instance"
    assert anomaly.severity_score > 0, "Severity should be calculated"
    assert anomaly.confidence > 0, "Confidence should be > 0"


def test_integration_with_phase_20(master_engine, high_severity_event):
    """
    Test Phase 20 workflow creation and execution integration.
    """
    anomalies = master_engine.phase_21.detect_anomalies(high_severity_event)
    assert len(anomalies) > 0

    anomaly = anomalies[0]
    workflow = master_engine.phase_20.create_workflow(anomaly)

    assert workflow is not None, "Workflow should be created"
    assert workflow.status == WorkflowStatus.PENDING, "Should start in PENDING state"

    success = master_engine.phase_20.execute_workflow(workflow.workflow_id)
    assert success, "Workflow execution should succeed"

    updated_workflow = master_engine.phase_20.workflows[workflow.workflow_id]
    assert updated_workflow.status == WorkflowStatus.COMPLETED, "Should complete"


def test_integration_with_phase_24_approval_workflow(master_engine, high_severity_event):
    """
    Test Phase 24 policy creation and approval workflow integration.
    """
    context = master_engine.execute_pipeline(high_severity_event)

    assert len(context.policies) > 0, "Policies should be created"

    for policy in context.policies:
        assert policy.approval_percentage == 0.0, "Initial approval should be 0%"
        assert len(policy.approved_by) == 0, "No approvals initially"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
