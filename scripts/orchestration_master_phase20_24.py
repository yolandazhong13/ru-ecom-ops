"""
orchestration_master_phase20-24.py
Master orchestration script implementing integrated 5-phase security pipeline
with continuous monitoring, sequential execution, and cross-phase data passing.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue
from threading import Lock
from abc import ABC, abstractmethod

# Import phase modules
# from phase20 import OrchestrationEngine, WorkflowStatus, ActionType
# from phase21 import ThreatPredictionEngine, AnomalyEvent, AnomalyType
# from phase22 import SecurityRiskQuantificationEngine, RiskLevel
# from phase23 import ComplianceAutomationEngine, ComplianceFramework
# from phase24 import PolicyGovernanceEngine, PolicyStatus

# P0 Control System imports
try:
    from p0_control_integration import P0ControlIntegration
    from p0_approval_ledger import (
        P0ControlledActionHandler,
        ApprovalGateConfig,
        ApprovalRejectedError,
        ApprovalTimeoutError,
    )
    P0_CONTROL_AVAILABLE = True
except ImportError:
    P0_CONTROL_AVAILABLE = False
    logger = logging.getLogger(__name__)

# Phase 24 real governance system (for P0 control integration)
try:
    from policy_governance_phase24 import PolicyGovernanceSystem
    POLICY_GOVERNANCE_AVAILABLE = True
except ImportError:
    POLICY_GOVERNANCE_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ACTION HANDLER INTERFACE FOR P0 CONTROL INTEGRATION
# ============================================================================

class ActionHandler(ABC):
    """Abstract base for action handlers integrated with P0 control system.

    Handlers must implement execute() and verify() methods to support
    P0ControlledActionHandler wrapping.
    """

    @abstractmethod
    def execute(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action.

        Args:
            content: Action parameters

        Returns:
            Execution result dict with keys:
                - execution_status: "success" or "failed"
                - action_result: Action-specific result data
                - timestamp: Execution timestamp
        """
        pass

    @abstractmethod
    def verify(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify execution result.

        Args:
            result: Execution result from execute()

        Returns:
            Verification result dict with keys:
                - verified: bool
                - evidence: dict with verification details
        """
        pass


class DefaultActionHandler(ActionHandler):
    """Default action handler for orchestration actions."""

    def __init__(self, action_type: str):
        self.action_type = action_type

    def execute(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action (simulation for now)."""
        return {
            "execution_status": "success",
            "action_result": {
                "action_type": self.action_type,
                "content": content,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def verify(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify execution result."""
        return {
            "verified": result.get("execution_status") == "success",
            "evidence": {
                "action_type": self.action_type,
                "result_keys": list(result.keys()),
            },
        }


# ============================================================================
# PHASE 21: THREAT PREDICTION INTERFACES
# ============================================================================

class AnomalyType(Enum):
    BEHAVIORAL = "behavioral"
    VOLUMETRIC = "volumetric"
    PROTOCOL = "protocol"
    STATISTICAL = "statistical"
    TEMPORAL = "temporal"
    CONTEXTUAL = "contextual"
    ZERO_DAY = "zero_day"
    INSIDER_THREAT = "insider_threat"


@dataclass
class AnomalyEvent:
    event_id: str
    timestamp: datetime
    source_ip: str
    destination_ip: str
    user_id: str
    event_type: str
    anomaly_type: AnomalyType
    severity_score: float  # 0-100
    confidence: float  # 0-1
    baseline_deviation: float
    contextual_factors: Dict
    related_events: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'source_ip': self.source_ip,
            'destination_ip': self.destination_ip,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'anomaly_type': self.anomaly_type.value,
            'severity_score': self.severity_score,
            'confidence': self.confidence,
            'baseline_deviation': self.baseline_deviation,
            'contextual_factors': self.contextual_factors,
            'related_events': self.related_events
        }


class ThreatPredictionEngine:
    """Simulates Phase 21: Threat Prediction & Anomaly Detection"""

    _anomaly_counter = 0  # Class-level counter for unique event IDs

    def __init__(self):
        self.baseline_threshold = 0.80  # 80% confidence
        self.std_dev_multiplier = 2.5
        self.anomaly_buffer = []

    def detect_anomalies(self, event_data: Dict) -> List[AnomalyEvent]:
        """Generate anomalies with severity scores for orchestration routing"""
        anomalies = []

        # Simulate anomaly detection from event_data
        if event_data.get('volumetric_spike', 0) > self.std_dev_multiplier:
            # Increment counter to ensure unique event IDs
            ThreatPredictionEngine._anomaly_counter += 1
            anomaly = AnomalyEvent(
                event_id=f"ANM-{int(time.time()*1000)}-{ThreatPredictionEngine._anomaly_counter}",
                timestamp=datetime.now(),
                source_ip=event_data.get('source_ip', '0.0.0.0'),
                destination_ip=event_data.get('destination_ip', '0.0.0.0'),
                user_id=event_data.get('user_id', 'unknown'),
                event_type=event_data.get('event_type', 'network'),
                anomaly_type=AnomalyType.VOLUMETRIC,
                severity_score=min(100, event_data.get('volumetric_spike', 50) * 15),
                confidence=min(1.0, event_data.get('confidence', 0.85)),
                baseline_deviation=event_data.get('volumetric_spike', 0),
                contextual_factors={'alert_source': 'automated_detection'},
                related_events=[]
            )
            anomalies.append(anomaly)

        return anomalies


# ============================================================================
# SEVERITY LEVEL CONVERSION: STRING TO NUMERIC
# ============================================================================

def severity_to_numeric(severity_level: str) -> int:
    """Convert severity level string to numeric value for P0 gate comparisons.

    Maps severity levels used by OrchestrationEngine (STRING) to numeric values
    required by P0 control system (INT) for approval gate threshold checks.

    Args:
        severity_level: String severity level ("CRITICAL", "HIGH", "MEDIUM")

    Returns:
        Numeric severity (0-100)
    """
    severity_mapping = {
        "CRITICAL": 80,
        "HIGH": 50,
        "MEDIUM": 0,
    }
    return severity_mapping.get(severity_level, 0)


# ============================================================================
# PHASE 20: SOAR ORCHESTRATION INTERFACES
# ============================================================================

class ActionType(Enum):
    ISOLATE_ASSET = "isolate_asset"
    BLOCK_IP = "block_ip"
    REVOKE_TOKEN = "revoke_token"
    NOTIFY_USER = "notify_user"
    ESCALATE_INCIDENT = "escalate_incident"
    COLLECT_EVIDENCE = "collect_evidence"
    EXECUTE_COMMAND = "execute_command"
    QUERY_LOGS = "query_logs"
    UPDATE_FIREWALL = "update_firewall"
    DISABLE_ACCOUNT = "disable_account"
    SNAPSHOT_VM = "snapshot_vm"
    ISOLATE_NETWORK = "isolate_network"


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowAction:
    action_id: str
    action_type: ActionType
    parameters: Dict
    status: str = "pending"
    execution_time: Optional[float] = None
    completion_time: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Workflow:
    workflow_id: str
    timestamp: datetime
    status: WorkflowStatus
    severity_level: str
    triggered_by_event: str
    actions: List[WorkflowAction] = field(default_factory=list)
    audit_trail: List[Dict] = field(default_factory=list)
    mitigation_status: str = "pending"


class OrchestrationEngine:
    """Simulates Phase 20: SOAR Orchestration Engine"""

    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.workflow_counter = 0
        self.execution_history: List[Dict] = []
        self.automation_rules: List[Dict] = []

        # Initialize P0 control system if available
        self.policy_governance_system = None
        self.p0_control = None

        if POLICY_GOVERNANCE_AVAILABLE and P0_CONTROL_AVAILABLE:
            try:
                self.policy_governance_system = PolicyGovernanceSystem()
                self.p0_control = P0ControlIntegration(self.policy_governance_system)
                logger.info("✓ P0 Control System initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize P0 Control System: {e}")
                self.policy_governance_system = None
                self.p0_control = None

    def create_workflow(self, anomaly: AnomalyEvent) -> Workflow:
        """Create workflow from anomaly event"""
        self.workflow_counter += 1
        workflow_id = f"WF-{self.workflow_counter:06d}"

        # Determine severity level from anomaly
        if anomaly.severity_score >= 80:
            severity_level = "CRITICAL"
            actions = [
                ActionType.ISOLATE_ASSET,
                ActionType.COLLECT_EVIDENCE,
                ActionType.ESCALATE_INCIDENT
            ]
        elif anomaly.severity_score >= 50:
            severity_level = "HIGH"
            actions = [
                ActionType.BLOCK_IP,
                ActionType.QUERY_LOGS,
                ActionType.NOTIFY_USER
            ]
        else:
            severity_level = "MEDIUM"
            actions = [ActionType.QUERY_LOGS, ActionType.NOTIFY_USER]

        workflow_actions = [
            WorkflowAction(
                action_id=f"ACT-{i:04d}",
                action_type=action,
                parameters={'anomaly_event': anomaly.event_id}
            )
            for i, action in enumerate(actions)
        ]

        workflow = Workflow(
            workflow_id=workflow_id,
            timestamp=datetime.now(),
            status=WorkflowStatus.PENDING,
            severity_level=severity_level,
            triggered_by_event=anomaly.event_id,
            actions=workflow_actions,
            audit_trail=[{
                'timestamp': datetime.now().isoformat(),
                'event': 'workflow_created',
                'details': f'From anomaly {anomaly.event_id}'
            }]
        )

        self.workflows[workflow_id] = workflow
        return workflow

    def execute_workflow(self, workflow_id: str) -> bool:
        """Execute workflow with P0 approval gate for critical incidents.

        Implements P0OrchestrationPattern:
        - For severity >= 50: wraps handler with P0ControlledActionHandler
        - Polls for approval decisions with timeout
        - Records approval to ledger and PROGRESS.md
        - For severity < 50: executes without gate
        """
        if workflow_id not in self.workflows:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        workflow = self.workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING

        # Convert severity from STRING to NUMERIC for P0 gate threshold check
        severity_numeric = severity_to_numeric(workflow.severity_level)
        logger.info(f"Workflow {workflow_id}: severity_level={workflow.severity_level} (numeric: {severity_numeric})")

        try:
            for action in workflow.actions:
                action.status = "in_progress"
                action.execution_time = time.time()

                # P0OrchestrationPattern: Conditionally apply approval gate
                try:
                    if severity_numeric >= 50 and self.p0_control is not None:
                        # P0 gate required: wrap handler with approval gate
                        logger.info(f"P0 gate REQUIRED for workflow {workflow_id} (severity {severity_numeric} >= 50)")

                        # Create action handler
                        action_handler = DefaultActionHandler(action.action_type.value)

                        # Define approvers (from P0 control system or config)
                        approvers = ["alice@company.com", "bob@company.com", "charlie@company.com"]

                        # Wrap with P0ControlledActionHandler
                        wrapped_handler = self.p0_control.wrap_action_handler(
                            handler=action_handler,
                            task_id=workflow_id,
                            severity_level=severity_numeric,
                            approvers=approvers,
                        )

                        # Execute with approval gate (blocks until approved or timeout)
                        logger.info(f"Executing action {action.action_id} with P0 approval gate")
                        result = wrapped_handler.execute(action.parameters)

                        # Record approval decision to ledger
                        self.p0_control.record_approval_decision(workflow_id, wrapped_handler)
                        logger.info(f"P0 approval recorded for workflow {workflow_id}")

                        action.result = result
                        action.status = "success"

                    else:
                        # No gate required: execute without approval
                        if severity_numeric < 50:
                            logger.info(f"P0 gate NOT required for workflow {workflow_id} (severity {severity_numeric} < 50)")
                        else:
                            logger.warning(f"P0 control not initialized, executing without gate")

                        # Create action handler
                        action_handler = DefaultActionHandler(action.action_type.value)

                        # Execute handler
                        result = action_handler.execute(action.parameters)

                        # Verify result
                        verification_result = action_handler.verify(result)

                        action.result = result
                        action.status = "success" if verification_result.get("verified", False) else "failed"

                except ApprovalRejectedError as e:
                    logger.error(f"P0 approval REJECTED for workflow {workflow_id}: {e}")
                    action.status = "failed"
                    action.error = f"Approval rejected: {str(e)}"
                    workflow.status = WorkflowStatus.FAILED
                    workflow.audit_trail.append({
                        'timestamp': datetime.now().isoformat(),
                        'event': 'p0_approval_rejected',
                        'action_id': action.action_id,
                        'reason': str(e)
                    })
                    return False

                except ApprovalTimeoutError as e:
                    logger.error(f"P0 approval TIMEOUT for workflow {workflow_id}: {e}")
                    action.status = "failed"
                    action.error = f"Approval timeout: {str(e)}"
                    workflow.status = WorkflowStatus.FAILED
                    workflow.audit_trail.append({
                        'timestamp': datetime.now().isoformat(),
                        'event': 'p0_approval_timeout',
                        'action_id': action.action_id,
                        'reason': str(e)
                    })
                    return False

                action.completion_time = datetime.now()

            workflow.status = WorkflowStatus.COMPLETED
            workflow.mitigation_status = "completed"
            workflow.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'workflow_completed',
                'actions_executed': len(workflow.actions),
                'p0_gate_applied': severity_numeric >= 50
            })

            logger.info(f"Workflow {workflow_id} completed successfully")
            return True

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'workflow_failed',
                'error': str(e)
            })
            logger.error(f"Workflow {workflow_id} failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _execute_action(self, action: WorkflowAction) -> bool:
        """Execute individual action.

        NOTE: This method is now deprecated in favor of inline handler execution
        in execute_workflow(). Kept for backward compatibility.
        """
        action.execution_time = time.time()

        # Create action handler
        action_handler = DefaultActionHandler(action.action_type.value)

        # Execute action
        result = action_handler.execute(action.parameters)

        # Verify result
        verification_result = action_handler.verify(result)

        # Store result
        action.result = result

        # Return success based on verification
        return verification_result.get("verified", False)

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow status details"""
        if workflow_id not in self.workflows:
            return None

        workflow = self.workflows[workflow_id]
        return {
            'workflow_id': workflow_id,
            'status': workflow.status.value,
            'severity_level': workflow.severity_level,
            'triggered_by': workflow.triggered_by_event,
            'actions_count': len(workflow.actions),
            'completed_actions': sum(1 for a in workflow.actions if a.status == "success"),
            'mitigation_status': workflow.mitigation_status,
            'audit_trail': workflow.audit_trail
        }


# ============================================================================
# PHASE 22: SECURITY RISK QUANTIFICATION INTERFACES
# ============================================================================

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    risk_id: str
    asset_type: str
    asset_value: float
    residual_risk_score: float  # Post-mitigation
    risk_level: RiskLevel
    financial_impact: float
    workflow_id: str
    timestamp: datetime
    audit_trail: List[Dict] = field(default_factory=list)


class SecurityRiskQuantificationEngine:
    """Simulates Phase 22: Security Risk Quantification"""

    def __init__(self):
        self.asset_database: Dict[str, Dict] = {
            'database_prod': {
                'annual_revenue': 5000000,
                'replacement_cost': 500000,
                'sensitivity': 0.95
            },
            'app_frontend': {
                'annual_revenue': 3000000,
                'replacement_cost': 200000,
                'sensitivity': 0.70
            }
        }

    def calculate_asset_value(self, asset_type: str) -> float:
        """Calculate asset value using formula"""
        if asset_type not in self.asset_database:
            return 0.0

        asset = self.asset_database[asset_type]
        revenue_weight = min(0.5 * asset['annual_revenue'], 1000000)
        replacement_weight = 0.3 * asset['replacement_cost']
        sensitivity_weight = 0.2 * asset['sensitivity'] * 100000

        return revenue_weight + replacement_weight + sensitivity_weight

    def assess_risk(self, workflow: Workflow, anomaly: AnomalyEvent) -> RiskAssessment:
        """Assess residual risk post-mitigation"""
        # Map anomaly to primary asset
        asset_type = 'database_prod' if 'database' in str(anomaly.anomaly_type) else 'app_frontend'

        asset_value = self.calculate_asset_value(asset_type)

        # Calculate residual risk (post-mitigation):
        # severity_score * (1 - mitigation_factor)
        # Use conservative 10% mitigation: even completed workflows reduce severity by only 10%
        mitigation_factor = 0.1 if workflow.status == WorkflowStatus.COMPLETED else 0.0
        residual_risk = anomaly.severity_score * (1 - mitigation_factor)

        # Determine risk level
        if residual_risk > 75:
            risk_level = RiskLevel.CRITICAL
        elif residual_risk > 50:
            risk_level = RiskLevel.HIGH
        elif residual_risk > 25:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        financial_impact = (residual_risk / 100) * asset_value

        risk_id = f"RISK-{int(time.time()*1000)}"

        return RiskAssessment(
            risk_id=risk_id,
            asset_type=asset_type,
            asset_value=asset_value,
            residual_risk_score=residual_risk,
            risk_level=risk_level,
            financial_impact=financial_impact,
            workflow_id=workflow.workflow_id,
            timestamp=datetime.now(),
            audit_trail=[{
                'timestamp': datetime.now().isoformat(),
                'event': 'risk_assessed',
                'methodology': 'post_mitigation_calculation'
            }]
        )


# ============================================================================
# PHASE 23: COMPLIANCE AUTOMATION INTERFACES
# ============================================================================

class ComplianceFramework(Enum):
    SOC2_TYPE2 = "soc2_type2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    CCPA = "ccpa"
    NIST_CSF = "nist_csf"
    CIS_CONTROLS = "cis_controls"


@dataclass
class ComplianceGap:
    framework: ComplianceFramework
    control_id: str
    current_status: str
    gap_description: str
    risk_exposure: str


@dataclass
class RemediationPlan:
    plan_id: str
    framework: ComplianceFramework
    gaps: List[ComplianceGap]
    priority_mapping: Dict[str, int]  # Maps risk level to priority
    estimated_effort_hours: float
    timestamp: datetime


class ComplianceAutomationEngine:
    """Simulates Phase 23: Compliance Automation"""

    def __init__(self):
        self.framework_controls: Dict[ComplianceFramework, List[str]] = {
            ComplianceFramework.SOC2_TYPE2: ['CC6.1', 'CC6.2', 'CC7.2'],
            ComplianceFramework.ISO27001: ['A.12.4.1', 'A.13.1.1'],
            ComplianceFramework.HIPAA: ['RA-3', 'SI-4'],
            ComplianceFramework.PCI_DSS: ['10.2', '12.3'],
            ComplianceFramework.GDPR: ['Article 33', 'Article 34'],
            ComplianceFramework.CCPA: ['Section 1798.150'],
            ComplianceFramework.NIST_CSF: ['DE.AE-1', 'DE.AE-2'],
            ComplianceFramework.CIS_CONTROLS: ['CIS 6.1', 'CIS 19.7']
        }

    def analyze_compliance_gaps(self, risk_assessment: RiskAssessment) -> List[RemediationPlan]:
        """Map risk assessment to compliance gaps and generate remediation plans"""
        remediation_plans = []

        for framework in ComplianceFramework:
            gaps = []

            # Map risk level to compliance controls
            if risk_assessment.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                # High-risk events trigger all security-related controls
                affected_controls = self.framework_controls.get(framework, [])

                for control_id in affected_controls:
                    gap = ComplianceGap(
                        framework=framework,
                        control_id=control_id,
                        current_status='non_compliant',
                        gap_description=f'Control {control_id} requires remediation due to {risk_assessment.risk_id}',
                        risk_exposure=risk_assessment.risk_level.value
                    )
                    gaps.append(gap)

            if gaps:
                plan = RemediationPlan(
                    plan_id=f"REMEDIATION-{framework.value}-{int(time.time())}",
                    framework=framework,
                    gaps=gaps,
                    priority_mapping={
                        'CRITICAL': 1,
                        'HIGH': 2,
                        'MEDIUM': 3,
                        'LOW': 4
                    },
                    estimated_effort_hours=len(gaps) * 2.5,
                    timestamp=datetime.now()
                )
                remediation_plans.append(plan)

        return remediation_plans


# ============================================================================
# PHASE 24: POLICY GOVERNANCE INTERFACES
# ============================================================================

class PolicyStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    RETIRED = "retired"


@dataclass
class PolicyVersion:
    policy_id: str
    version_number: int
    status: PolicyStatus
    content: Dict
    created_at: datetime
    approved_by: List[str] = field(default_factory=list)
    approval_percentage: float = 0.0  # With round(...,2) precision
    approver_count: int = 0
    audit_trail: List[Dict] = field(default_factory=list)


class PolicyGovernanceEngine:
    """Simulates Phase 24: Policy Governance"""

    def __init__(self):
        self.policies: Dict[str, List[PolicyVersion]] = {}
        self.approval_workflows: Dict[str, Dict] = {}
        self.approver_list = ['security_lead', 'compliance_officer', 'ciso']

    def create_policy_from_remediation(self, remediation_plan: RemediationPlan) -> PolicyVersion:
        """Create policy from remediation plan"""
        policy_id = f"POL-{remediation_plan.plan_id}"

        policy = PolicyVersion(
            policy_id=policy_id,
            version_number=1,
            status=PolicyStatus.REVIEW,
            content={
                'framework': remediation_plan.framework.value,
                'gaps': [
                    {
                        'control': g.control_id,
                        'description': g.gap_description,
                        'exposure': g.risk_exposure
                    }
                    for g in remediation_plan.gaps
                ],
                'effort_hours': remediation_plan.estimated_effort_hours
            },
            created_at=datetime.now(),
            audit_trail=[{
                'timestamp': datetime.now().isoformat(),
                'event': 'policy_created',
                'source': 'remediation_plan'
            }]
        )

        if policy_id not in self.policies:
            self.policies[policy_id] = []
        self.policies[policy_id].append(policy)

        # Create approval workflow
        approval_id = f"APR-{int(time.time()*1000)}"
        self.approval_workflows[approval_id] = {
            'policy_id': policy_id,
            'approvers': self.approver_list.copy(),
            'approved_by': [],
            'status': 'pending',
            'created_at': datetime.now()
        }

        return policy

    def process_approvals(self, approval_id: str) -> Optional[PolicyVersion]:
        """Process policy approvals and update status"""
        if approval_id not in self.approval_workflows:
            return None

        workflow = self.approval_workflows[approval_id]
        policy_id = workflow['policy_id']

        # If approved_by not already set, simulate approval collection
        if not workflow['approved_by']:
            approved_count = min(len(workflow['approvers']), 2)  # Assume 2/3 approve
            workflow['approved_by'] = workflow['approvers'][:approved_count]

        # Calculate approval percentage with round(...,2) precision
        approval_percentage = round((len(workflow['approved_by']) / len(workflow['approvers'])) * 100, 2)

        # Get latest policy version
        policy = self.policies[policy_id][-1]
        policy.approved_by = workflow['approved_by']
        policy.approval_percentage = approval_percentage
        policy.approver_count = len(workflow['approvers'])

        if approval_percentage >= 66.67:  # Meets threshold (2/3)
            policy.status = PolicyStatus.APPROVED
            workflow['status'] = 'approved'
            policy.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'policy_approved',
                'approval_percentage': approval_percentage,
                'approved_by': workflow['approved_by']
            })
        else:
            policy.status = PolicyStatus.DRAFT
            workflow['status'] = 'pending_more_approvals'
            policy.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'policy_awaiting_approvals',
                'approval_percentage': approval_percentage
            })

        return policy


# ============================================================================
# MASTER ORCHESTRATION LOOP
# ============================================================================

@dataclass
class OrchestrationContext:
    """Context object for passing data through pipeline"""
    anomaly: Optional[AnomalyEvent] = None
    workflow: Optional[Workflow] = None
    risk_assessment: Optional[RiskAssessment] = None
    remediation_plans: List[RemediationPlan] = field(default_factory=list)
    policies: List[PolicyVersion] = field(default_factory=list)
    approval_workflows: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    audit_trail: List[Dict] = field(default_factory=list)


class MasterOrchestrationEngine:
    """Master orchestration engine coordinating Phases 20-24"""

    def __init__(self):
        self.phase_21 = ThreatPredictionEngine()
        self.phase_20 = OrchestrationEngine()
        self.phase_22 = SecurityRiskQuantificationEngine()
        self.phase_23 = ComplianceAutomationEngine()
        self.phase_24 = PolicyGovernanceEngine()

        self.execution_queue: Queue = Queue()
        self.completed_contexts: List[OrchestrationContext] = []
        self.lock = Lock()
        self.monitoring_active = True

    def execute_pipeline(self, event_data: Dict) -> OrchestrationContext:
        """Execute complete 5-phase pipeline"""
        context = OrchestrationContext()
        context.timestamp = datetime.now()

        try:
            # PHASE 21: Detect anomalies
            logger.info("PHASE 21: Detecting anomalies...")
            anomalies = self.phase_21.detect_anomalies(event_data)

            if not anomalies:
                logger.info("No anomalies detected")
                return context

            context.anomaly = anomalies[0]  # Process first anomaly
            context.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'phase': 21,
                'event': 'anomaly_detected',
                'severity': context.anomaly.severity_score
            })

            # PHASE 20: Orchestrate response
            logger.info(f"PHASE 20: Orchestrating response to anomaly {context.anomaly.event_id}")

            if context.anomaly.severity_score >= 50:
                # Automatic orchestration for high-severity anomalies
                context.workflow = self.phase_20.create_workflow(context.anomaly)
                success = self.phase_20.execute_workflow(context.workflow.workflow_id)

                context.audit_trail.append({
                    'timestamp': datetime.now().isoformat(),
                    'phase': 20,
                    'event': 'workflow_executed' if success else 'workflow_failed',
                    'workflow_id': context.workflow.workflow_id
                })
            else:
                # Manual review for low-severity anomalies
                logger.info(f"Anomaly {context.anomaly.event_id} requires manual review")
                context.audit_trail.append({
                    'timestamp': datetime.now().isoformat(),
                    'phase': 20,
                    'event': 'manual_review_required',
                    'severity': context.anomaly.severity_score
                })

            # PHASE 22: Quantify risk
            if context.workflow:
                logger.info(f"PHASE 22: Quantifying risk for workflow {context.workflow.workflow_id}")
                context.risk_assessment = self.phase_22.assess_risk(context.workflow, context.anomaly)

                context.audit_trail.append({
                    'timestamp': datetime.now().isoformat(),
                    'phase': 22,
                    'event': 'risk_quantified',
                    'risk_level': context.risk_assessment.risk_level.value,
                    'financial_impact': context.risk_assessment.financial_impact
                })

                # PHASE 23: Analyze compliance gaps
                logger.info(f"PHASE 23: Analyzing compliance gaps for risk {context.risk_assessment.risk_id}")
                context.remediation_plans = self.phase_23.analyze_compliance_gaps(context.risk_assessment)

                context.audit_trail.append({
                    'timestamp': datetime.now().isoformat(),
                    'phase': 23,
                    'event': 'compliance_gaps_analyzed',
                    'remediation_plans': len(context.remediation_plans)
                })

                # PHASE 24: Create policies and approvals
                logger.info("PHASE 24: Creating approval-required policies...")
                for plan in context.remediation_plans:
                    policy = self.phase_24.create_policy_from_remediation(plan)
                    context.policies.append(policy)

                    # Find approval workflow ID (last created)
                    approval_ids = list(self.phase_24.approval_workflows.keys())
                    if approval_ids:
                        context.approval_workflows.append(approval_ids[-1])

                context.audit_trail.append({
                    'timestamp': datetime.now().isoformat(),
                    'phase': 24,
                    'event': 'policies_created',
                    'policy_count': len(context.policies)
                })

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}")
            context.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'event': 'pipeline_error',
                'error': str(e)
            })

        # Store completed context for approval tracking
        with self.lock:
            self.completed_contexts.append(context)

        return context

    def process_approvals_loop(self) -> List[OrchestrationContext]:
        """Continuous loop for processing policy approvals"""
        approved_contexts = []

        for approval_id in list(self.phase_24.approval_workflows.keys()):
            workflow = self.phase_24.approval_workflows[approval_id]

            if workflow['status'] in ['pending', 'pending_more_approvals']:
                policy = self.phase_24.process_approvals(approval_id)

                if policy and policy.status == PolicyStatus.APPROVED:
                    logger.info(f"Policy {policy.policy_id} approved with {policy.approval_percentage}%")

                    # Find and re-execute related workflows
                    for ctx in self.completed_contexts:
                        if ctx.workflow and policy.policy_id in ctx.workflow.workflow_id:
                            logger.info(f"Re-executing workflow {ctx.workflow.workflow_id} after policy approval")
                            self.phase_20.execute_workflow(ctx.workflow.workflow_id)
                            approved_contexts.append(ctx)

        return approved_contexts

    def run_monitoring_loop(self, interval_seconds: int = 60, max_iterations: int = None):
        """Main monitoring loop with sequential phase execution"""
        iteration = 0

        while self.monitoring_active and (max_iterations is None or iteration < max_iterations):
            try:
                iteration += 1
                logger.info(f"=== Monitoring iteration {iteration} ===")

                # Simulate event generation
                simulated_event = {
                    'source_ip': '192.168.1.100',
                    'destination_ip': '10.0.0.1',
                    'user_id': 'user_12345',
                    'event_type': 'network_traffic',
                    'volumetric_spike': 3.5,
                    'confidence': 0.92
                }

                # Execute 5-phase pipeline
                context = self.execute_pipeline(simulated_event)

                if context.anomaly:
                    with self.lock:
                        self.completed_contexts.append(context)

                # Process approval workflows
                approved = self.process_approvals_loop()
                logger.info(f"Approved contexts in this iteration: {len(approved)}")

                # Wait before next iteration
                if interval_seconds > 0 and (max_iterations is None or iteration < max_iterations):
                    logger.info(f"Sleeping for {interval_seconds}s until next monitoring cycle")
                    time.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(interval_seconds)

        logger.info(f"Monitoring loop completed after {iteration} iterations")

    def get_execution_summary(self) -> Dict:
        """Get comprehensive execution summary"""
        with self.lock:
            total_contexts = len(self.completed_contexts)
            contexts_with_workflows = sum(1 for c in self.completed_contexts if c.workflow)
            contexts_with_policies = sum(1 for c in self.completed_contexts if c.policies)

            return {
                'total_contexts_processed': total_contexts,
                'contexts_with_workflows': contexts_with_workflows,
                'contexts_with_policies': contexts_with_policies,
                'workflows_created': len(self.phase_20.workflows),
                'policies_created': len(self.phase_24.policies),
                'approval_workflows': len(self.phase_24.approval_workflows),
                'phase_20_status': {
                    'total_workflows': len(self.phase_20.workflows),
                    'completed': sum(1 for w in self.phase_20.workflows.values()
                                   if w.status == WorkflowStatus.COMPLETED)
                },
                'phase_24_status': {
                    'total_policies': sum(len(versions) for versions in self.phase_24.policies.values()),
                    'approved_policies': sum(
                        sum(1 for v in versions if v.status == PolicyStatus.APPROVED)
                        for versions in self.phase_24.policies.values()
                    )
                }
            }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    engine = MasterOrchestrationEngine()

    # Run monitoring loop for demonstration (3 iterations with 2s interval)
    logger.info("Starting Master Orchestration Engine - Phases 20-24 Pipeline")
    engine.run_monitoring_loop(interval_seconds=2, max_iterations=3)

    # Print final execution summary
    summary = engine.get_execution_summary()
    logger.info("=== FINAL EXECUTION SUMMARY ===")
    logger.info(json.dumps(summary, indent=2))
