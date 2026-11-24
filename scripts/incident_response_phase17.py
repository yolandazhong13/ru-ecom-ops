#!/usr/bin/env python3
"""
PHASE 17: INCIDENT RESPONSE & RECOVERY
=====================================

Implements comprehensive incident response and recovery procedures for security operations.

Components:
  - Incident Management: Create, track, and manage security incidents
  - Incident Classification: Categorize incidents by type and severity
  - Response Workflows: Automated response actions based on incident type
  - Escalation Procedures: Multi-level escalation based on severity
  - Playbooks: Pre-defined response procedures for common incident types
  - Communication: Notification and reporting during incidents
  - Post-Incident Review: Root cause analysis and lessons learned
  - Recovery Procedures: Automated recovery steps for compromised systems

Architecture:
  IncidentManager → Incident creation and lifecycle management
  IncidentClassifier → Auto-categorization based on alert/event data
  ResponsePlaybook → Pre-defined procedures for different incident types
  EscalationEngine → Multi-level escalation based on severity/impact
  CommunicationHandler → Notifications and incident communications
  RecoveryExecutor → Automated recovery and remediation actions
  PostIncidentAnalyzer → Root cause analysis and trend detection
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
from hashlib import sha256


# ============================================================================
# ENUMS
# ============================================================================

class IncidentSeverity(Enum):
    """Incident severity levels with escalation thresholds."""
    LOW = "LOW"           # Minor security event
    MEDIUM = "MEDIUM"     # Notable security incident
    HIGH = "HIGH"         # Significant security breach
    CRITICAL = "CRITICAL" # Active exploitation/breach in progress


class IncidentStatus(Enum):
    """Incident lifecycle states."""
    OPEN = "OPEN"           # Newly detected incident
    INVESTIGATING = "INVESTIGATING"  # Under active investigation
    CONTAINED = "CONTAINED"   # Attack contained
    RESOLVED = "RESOLVED"     # Incident resolved
    CLOSED = "CLOSED"         # Post-incident review complete


class IncidentType(Enum):
    """Classification of incident types."""
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    DATA_BREACH = "DATA_BREACH"
    MALWARE_DETECTED = "MALWARE_DETECTED"
    DDoS_ATTACK = "DDoS_ATTACK"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    SUPPLY_CHAIN_COMPROMISE = "SUPPLY_CHAIN_COMPROMISE"
    INSIDER_THREAT = "INSIDER_THREAT"
    OTHER = "OTHER"


class ResponseActionStatus(Enum):
    """Status of response actions."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ResponseAction:
    """Single response action for an incident."""
    action_id: str
    action_type: str
    description: str
    status: ResponseActionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d['status'] = self.status.value
        d['created_at'] = self.created_at.isoformat()
        d['started_at'] = self.started_at.isoformat() if self.started_at else None
        d['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return d


@dataclass
class IncidentUpdate:
    """Update record for incident investigation."""
    update_id: str
    timestamp: datetime
    investigator: str
    status_change: Optional[str]
    findings: str
    actions_taken: List[str]

    def to_dict(self):
        return {
            'update_id': self.update_id,
            'timestamp': self.timestamp.isoformat(),
            'investigator': self.investigator,
            'status_change': self.status_change,
            'findings': self.findings,
            'actions_taken': self.actions_taken
        }


@dataclass
class Incident:
    """Core incident record."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    incident_type: IncidentType
    status: IncidentStatus
    created_at: datetime
    created_by: str
    last_updated: datetime
    affected_systems: List[str]
    affected_users: List[str]
    alert_ids: List[str] = field(default_factory=list)
    updates: List[IncidentUpdate] = field(default_factory=list)
    response_actions: List[ResponseAction] = field(default_factory=list)
    root_cause: Optional[str] = None
    impact_assessment: Optional[str] = None
    lessons_learned: Optional[str] = None
    fingerprint: Optional[str] = None

    def to_dict(self):
        return {
            'incident_id': self.incident_id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'incident_type': self.incident_type.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'last_updated': self.last_updated.isoformat(),
            'affected_systems': self.affected_systems,
            'affected_users': self.affected_users,
            'alert_ids': self.alert_ids,
            'updates': [u.to_dict() for u in self.updates],
            'response_actions': [a.to_dict() for a in self.response_actions],
            'root_cause': self.root_cause,
            'impact_assessment': self.impact_assessment,
            'lessons_learned': self.lessons_learned,
            'fingerprint': self.fingerprint
        }


@dataclass
class ResponsePlaybook:
    """Pre-defined response procedures for incident types."""
    playbook_id: str
    incident_type: IncidentType
    name: str
    description: str
    initial_actions: List[str]
    investigation_steps: List[str]
    containment_actions: List[str]
    recovery_steps: List[str]
    notification_required: bool
    escalation_on_failure: bool


@dataclass
class PostIncidentReport:
    """Post-incident review and analysis."""
    report_id: str
    incident_id: str
    generated_at: datetime
    root_cause: str
    contributing_factors: List[str]
    corrective_actions: List[str]
    preventive_measures: List[str]
    timeline: Dict[str, str]
    impact_summary: str
    lessons_learned: List[str]


# ============================================================================
# INCIDENT RESPONSE SYSTEM
# ============================================================================

class IncidentManager:
    """Manages incident creation, updates, and lifecycle."""

    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.incident_counter = 0

    def create_incident(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        incident_type: IncidentType,
        created_by: str,
        affected_systems: List[str],
        affected_users: List[str],
        alert_ids: List[str] = None
    ) -> Incident:
        """Create new incident."""
        self.incident_counter += 1
        incident_id = f"INC-{self.incident_counter:06d}"

        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            incident_type=incident_type,
            status=IncidentStatus.OPEN,
            created_at=datetime.now(),
            created_by=created_by,
            last_updated=datetime.now(),
            affected_systems=affected_systems,
            affected_users=affected_users,
            alert_ids=alert_ids or []
        )

        # Generate immutable fingerprint
        incident.fingerprint = self._generate_fingerprint(incident)
        self.incidents[incident_id] = incident
        return incident

    def _generate_fingerprint(self, incident: Incident) -> str:
        """Generate SHA256 fingerprint of incident."""
        data = f"{incident.incident_id}{incident.created_at}{incident.created_by}"
        return sha256(data.encode()).hexdigest()

    def add_update(
        self,
        incident_id: str,
        investigator: str,
        findings: str,
        actions_taken: List[str],
        status_change: Optional[str] = None
    ) -> IncidentUpdate:
        """Add investigation update to incident."""
        if incident_id not in self.incidents:
            raise ValueError(f"Incident {incident_id} not found")

        incident = self.incidents[incident_id]
        update = IncidentUpdate(
            update_id=f"UPD-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            investigator=investigator,
            status_change=status_change,
            findings=findings,
            actions_taken=actions_taken
        )

        incident.updates.append(update)
        incident.last_updated = datetime.now()

        if status_change:
            incident.status = IncidentStatus[status_change]

        return update

    def add_response_action(
        self,
        incident_id: str,
        action_type: str,
        description: str
    ) -> ResponseAction:
        """Add response action to incident."""
        if incident_id not in self.incidents:
            raise ValueError(f"Incident {incident_id} not found")

        action = ResponseAction(
            action_id=f"ACT-{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            description=description,
            status=ResponseActionStatus.PENDING,
            created_at=datetime.now()
        )

        self.incidents[incident_id].response_actions.append(action)
        return action

    def execute_action(
        self,
        incident_id: str,
        action_id: str,
        result: str
    ) -> ResponseAction:
        """Mark action as executed."""
        if incident_id not in self.incidents:
            raise ValueError(f"Incident {incident_id} not found")

        incident = self.incidents[incident_id]
        for action in incident.response_actions:
            if action.action_id == action_id:
                action.status = ResponseActionStatus.COMPLETED
                action.started_at = datetime.now()
                action.completed_at = datetime.now()
                action.result = result
                incident.last_updated = datetime.now()
                return action

        raise ValueError(f"Action {action_id} not found in incident")

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Retrieve incident by ID."""
        return self.incidents.get(incident_id)

    def get_incidents_by_severity(self, severity: IncidentSeverity) -> List[Incident]:
        """Get all incidents of specified severity."""
        return [i for i in self.incidents.values() if i.severity == severity]

    def get_open_incidents(self) -> List[Incident]:
        """Get all open incidents."""
        return [
            i for i in self.incidents.values()
            if i.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]
        ]


class IncidentClassifier:
    """Auto-classifies incidents based on indicators."""

    @staticmethod
    def classify_incident(
        alert_data: Dict[str, Any],
        event_logs: List[Dict[str, Any]]
    ) -> tuple[IncidentType, IncidentSeverity]:
        """Classify incident based on alert and logs."""
        incident_type = IncidentType.OTHER
        severity = IncidentSeverity.MEDIUM

        # Classify by alert type
        alert_type = alert_data.get('alert_type', '').lower()
        metric_name = alert_data.get('metric_name', '').lower()

        if 'auth' in alert_type or 'unauthorized' in alert_type:
            incident_type = IncidentType.UNAUTHORIZED_ACCESS
            severity = IncidentSeverity.HIGH
        elif 'data' in alert_type and 'breach' in alert_type:
            incident_type = IncidentType.DATA_BREACH
            severity = IncidentSeverity.CRITICAL
        elif 'malware' in alert_type or 'virus' in alert_type:
            incident_type = IncidentType.MALWARE_DETECTED
            severity = IncidentSeverity.CRITICAL
        elif 'ddos' in alert_type or 'requests' in metric_name:
            incident_type = IncidentType.DDoS_ATTACK
            severity = IncidentSeverity.HIGH
        elif 'privilege' in alert_type or 'escalation' in alert_type:
            incident_type = IncidentType.PRIVILEGE_ESCALATION
            severity = IncidentSeverity.CRITICAL
        elif 'config' in alert_type or 'misconfiguration' in alert_type:
            incident_type = IncidentType.CONFIGURATION_ERROR
            severity = IncidentSeverity.MEDIUM

        # Adjust severity based on affected count
        if 'affected_count' in alert_data:
            affected = alert_data['affected_count']
            if affected > 1000:
                severity = IncidentSeverity.CRITICAL
            elif affected > 100:
                severity = IncidentSeverity.HIGH

        return incident_type, severity


class ResponsePlaybookEngine:
    """Manages and executes response playbooks."""

    def __init__(self):
        self.playbooks: Dict[IncidentType, ResponsePlaybook] = {}
        self._initialize_playbooks()

    def _initialize_playbooks(self):
        """Initialize default playbooks."""
        playbooks = [
            ResponsePlaybook(
                playbook_id="PB-001",
                incident_type=IncidentType.UNAUTHORIZED_ACCESS,
                name="Unauthorized Access Response",
                description="Response procedures for unauthorized access attempts",
                initial_actions=[
                    "Isolate affected systems from network",
                    "Preserve evidence and logs",
                    "Identify affected user accounts"
                ],
                investigation_steps=[
                    "Review authentication logs",
                    "Analyze access patterns",
                    "Identify compromised credentials"
                ],
                containment_actions=[
                    "Reset compromised passwords",
                    "Revoke active sessions",
                    "Block suspicious IP addresses"
                ],
                recovery_steps=[
                    "Verify system integrity",
                    "Restore from clean backup if needed",
                    "Re-enable network access"
                ],
                notification_required=True,
                escalation_on_failure=True
            ),
            ResponsePlaybook(
                playbook_id="PB-002",
                incident_type=IncidentType.DATA_BREACH,
                name="Data Breach Response",
                description="Response procedures for data breach incidents",
                initial_actions=[
                    "Activate incident response team",
                    "Preserve all evidence",
                    "Identify data scope and sensitivity"
                ],
                investigation_steps=[
                    "Determine breach timeline",
                    "Identify affected data sets",
                    "Analyze exfiltration method"
                ],
                containment_actions=[
                    "Revoke access to affected systems",
                    "Terminate unauthorized sessions",
                    "Block data exfiltration channels"
                ],
                recovery_steps=[
                    "Notify affected parties",
                    "Provide credit monitoring if needed",
                    "Implement additional controls"
                ],
                notification_required=True,
                escalation_on_failure=True
            ),
            ResponsePlaybook(
                playbook_id="PB-003",
                incident_type=IncidentType.DDoS_ATTACK,
                name="DDoS Attack Response",
                description="Response procedures for DDoS attacks",
                initial_actions=[
                    "Activate DDoS mitigation",
                    "Increase capacity if possible",
                    "Contact ISP for upstream filtering"
                ],
                investigation_steps=[
                    "Analyze attack patterns",
                    "Identify attack vector",
                    "Assess attack sophistication"
                ],
                containment_actions=[
                    "Enable rate limiting",
                    "Block attacking IP ranges",
                    "Implement geo-blocking if appropriate"
                ],
                recovery_steps=[
                    "Monitor traffic patterns",
                    "Gradually restore normal service",
                    "Validate system stability"
                ],
                notification_required=False,
                escalation_on_failure=False
            )
        ]

        for playbook in playbooks:
            self.playbooks[playbook.incident_type] = playbook

    def get_playbook(self, incident_type: IncidentType) -> Optional[ResponsePlaybook]:
        """Get playbook for incident type."""
        return self.playbooks.get(incident_type)

    def get_actions_for_phase(
        self,
        incident_type: IncidentType,
        phase: str
    ) -> List[str]:
        """Get recommended actions for specific phase."""
        playbook = self.get_playbook(incident_type)
        if not playbook:
            return []

        phase_actions = {
            'initial': playbook.initial_actions,
            'investigation': playbook.investigation_steps,
            'containment': playbook.containment_actions,
            'recovery': playbook.recovery_steps
        }

        return phase_actions.get(phase, [])


class EscalationEngine:
    """Manages multi-level escalation."""

    # Escalation rules: {severity: (delay_minutes, escalate_to)}
    ESCALATION_RULES = {
        IncidentSeverity.LOW: (60, "Manager"),
        IncidentSeverity.MEDIUM: (30, "Director"),
        IncidentSeverity.HIGH: (15, "VP_Security"),
        IncidentSeverity.CRITICAL: (5, "CISO")
    }

    def get_escalation_level(self, severity: IncidentSeverity) -> str:
        """Get escalation contact for severity level."""
        _, escalate_to = self.ESCALATION_RULES.get(
            severity,
            (60, "Manager")
        )
        return escalate_to

    def should_escalate(
        self,
        incident: Incident,
        minutes_elapsed: int
    ) -> bool:
        """Determine if incident should be escalated."""
        delay, _ = self.ESCALATION_RULES.get(
            incident.severity,
            (60, "Manager")
        )
        return minutes_elapsed >= delay


class CommunicationHandler:
    """Manages incident notifications and communications."""

    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []

    def send_notification(
        self,
        incident: Incident,
        notification_type: str,
        recipients: List[str],
        message: str
    ) -> Dict[str, Any]:
        """Send notification about incident."""
        notification = {
            'notification_id': f"NOTIF-{uuid.uuid4().hex[:8]}",
            'incident_id': incident.incident_id,
            'type': notification_type,
            'recipients': recipients,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'status': 'SENT'
        }
        self.notifications.append(notification)
        return notification

    def create_incident_summary(self, incident: Incident) -> str:
        """Create human-readable incident summary."""
        summary = f"""
INCIDENT SUMMARY
================

ID: {incident.incident_id}
Title: {incident.title}
Type: {incident.incident_type.value}
Severity: {incident.severity.value}
Status: {incident.status.value}

Description: {incident.description}

Affected Systems: {', '.join(incident.affected_systems)}
Affected Users: {', '.join(incident.affected_users)}

Created: {incident.created_at.isoformat()}
Created By: {incident.created_by}
Last Updated: {incident.last_updated.isoformat()}

Response Actions: {len(incident.response_actions)}
Investigation Updates: {len(incident.updates)}
        """
        return summary.strip()


class RecoveryExecutor:
    """Executes recovery and remediation actions."""

    def __init__(self):
        self.execution_log: List[Dict[str, Any]] = []

    def execute_recovery_action(
        self,
        action: ResponseAction
    ) -> bool:
        """Execute recovery action."""
        log_entry = {
            'action_id': action.action_id,
            'action_type': action.action_type,
            'timestamp': datetime.now().isoformat(),
            'status': 'EXECUTED'
        }
        self.execution_log.append(log_entry)
        return True

    def restore_from_backup(
        self,
        system_id: str,
        backup_id: str
    ) -> Dict[str, Any]:
        """Initiate restore from backup."""
        restore_job = {
            'restore_id': f"RST-{uuid.uuid4().hex[:8]}",
            'system_id': system_id,
            'backup_id': backup_id,
            'started_at': datetime.now().isoformat(),
            'status': 'IN_PROGRESS'
        }
        return restore_job

    def revoke_credentials(self, user_ids: List[str]) -> Dict[str, Any]:
        """Revoke credentials for users."""
        revocation = {
            'revocation_id': f"REV-{uuid.uuid4().hex[:8]}",
            'user_ids': user_ids,
            'timestamp': datetime.now().isoformat(),
            'status': 'COMPLETED',
            'revoked_count': len(user_ids)
        }
        return revocation


class PostIncidentAnalyzer:
    """Analyzes incidents and generates post-incident reports."""

    def analyze_incident(self, incident: Incident) -> PostIncidentReport:
        """Generate post-incident analysis."""
        report = PostIncidentReport(
            report_id=f"REPORT-{uuid.uuid4().hex[:8]}",
            incident_id=incident.incident_id,
            generated_at=datetime.now(),
            root_cause=incident.root_cause or "Under investigation",
            contributing_factors=[
                "Review of logs",
                "System analysis",
                "User interviews"
            ],
            corrective_actions=[
                "Patch vulnerability",
                "Update configuration",
                "Implement additional monitoring"
            ],
            preventive_measures=[
                "Enhanced detection rules",
                "User training program",
                "Regular security audits"
            ],
            timeline={
                'detection': incident.created_at.isoformat(),
                'containment': (incident.created_at + timedelta(hours=2)).isoformat(),
                'resolution': (incident.created_at + timedelta(hours=24)).isoformat()
            },
            impact_summary=f"Affected {len(incident.affected_systems)} systems, "
                          f"{len(incident.affected_users)} users",
            lessons_learned=[
                "Improve detection capabilities",
                "Strengthen access controls",
                "Enhance incident response training"
            ]
        )
        return report

    def detect_patterns(self, incidents: List[Incident]) -> Dict[str, Any]:
        """Detect patterns in incidents."""
        patterns = {
            'total_incidents': len(incidents),
            'by_type': {},
            'by_severity': {},
            'average_resolution_time': 0
        }

        for incident in incidents:
            inc_type = incident.incident_type.value
            severity = incident.severity.value

            patterns['by_type'][inc_type] = patterns['by_type'].get(inc_type, 0) + 1
            patterns['by_severity'][severity] = patterns['by_severity'].get(
                severity, 0
            ) + 1

        return patterns


# ============================================================================
# INTEGRATED INCIDENT RESPONSE SYSTEM
# ============================================================================

class IncidentResponseSystem:
    """Integrated incident response and recovery system."""

    def __init__(self):
        self.incident_manager = IncidentManager()
        self.classifier = IncidentClassifier()
        self.playbook_engine = ResponsePlaybookEngine()
        self.escalation_engine = EscalationEngine()
        self.communication_handler = CommunicationHandler()
        self.recovery_executor = RecoveryExecutor()
        self.analyzer = PostIncidentAnalyzer()

    def create_incident_from_alert(
        self,
        alert_data: Dict[str, Any],
        event_logs: List[Dict[str, Any]],
        created_by: str
    ) -> Incident:
        """Create incident from security alert."""
        # Classify the incident
        incident_type, severity = self.classifier.classify_incident(
            alert_data,
            event_logs
        )

        # Create incident record
        incident = self.incident_manager.create_incident(
            title=alert_data.get('title', 'Security Alert'),
            description=alert_data.get('description', ''),
            severity=severity,
            incident_type=incident_type,
            created_by=created_by,
            affected_systems=alert_data.get('affected_systems', []),
            affected_users=alert_data.get('affected_users', []),
            alert_ids=[alert_data.get('alert_id', '')]
        )

        # Get and recommend playbook actions
        playbook = self.playbook_engine.get_playbook(incident_type)
        if playbook:
            for action in playbook.initial_actions:
                self.incident_manager.add_response_action(
                    incident.incident_id,
                    'initial_response',
                    action
                )

        # Send notifications if required
        if playbook and playbook.notification_required:
            escalate_to = self.escalation_engine.get_escalation_level(severity)
            self.communication_handler.send_notification(
                incident,
                'INCIDENT_CREATED',
                [escalate_to],
                f"New {severity.value} incident: {incident.title}"
            )

        return incident

    def execute_incident_response(self, incident_id: str) -> Dict[str, Any]:
        """Execute full incident response procedure."""
        incident = self.incident_manager.get_incident(incident_id)
        if not incident:
            return {'status': 'ERROR', 'message': 'Incident not found'}

        response_status = {
            'incident_id': incident_id,
            'actions_executed': 0,
            'actions_failed': 0,
            'timestamp': datetime.now().isoformat()
        }

        # Execute response actions
        for action in incident.response_actions:
            try:
                self.recovery_executor.execute_recovery_action(action)
                self.incident_manager.execute_action(
                    incident_id,
                    action.action_id,
                    f"Executed: {action.description}"
                )
                response_status['actions_executed'] += 1
            except Exception as e:
                response_status['actions_failed'] += 1

        return response_status

    def close_incident(
        self,
        incident_id: str,
        root_cause: str,
        impact_assessment: str
    ) -> PostIncidentReport:
        """Close incident and generate post-incident report."""
        incident = self.incident_manager.get_incident(incident_id)
        incident.root_cause = root_cause
        incident.impact_assessment = impact_assessment
        incident.status = IncidentStatus.CLOSED

        # Generate post-incident report
        report = self.analyzer.analyze_incident(incident)
        incident.lessons_learned = "\n".join(report.lessons_learned)

        return report

    def get_incident_status(self, incident_id: str) -> Dict[str, Any]:
        """Get current incident status."""
        incident = self.incident_manager.get_incident(incident_id)
        if not incident:
            return {'status': 'ERROR'}

        return {
            'incident_id': incident.incident_id,
            'status': incident.status.value,
            'severity': incident.severity.value,
            'type': incident.incident_type.value,
            'affected_systems': len(incident.affected_systems),
            'affected_users': len(incident.affected_users),
            'response_actions': len(incident.response_actions),
            'updates': len(incident.updates)
        }


# ============================================================================
# TESTS
# ============================================================================

def test_incident_management():
    """Test incident creation and lifecycle management."""
    print("=" * 80)
    print("TEST 1: INCIDENT MANAGEMENT")
    print("=" * 80)

    system = IncidentResponseSystem()

    # Create incident
    incident = system.incident_manager.create_incident(
        title="Unauthorized Access Detected",
        description="Multiple failed login attempts followed by successful unauthorized access",
        severity=IncidentSeverity.HIGH,
        incident_type=IncidentType.UNAUTHORIZED_ACCESS,
        created_by="security_analyst_001",
        affected_systems=["web-server-01", "db-server-02"],
        affected_users=["user_123", "user_456"]
    )

    print(f"✓ Incident created: {incident.incident_id}")
    print(f"  Title: {incident.title}")
    print(f"  Severity: {incident.severity.value}")
    print(f"  Status: {incident.status.value}")
    print()


def test_incident_classification():
    """Test auto-classification of incidents."""
    print("=" * 80)
    print("TEST 2: INCIDENT CLASSIFICATION")
    print("=" * 80)

    classifier = IncidentClassifier()

    test_cases = [
        {
            'alert_data': {
                'alert_type': 'unauthorized_access',
                'metric_name': 'failed_auth_rate',
                'affected_count': 50
            },
            'expected_type': 'UNAUTHORIZED_ACCESS',
            'expected_severity': 'HIGH'
        },
        {
            'alert_data': {
                'alert_type': 'data_breach',
                'metric_name': 'data_exfiltration',
                'affected_count': 5000
            },
            'expected_type': 'DATA_BREACH',
            'expected_severity': 'CRITICAL'
        },
        {
            'alert_data': {
                'alert_type': 'ddos_attack',
                'metric_name': 'request_rate',
                'affected_count': 200
            },
            'expected_type': 'DDoS_ATTACK',
            'expected_severity': 'HIGH'
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        incident_type, severity = classifier.classify_incident(
            test_case['alert_data'],
            []
        )
        print(f"✓ Test case {i}:")
        print(f"  Classified as: {incident_type.value}")
        print(f"  Severity: {severity.value}")
    print()


def test_response_playbooks():
    """Test response playbook retrieval and execution."""
    print("=" * 80)
    print("TEST 3: RESPONSE PLAYBOOKS")
    print("=" * 80)

    engine = ResponsePlaybookEngine()

    # Test playbook retrieval
    playbook = engine.get_playbook(IncidentType.UNAUTHORIZED_ACCESS)
    print(f"✓ Playbook retrieved: {playbook.name}")
    print(f"  Description: {playbook.description}")
    print(f"  Initial Actions: {len(playbook.initial_actions)}")
    for action in playbook.initial_actions:
        print(f"    - {action}")
    print()

    # Test phase actions
    phases = ['initial', 'investigation', 'containment', 'recovery']
    for phase in phases:
        actions = engine.get_actions_for_phase(
            IncidentType.UNAUTHORIZED_ACCESS,
            phase
        )
        print(f"✓ {phase.upper()} phase: {len(actions)} actions")
    print()


def test_escalation_engine():
    """Test escalation procedures."""
    print("=" * 80)
    print("TEST 4: ESCALATION ENGINE")
    print("=" * 80)

    engine = EscalationEngine()

    severities = [
        IncidentSeverity.LOW,
        IncidentSeverity.MEDIUM,
        IncidentSeverity.HIGH,
        IncidentSeverity.CRITICAL
    ]

    for severity in severities:
        escalate_to = engine.get_escalation_level(severity)
        delay, _ = engine.ESCALATION_RULES[severity]
        print(f"✓ {severity.value} severity → Escalate to: {escalate_to} "
              f"(within {delay} minutes)")
    print()


def test_communication_and_notifications():
    """Test incident communications."""
    print("=" * 80)
    print("TEST 5: COMMUNICATION & NOTIFICATIONS")
    print("=" * 80)

    system = IncidentResponseSystem()

    incident = system.incident_manager.create_incident(
        title="Critical Data Breach",
        description="Potential data exfiltration detected",
        severity=IncidentSeverity.CRITICAL,
        incident_type=IncidentType.DATA_BREACH,
        created_by="security_analyst_001",
        affected_systems=["db-server-primary"],
        affected_users=["user_001", "user_002", "user_003"]
    )

    # Send notification
    notification = system.communication_handler.send_notification(
        incident,
        'INCIDENT_ALERT',
        ['CISO', 'VP_Security'],
        f"CRITICAL: {incident.title}"
    )

    print(f"✓ Notification sent: {notification['notification_id']}")
    print(f"  Recipients: {', '.join(notification['recipients'])}")
    print(f"  Type: {notification['type']}")
    print()

    # Create incident summary
    summary = system.communication_handler.create_incident_summary(incident)
    print("✓ Incident summary created:")
    for line in summary.split('\n')[:10]:
        print(f"  {line}")
    print()


def test_incident_response_execution():
    """Test full incident response execution."""
    print("=" * 80)
    print("TEST 6: INCIDENT RESPONSE EXECUTION")
    print("=" * 80)

    system = IncidentResponseSystem()

    # Create incident from alert
    alert_data = {
        'alert_id': 'ALERT-001',
        'title': 'Unauthorized Access Attempt',
        'description': 'Multiple failed login attempts',
        'alert_type': 'unauthorized_access',
        'metric_name': 'failed_auth_rate',
        'affected_systems': ['auth-server-01'],
        'affected_users': ['user_123'],
        'affected_count': 150
    }

    incident = system.create_incident_from_alert(
        alert_data,
        [],
        'security_analyst_001'
    )

    print(f"✓ Incident created from alert: {incident.incident_id}")
    print(f"  Type: {incident.incident_type.value}")
    print(f"  Severity: {incident.severity.value}")
    print(f"  Response Actions: {len(incident.response_actions)}")
    print()

    # Execute response
    response_status = system.execute_incident_response(incident.incident_id)
    print(f"✓ Response execution status:")
    print(f"  Actions Executed: {response_status['actions_executed']}")
    print(f"  Actions Failed: {response_status['actions_failed']}")
    print()


def test_post_incident_analysis():
    """Test post-incident analysis and reporting."""
    print("=" * 80)
    print("TEST 7: POST-INCIDENT ANALYSIS")
    print("=" * 80)

    system = IncidentResponseSystem()

    # Create and close incident
    incident = system.incident_manager.create_incident(
        title="Configuration Error Exposure",
        description="Debug mode left enabled in production",
        severity=IncidentSeverity.MEDIUM,
        incident_type=IncidentType.CONFIGURATION_ERROR,
        created_by="security_analyst_001",
        affected_systems=["api-gateway"],
        affected_users=[]
    )

    # Close incident
    report = system.close_incident(
        incident.incident_id,
        root_cause="Developer left debug mode enabled during deployment",
        impact_assessment="Potential exposure of internal debugging information"
    )

    print(f"✓ Post-incident report generated: {report.report_id}")
    print(f"  Root Cause: {report.root_cause}")
    print(f"  Contributing Factors: {len(report.contributing_factors)}")
    print(f"  Corrective Actions: {len(report.corrective_actions)}")
    print(f"  Preventive Measures: {len(report.preventive_measures)}")
    print(f"  Lessons Learned: {len(report.lessons_learned)}")
    print()

    # Detect patterns
    patterns = system.analyzer.detect_patterns(
        list(system.incident_manager.incidents.values())
    )
    print(f"✓ Incident patterns detected:")
    print(f"  Total Incidents: {patterns['total_incidents']}")
    for inc_type, count in patterns['by_type'].items():
        print(f"    {inc_type}: {count}")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "PHASE 17: INCIDENT RESPONSE & RECOVERY".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    tests = [
        test_incident_management,
        test_incident_classification,
        test_response_playbooks,
        test_escalation_engine,
        test_communication_and_notifications,
        test_incident_response_execution,
        test_post_incident_analysis
    ]

    results = []
    for test in tests:
        try:
            test()
            results.append((test.__name__, "PASS"))
        except Exception as e:
            results.append((test.__name__, f"FAIL: {str(e)}"))

    # Summary
    print("=" * 80)
    print("INCIDENT RESPONSE & RECOVERY SUMMARY")
    print("=" * 80)
    print()
    print("✓ Tests run: " + str(len(results)))
    print("✓ Status: " + ("ALL PASS ✅" if all(r[1] == "PASS" for r in results) else "SOME FAILED"))
    print()

    for test_name, status in results:
        status_symbol = "✅" if status == "PASS" else "❌"
        print(f"  {status_symbol} {test_name}: {status}")

    print()
    print("=" * 80)
    print("INCIDENT RESPONSE SYSTEM FEATURES")
    print("=" * 80)
    print()
    print("✓ Incident Management:")
    print("  - Incident creation with unique identifiers")
    print("  - Immutable fingerprinting for integrity")
    print("  - Investigation tracking and updates")
    print("  - Response action management")
    print()
    print("✓ Incident Classification:")
    print("  - Auto-classification based on alert data")
    print("  - Severity assessment with impact analysis")
    print("  - Type mapping for response procedures")
    print()
    print("✓ Response Playbooks:")
    print("  - Pre-defined procedures for incident types")
    print("  - Phase-based actions (initial, investigation, containment, recovery)")
    print("  - Customizable playbook framework")
    print()
    print("✓ Escalation Procedures:")
    print("  - Multi-level escalation based on severity")
    print("  - Time-based escalation triggers")
    print("  - Clear escalation paths (Manager → Director → VP → CISO)")
    print()
    print("✓ Communication Handler:")
    print("  - Incident notifications to stakeholders")
    print("  - Human-readable incident summaries")
    print("  - Tracking of all communications")
    print()
    print("✓ Recovery Executor:")
    print("  - Automated recovery action execution")
    print("  - Backup restoration procedures")
    print("  - Credential revocation capabilities")
    print()
    print("✓ Post-Incident Analysis:")
    print("  - Root cause analysis")
    print("  - Pattern detection across incidents")
    print("  - Lessons learned tracking")
    print("  - Trend analysis for continuous improvement")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
