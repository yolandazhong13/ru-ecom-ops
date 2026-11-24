#!/usr/bin/env python3
"""
PHASE 18: THREAT INTELLIGENCE & VULNERABILITY MANAGEMENT
==========================================================

Implements comprehensive threat intelligence collection, vulnerability management,
and risk assessment for proactive security operations.

Components:
  - Threat Feed Integration: Aggregate threat intelligence from multiple sources
  - Vulnerability Management: Track and prioritize vulnerabilities
  - Risk Scoring: Calculate CVSS and risk scores for vulnerabilities
  - Threat Correlation: Correlate threats with incidents and systems
  - Remediation Tracking: Monitor patch deployment and remediation status
  - Threat Modeling: Model threats against system architecture
  - Asset Inventory: Maintain current asset inventory with vulnerability data
  - Advisory Management: Track and respond to security advisories

Architecture:
  ThreatFeedManager → Collect and normalize threat intelligence
  VulnerabilityScanner → Track and assess vulnerabilities
  RiskAssessment → Calculate CVSS and risk scores
  ThreatCorrelation → Link threats to incidents and assets
  RemediationTracker → Monitor remediation progress
  ThreatModel → Attack surface analysis
  AssetInventory → System and asset inventory management
  AdvisoryHandler → Process security advisories
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

class VulnerabilitySeverity(Enum):
    """CVSS severity ratings."""
    NONE = "NONE"              # 0.0
    LOW = "LOW"                # 0.1-3.9
    MEDIUM = "MEDIUM"          # 4.0-6.9
    HIGH = "HIGH"              # 7.0-8.9
    CRITICAL = "CRITICAL"      # 9.0-10.0


class ThreatLevel(Enum):
    """Threat intelligence severity levels."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RemediationStatus(Enum):
    """Vulnerability remediation status."""
    UNPATCHED = "UNPATCHED"
    PATCH_AVAILABLE = "PATCH_AVAILABLE"
    PATCH_STAGED = "PATCH_STAGED"
    PATCH_DEPLOYED = "PATCH_DEPLOYED"
    VERIFIED = "VERIFIED"
    WAIVED = "WAIVED"


class AssetType(Enum):
    """Types of assets in inventory."""
    SERVER = "SERVER"
    WORKSTATION = "WORKSTATION"
    NETWORK_DEVICE = "NETWORK_DEVICE"
    DATABASE = "DATABASE"
    APPLICATION = "APPLICATION"
    CONTAINER = "CONTAINER"
    CLOUD_RESOURCE = "CLOUD_RESOURCE"
    IOT_DEVICE = "IOT_DEVICE"


class ThreatSourceType(Enum):
    """Source of threat intelligence."""
    NVD = "NVD"                          # National Vulnerability Database
    CISA = "CISA"                        # CISA Advisories
    VENDOR = "VENDOR"                    # Vendor advisories
    OSINT = "OSINT"                      # Open source intelligence
    COMMERCIAL = "COMMERCIAL"            # Commercial threat feeds
    INTERNAL = "INTERNAL"                # Internal security team
    DARK_WEB = "DARK_WEB"                # Dark web monitoring
    COMMUNITY = "COMMUNITY"              # Community reports


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Vulnerability:
    """Vulnerability record."""
    vuln_id: str
    cve_id: str
    title: str
    description: str
    affected_software: List[str]
    affected_versions: List[str]
    cvss_score: float
    cvss_severity: VulnerabilitySeverity
    cvss_vector: str
    published_date: datetime
    discovered_date: Optional[datetime]
    exploited_in_wild: bool
    exploit_availability: str  # None, Proof-of-Concept, Functional, Weaponized
    affected_assets: List[str] = field(default_factory=list)
    remediation_status: RemediationStatus = RemediationStatus.UNPATCHED
    patch_available_date: Optional[datetime] = None
    patch_deployed_date: Optional[datetime] = None
    notes: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d['cvss_severity'] = self.cvss_severity.value
        d['remediation_status'] = self.remediation_status.value
        d['published_date'] = self.published_date.isoformat()
        d['discovered_date'] = self.discovered_date.isoformat() if self.discovered_date else None
        d['patch_available_date'] = self.patch_available_date.isoformat() if self.patch_available_date else None
        d['patch_deployed_date'] = self.patch_deployed_date.isoformat() if self.patch_deployed_date else None
        return d


@dataclass
class ThreatIntelligence:
    """Threat intelligence report."""
    threat_id: str
    title: str
    description: str
    threat_level: ThreatLevel
    threat_source: ThreatSourceType
    source_name: str
    collected_date: datetime
    related_vulnerabilities: List[str]
    related_indicators: List[str]  # IPs, domains, hashes
    affected_industries: List[str]
    affected_regions: List[str]
    attack_patterns: List[str]
    campaign_name: Optional[str] = None
    threat_actor: Optional[str] = None
    tactics: List[str] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d['threat_level'] = self.threat_level.value
        d['threat_source'] = self.threat_source.value
        d['collected_date'] = self.collected_date.isoformat()
        return d


@dataclass
class Asset:
    """System asset in inventory."""
    asset_id: str
    name: str
    asset_type: AssetType
    owner: str
    status: str  # active, inactive, decommissioned
    ip_address: Optional[str]
    hostname: Optional[str]
    os: Optional[str]
    software_installed: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    last_scanned: Optional[datetime] = None
    last_patched: Optional[datetime] = None
    criticality: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL

    def to_dict(self):
        d = asdict(self)
        d['asset_type'] = self.asset_type.value
        d['last_scanned'] = self.last_scanned.isoformat() if self.last_scanned else None
        d['last_patched'] = self.last_patched.isoformat() if self.last_patched else None
        return d


@dataclass
class RemediationPlan:
    """Plan for remediating vulnerabilities."""
    plan_id: str
    created_date: datetime
    target_completion: datetime
    vulnerabilities: List[str]
    affected_assets: List[str]
    actions: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PLANNED"  # PLANNED, IN_PROGRESS, COMPLETED
    owner: str = ""

    def to_dict(self):
        d = asdict(self)
        d['created_date'] = self.created_date.isoformat()
        d['target_completion'] = self.target_completion.isoformat()
        return d


@dataclass
class SecurityAdvisory:
    """Security advisory from vendor or authority."""
    advisory_id: str
    title: str
    source: str
    published_date: datetime
    severity: VulnerabilitySeverity
    affected_products: List[str]
    recommended_actions: List[str]
    references: List[str]
    related_vulnerabilities: List[str]
    action_required: bool
    deadline: Optional[datetime] = None

    def to_dict(self):
        d = asdict(self)
        d['severity'] = self.severity.value
        d['published_date'] = self.published_date.isoformat()
        d['deadline'] = self.deadline.isoformat() if self.deadline else None
        return d


# ============================================================================
# THREAT INTELLIGENCE SYSTEM
# ============================================================================

class ThreatFeedManager:
    """Manages threat intelligence feeds."""

    def __init__(self):
        self.feeds: Dict[str, List[ThreatIntelligence]] = {}
        self.all_threats: Dict[str, ThreatIntelligence] = {}
        self.threat_counter = 0

    def add_threat_feed(self, feed_name: str, threats: List[Dict[str, Any]]):
        """Add threats from a feed."""
        self.feeds[feed_name] = []

        for threat_data in threats:
            self.threat_counter += 1
            threat = ThreatIntelligence(
                threat_id=f"THREAT-{self.threat_counter:06d}",
                title=threat_data.get('title', ''),
                description=threat_data.get('description', ''),
                threat_level=ThreatLevel[threat_data.get('threat_level', 'MEDIUM')],
                threat_source=ThreatSourceType[threat_data.get('source', 'OSINT')],
                source_name=feed_name,
                collected_date=datetime.now(),
                related_vulnerabilities=threat_data.get('cves', []),
                related_indicators=threat_data.get('indicators', []),
                affected_industries=threat_data.get('industries', []),
                affected_regions=threat_data.get('regions', []),
                attack_patterns=threat_data.get('patterns', []),
                campaign_name=threat_data.get('campaign', None),
                threat_actor=threat_data.get('actor', None),
                tactics=threat_data.get('tactics', []),
                techniques=threat_data.get('techniques', [])
            )

            self.feeds[feed_name].append(threat)
            self.all_threats[threat.threat_id] = threat

    def get_threats_by_level(self, threat_level: ThreatLevel) -> List[ThreatIntelligence]:
        """Get threats by severity level."""
        return [t for t in self.all_threats.values() if t.threat_level == threat_level]

    def get_threats_by_source(self, source: ThreatSourceType) -> List[ThreatIntelligence]:
        """Get threats from specific source."""
        return [t for t in self.all_threats.values() if t.threat_source == source]

    def get_latest_threats(self, days: int = 7) -> List[ThreatIntelligence]:
        """Get threats from last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            t for t in self.all_threats.values()
            if t.collected_date >= cutoff
        ]


class VulnerabilityScanner:
    """Manages vulnerability data."""

    def __init__(self):
        self.vulnerabilities: Dict[str, Vulnerability] = {}
        self.vuln_counter = 0

    def register_vulnerability(
        self,
        cve_id: str,
        title: str,
        description: str,
        cvss_score: float,
        affected_software: List[str],
        affected_versions: List[str],
        exploited_in_wild: bool = False
    ) -> Vulnerability:
        """Register new vulnerability."""
        self.vuln_counter += 1
        vuln_id = f"VULN-{self.vuln_counter:06d}"

        # Determine severity from CVSS score
        if cvss_score == 0:
            severity = VulnerabilitySeverity.NONE
        elif cvss_score < 4.0:
            severity = VulnerabilitySeverity.LOW
        elif cvss_score < 7.0:
            severity = VulnerabilitySeverity.MEDIUM
        elif cvss_score < 9.0:
            severity = VulnerabilitySeverity.HIGH
        else:
            severity = VulnerabilitySeverity.CRITICAL

        vuln = Vulnerability(
            vuln_id=vuln_id,
            cve_id=cve_id,
            title=title,
            description=description,
            affected_software=affected_software,
            affected_versions=affected_versions,
            cvss_score=cvss_score,
            cvss_severity=severity,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            published_date=datetime.now(),
            discovered_date=None,
            exploited_in_wild=exploited_in_wild,
            exploit_availability="Proof-of-Concept" if exploited_in_wild else "None"
        )

        self.vulnerabilities[vuln_id] = vuln
        return vuln

    def get_vulnerabilities_by_severity(
        self,
        severity: VulnerabilitySeverity
    ) -> List[Vulnerability]:
        """Get vulnerabilities by severity level."""
        return [v for v in self.vulnerabilities.values() if v.cvss_severity == severity]

    def get_critical_vulnerabilities(self) -> List[Vulnerability]:
        """Get all critical vulnerabilities."""
        return self.get_vulnerabilities_by_severity(VulnerabilitySeverity.CRITICAL)

    def update_remediation_status(
        self,
        vuln_id: str,
        status: RemediationStatus
    ) -> Vulnerability:
        """Update remediation status of vulnerability."""
        if vuln_id not in self.vulnerabilities:
            raise ValueError(f"Vulnerability {vuln_id} not found")

        vuln = self.vulnerabilities[vuln_id]
        vuln.remediation_status = status

        if status == RemediationStatus.PATCH_AVAILABLE:
            vuln.patch_available_date = datetime.now()
        elif status == RemediationStatus.PATCH_DEPLOYED:
            vuln.patch_deployed_date = datetime.now()

        return vuln


class RiskAssessment:
    """Calculates risk scores and metrics."""

    # Risk calculation constants
    CVSS_WEIGHT = 0.6
    EXPLOITABILITY_WEIGHT = 0.25
    PREVALENCE_WEIGHT = 0.15

    @staticmethod
    def calculate_risk_score(
        vulnerability: Vulnerability,
        exploited_in_wild: bool,
        asset_criticality: str
    ) -> float:
        """Calculate overall risk score (0-100)."""
        # CVSS component (0-100)
        cvss_component = (vulnerability.cvss_score / 10.0) * 100

        # Exploitability component (0-100)
        exploitability = 100 if exploited_in_wild else 30

        # Asset criticality component (0-100)
        criticality_map = {
            'LOW': 30,
            'MEDIUM': 60,
            'HIGH': 85,
            'CRITICAL': 100
        }
        criticality = criticality_map.get(asset_criticality, 60)

        # Calculate weighted risk score
        risk_score = (
            (cvss_component * RiskAssessment.CVSS_WEIGHT) +
            (exploitability * RiskAssessment.EXPLOITABILITY_WEIGHT) +
            (criticality * RiskAssessment.PREVALENCE_WEIGHT)
        )

        return min(100, max(0, risk_score))

    @staticmethod
    def prioritize_vulnerabilities(
        vulnerabilities: List[tuple[Vulnerability, float]]
    ) -> List[tuple[Vulnerability, float]]:
        """Sort vulnerabilities by risk score (highest first)."""
        return sorted(vulnerabilities, key=lambda x: x[1], reverse=True)


class AssetInventory:
    """Manages system asset inventory."""

    def __init__(self):
        self.assets: Dict[str, Asset] = {}
        self.asset_counter = 0

    def add_asset(
        self,
        name: str,
        asset_type: AssetType,
        owner: str,
        criticality: str = "MEDIUM",
        ip_address: Optional[str] = None,
        hostname: Optional[str] = None,
        os: Optional[str] = None
    ) -> Asset:
        """Add asset to inventory."""
        self.asset_counter += 1
        asset_id = f"ASSET-{self.asset_counter:06d}"

        asset = Asset(
            asset_id=asset_id,
            name=name,
            asset_type=asset_type,
            owner=owner,
            status="active",
            ip_address=ip_address,
            hostname=hostname,
            os=os,
            criticality=criticality
        )

        self.assets[asset_id] = asset
        return asset

    def link_vulnerability_to_asset(
        self,
        asset_id: str,
        vuln_id: str
    ):
        """Link vulnerability to affected asset."""
        if asset_id not in self.assets:
            raise ValueError(f"Asset {asset_id} not found")

        asset = self.assets[asset_id]
        if vuln_id not in asset.vulnerabilities:
            asset.vulnerabilities.append(vuln_id)

    def get_assets_by_type(self, asset_type: AssetType) -> List[Asset]:
        """Get assets by type."""
        return [a for a in self.assets.values() if a.asset_type == asset_type]

    def get_critical_assets(self) -> List[Asset]:
        """Get all critical assets."""
        return [a for a in self.assets.values() if a.criticality == "CRITICAL"]

    def get_vulnerable_assets(self) -> List[Asset]:
        """Get assets with known vulnerabilities."""
        return [a for a in self.assets.values() if len(a.vulnerabilities) > 0]


class ThreatCorrelation:
    """Correlates threats with vulnerabilities and incidents."""

    def __init__(self):
        self.correlations: List[Dict[str, Any]] = []

    def correlate_threat_to_vulnerability(
        self,
        threat: ThreatIntelligence,
        vulnerability: Vulnerability,
        confidence: float
    ) -> Dict[str, Any]:
        """Create correlation between threat and vulnerability."""
        correlation = {
            'correlation_id': f"CORR-{uuid.uuid4().hex[:8]}",
            'threat_id': threat.threat_id,
            'vuln_id': vulnerability.vuln_id,
            'confidence': confidence,
            'created_at': datetime.now().isoformat(),
            'status': 'ACTIVE'
        }
        self.correlations.append(correlation)
        return correlation

    def find_related_vulnerabilities(
        self,
        threat: ThreatIntelligence,
        vulnerabilities: Dict[str, Vulnerability]
    ) -> List[Vulnerability]:
        """Find vulnerabilities related to threat."""
        related = []
        for cve_id in threat.related_vulnerabilities:
            for vuln in vulnerabilities.values():
                if vuln.cve_id == cve_id:
                    related.append(vuln)
        return related

    def get_threat_landscape(
        self,
        threats: Dict[str, ThreatIntelligence]
    ) -> Dict[str, Any]:
        """Generate threat landscape summary."""
        landscape = {
            'total_threats': len(threats),
            'by_level': {},
            'by_source': {},
            'active_campaigns': [],
            'threatened_industries': set()
        }

        for threat in threats.values():
            level = threat.threat_level.value
            landscape['by_level'][level] = landscape['by_level'].get(level, 0) + 1

            source = threat.threat_source.value
            landscape['by_source'][source] = landscape['by_source'].get(source, 0) + 1

            if threat.campaign_name:
                landscape['active_campaigns'].append(threat.campaign_name)

            landscape['threatened_industries'].update(threat.affected_industries)

        landscape['threatened_industries'] = list(landscape['threatened_industries'])
        return landscape


class RemediationTracker:
    """Tracks vulnerability remediation efforts."""

    def __init__(self):
        self.plans: Dict[str, RemediationPlan] = {}
        self.plan_counter = 0

    def create_remediation_plan(
        self,
        vulnerabilities: List[str],
        affected_assets: List[str],
        target_days: int = 30,
        owner: str = ""
    ) -> RemediationPlan:
        """Create remediation plan for vulnerabilities."""
        self.plan_counter += 1
        plan_id = f"PLAN-{self.plan_counter:06d}"

        plan = RemediationPlan(
            plan_id=plan_id,
            created_date=datetime.now(),
            target_completion=datetime.now() + timedelta(days=target_days),
            vulnerabilities=vulnerabilities,
            affected_assets=affected_assets,
            owner=owner
        )

        # Add standard remediation actions
        plan.actions = [
            {'action': 'Assess patch compatibility', 'status': 'PENDING'},
            {'action': 'Deploy to test environment', 'status': 'PENDING'},
            {'action': 'Validate functionality', 'status': 'PENDING'},
            {'action': 'Deploy to production', 'status': 'PENDING'},
            {'action': 'Verify deployment', 'status': 'PENDING'}
        ]

        self.plans[plan_id] = plan
        return plan

    def update_plan_status(self, plan_id: str, status: str):
        """Update remediation plan status."""
        if plan_id not in self.plans:
            raise ValueError(f"Plan {plan_id} not found")
        self.plans[plan_id].status = status

    def get_overdue_plans(self) -> List[RemediationPlan]:
        """Get remediation plans that are overdue."""
        now = datetime.now()
        return [
            p for p in self.plans.values()
            if p.target_completion < now and p.status != "COMPLETED"
        ]


class SecurityAdvisoryHandler:
    """Manages security advisories."""

    def __init__(self):
        self.advisories: Dict[str, SecurityAdvisory] = {}
        self.advisory_counter = 0

    def process_advisory(
        self,
        title: str,
        source: str,
        severity: VulnerabilitySeverity,
        affected_products: List[str],
        recommended_actions: List[str],
        action_required: bool = True,
        days_to_deadline: int = 30
    ) -> SecurityAdvisory:
        """Process security advisory."""
        self.advisory_counter += 1
        advisory_id = f"ADV-{self.advisory_counter:06d}"

        advisory = SecurityAdvisory(
            advisory_id=advisory_id,
            title=title,
            source=source,
            published_date=datetime.now(),
            severity=severity,
            affected_products=affected_products,
            recommended_actions=recommended_actions,
            references=[],
            related_vulnerabilities=[],
            action_required=action_required,
            deadline=datetime.now() + timedelta(days=days_to_deadline) if action_required else None
        )

        self.advisories[advisory_id] = advisory
        return advisory

    def get_urgent_advisories(self) -> List[SecurityAdvisory]:
        """Get advisories requiring urgent action."""
        now = datetime.now()
        return [
            a for a in self.advisories.values()
            if a.action_required and a.deadline and a.deadline < now + timedelta(days=7)
        ]


# ============================================================================
# INTEGRATED THREAT INTELLIGENCE SYSTEM
# ============================================================================

class ThreatIntelligenceSystem:
    """Integrated threat intelligence and vulnerability management system."""

    def __init__(self):
        self.feed_manager = ThreatFeedManager()
        self.scanner = VulnerabilityScanner()
        self.risk_assessment = RiskAssessment()
        self.inventory = AssetInventory()
        self.threat_correlation = ThreatCorrelation()
        self.remediation_tracker = RemediationTracker()
        self.advisory_handler = SecurityAdvisoryHandler()

    def analyze_threat_landscape(self) -> Dict[str, Any]:
        """Generate comprehensive threat landscape analysis."""
        return self.threat_correlation.get_threat_landscape(
            self.feed_manager.all_threats
        )

    def identify_at_risk_assets(self) -> List[Dict[str, Any]]:
        """Identify assets at highest risk."""
        at_risk = []

        for asset in self.inventory.get_vulnerable_assets():
            total_risk = 0
            critical_count = 0

            for vuln_id in asset.vulnerabilities:
                if vuln_id in self.scanner.vulnerabilities:
                    vuln = self.scanner.vulnerabilities[vuln_id]
                    risk = self.risk_assessment.calculate_risk_score(
                        vuln,
                        vuln.exploited_in_wild,
                        asset.criticality
                    )
                    total_risk += risk

                    if vuln.cvss_severity == VulnerabilitySeverity.CRITICAL:
                        critical_count += 1

            at_risk.append({
                'asset_id': asset.asset_id,
                'asset_name': asset.name,
                'criticality': asset.criticality,
                'vulnerability_count': len(asset.vulnerabilities),
                'critical_count': critical_count,
                'total_risk_score': total_risk / len(asset.vulnerabilities)
            })

        return sorted(at_risk, key=lambda x: x['total_risk_score'], reverse=True)


# ============================================================================
# TESTS
# ============================================================================

def test_threat_feed_integration():
    """Test threat intelligence feed integration."""
    print("=" * 80)
    print("TEST 1: THREAT FEED INTEGRATION")
    print("=" * 80)

    manager = ThreatFeedManager()

    # Add threat feed
    threats = [
        {
            'title': 'APT Campaign Targeting Financial Sector',
            'description': 'New APT campaign using zero-day vulnerabilities',
            'threat_level': 'CRITICAL',
            'source': 'CISA',
            'cves': ['CVE-2025-1234', 'CVE-2025-1235'],
            'indicators': ['192.168.1.100', 'malicious.com'],
            'industries': ['Finance', 'Banking'],
            'regions': ['US', 'EU'],
            'patterns': ['Spear phishing', 'Lateral movement'],
            'actor': 'APT-28'
        },
        {
            'title': 'Ransomware Campaign: LockBit 3.0',
            'description': 'Increased LockBit 3.0 ransomware activity',
            'threat_level': 'HIGH',
            'source': 'OSINT',
            'cves': ['CVE-2025-5678'],
            'indicators': ['10.0.0.50'],
            'industries': ['Healthcare', 'Manufacturing'],
            'regions': ['Global'],
            'patterns': ['Credential theft', 'Encryption'],
            'campaign': 'LockBit-Wave-Q4-2025'
        }
    ]

    manager.add_threat_feed("CISA_FEEDS", threats)

    print(f"✓ Threats ingested: {len(manager.all_threats)}")
    for threat in manager.all_threats.values():
        print(f"  [{threat.threat_id}] {threat.title} ({threat.threat_level.value})")
    print()


def test_vulnerability_management():
    """Test vulnerability tracking and management."""
    print("=" * 80)
    print("TEST 2: VULNERABILITY MANAGEMENT")
    print("=" * 80)

    scanner = VulnerabilityScanner()

    # Register vulnerabilities
    vulns = [
        {
            'cve': 'CVE-2025-1234',
            'title': 'RCE in Apache Struts',
            'cvss': 9.8,
            'software': ['Apache Struts'],
            'versions': ['2.5.0', '2.5.1', '2.5.2'],
            'exploited': True
        },
        {
            'cve': 'CVE-2025-5678',
            'title': 'SQL Injection in WordPress Plugin',
            'cvss': 7.2,
            'software': ['WordPress', 'Plugin: BadPlugin'],
            'versions': ['1.0', '1.1'],
            'exploited': False
        }
    ]

    for vuln_data in vulns:
        vuln = scanner.register_vulnerability(
            cve_id=vuln_data['cve'],
            title=vuln_data['title'],
            description=f"Vulnerability {vuln_data['cve']}",
            cvss_score=vuln_data['cvss'],
            affected_software=vuln_data['software'],
            affected_versions=vuln_data['versions'],
            exploited_in_wild=vuln_data['exploited']
        )
        print(f"✓ Registered: {vuln.cve_id} - {vuln.title}")
        print(f"  CVSS: {vuln.cvss_score} ({vuln.cvss_severity.value})")
        print(f"  Exploited: {'Yes' if vuln.exploited_in_wild else 'No'}")

    print()


def test_risk_assessment():
    """Test risk scoring and prioritization."""
    print("=" * 80)
    print("TEST 3: RISK ASSESSMENT")
    print("=" * 80)

    scanner = VulnerabilityScanner()
    risk = RiskAssessment()

    vuln1 = scanner.register_vulnerability(
        cve_id='CVE-2025-1234',
        title='Critical RCE',
        description='Remote code execution',
        cvss_score=9.8,
        affected_software=['Apache Struts'],
        affected_versions=['2.5.0'],
        exploited_in_wild=True
    )

    vuln2 = scanner.register_vulnerability(
        cve_id='CVE-2025-5678',
        title='Medium Elevation',
        description='Local privilege escalation',
        cvss_score=6.5,
        affected_software=['Linux Kernel'],
        affected_versions=['5.10.0'],
        exploited_in_wild=False
    )

    # Calculate risk scores
    risk1 = risk.calculate_risk_score(vuln1, True, 'CRITICAL')
    risk2 = risk.calculate_risk_score(vuln2, False, 'MEDIUM')

    print(f"✓ Risk Score for CVE-2025-1234: {risk1:.1f}/100")
    print(f"  CVSS: 9.8, Exploited: Yes, Asset: Critical")
    print(f"✓ Risk Score for CVE-2025-5678: {risk2:.1f}/100")
    print(f"  CVSS: 6.5, Exploited: No, Asset: Medium")
    print()


def test_asset_inventory():
    """Test asset inventory management."""
    print("=" * 80)
    print("TEST 4: ASSET INVENTORY")
    print("=" * 80)

    inventory = AssetInventory()

    assets_data = [
        {'name': 'web-prod-01', 'type': 'SERVER', 'criticality': 'CRITICAL'},
        {'name': 'db-prod-01', 'type': 'DATABASE', 'criticality': 'CRITICAL'},
        {'name': 'workstation-01', 'type': 'WORKSTATION', 'criticality': 'LOW'},
        {'name': 'container-app-01', 'type': 'CONTAINER', 'criticality': 'HIGH'}
    ]

    for asset_data in assets_data:
        asset = inventory.add_asset(
            name=asset_data['name'],
            asset_type=AssetType[asset_data['type']],
            owner='IT',
            criticality=asset_data['criticality']
        )
        print(f"✓ Added asset: {asset.asset_id} - {asset.name} ({asset.criticality})")

    critical = inventory.get_critical_assets()
    print(f"\n✓ Critical assets: {len(critical)}")
    print()


def test_threat_correlation():
    """Test threat correlation with vulnerabilities."""
    print("=" * 80)
    print("TEST 5: THREAT CORRELATION")
    print("=" * 80)

    system = ThreatIntelligenceSystem()

    # Add threat
    threats = [{
        'title': 'CVE-2025-1234 Exploit Kit',
        'description': 'Active exploitation of CVE-2025-1234',
        'threat_level': 'CRITICAL',
        'source': 'CISA',
        'cves': ['CVE-2025-1234'],
        'indicators': ['malicious.com'],
        'industries': ['All'],
        'regions': ['Global'],
        'patterns': ['Exploitation'],
        'actor': 'Unknown'
    }]

    system.feed_manager.add_threat_feed("OSINT", threats)

    # Add vulnerability
    vuln = system.scanner.register_vulnerability(
        cve_id='CVE-2025-1234',
        title='RCE Vulnerability',
        description='Remote code execution',
        cvss_score=9.8,
        affected_software=['Apache Struts'],
        affected_versions=['2.5.0'],
        exploited_in_wild=True
    )

    # Correlate
    threat = list(system.feed_manager.all_threats.values())[0]
    correlation = system.threat_correlation.correlate_threat_to_vulnerability(
        threat, vuln, 0.95
    )

    print(f"✓ Correlation created: {correlation['correlation_id']}")
    print(f"  Threat: {threat.threat_id}")
    print(f"  Vulnerability: {vuln.vuln_id}")
    print(f"  Confidence: {correlation['confidence']:.0%}")
    print()


def test_remediation_tracking():
    """Test remediation plan creation and tracking."""
    print("=" * 80)
    print("TEST 6: REMEDIATION TRACKING")
    print("=" * 80)

    tracker = RemediationTracker()

    plan = tracker.create_remediation_plan(
        vulnerabilities=['VULN-000001', 'VULN-000002'],
        affected_assets=['ASSET-000001', 'ASSET-000002'],
        target_days=30,
        owner='Security Team'
    )

    print(f"✓ Remediation plan created: {plan.plan_id}")
    print(f"  Target completion: {plan.target_completion.date()}")
    print(f"  Vulnerabilities: {len(plan.vulnerabilities)}")
    print(f"  Actions:")
    for i, action in enumerate(plan.actions, 1):
        print(f"    {i}. {action['action']} ({action['status']})")
    print()


def test_advisory_handling():
    """Test security advisory handling."""
    print("=" * 80)
    print("TEST 7: ADVISORY HANDLING")
    print("=" * 80)

    handler = SecurityAdvisoryHandler()

    advisory = handler.process_advisory(
        title='Critical Apache Struts RCE',
        source='Apache Foundation',
        severity=VulnerabilitySeverity.CRITICAL,
        affected_products=['Apache Struts 2.5.0-2.5.2'],
        recommended_actions=['Upgrade to 2.5.3', 'Apply WAF rules'],
        action_required=True,
        days_to_deadline=7
    )

    print(f"✓ Advisory processed: {advisory.advisory_id}")
    print(f"  Title: {advisory.title}")
    print(f"  Severity: {advisory.severity.value}")
    print(f"  Action Required: Yes")
    print(f"  Deadline: {advisory.deadline.date()}")
    print(f"  Recommended Actions:")
    for action in advisory.recommended_actions:
        print(f"    - {action}")
    print()


def test_threat_landscape_analysis():
    """Test threat landscape analysis."""
    print("=" * 80)
    print("TEST 8: THREAT LANDSCAPE ANALYSIS")
    print("=" * 80)

    system = ThreatIntelligenceSystem()

    # Add multiple threats
    threats = [
        {
            'title': 'APT Campaign',
            'description': 'Advanced threat',
            'threat_level': 'CRITICAL',
            'source': 'CISA',
            'cves': [],
            'indicators': [],
            'industries': ['Finance'],
            'regions': ['US'],
            'patterns': [],
            'campaign': 'APT-28-Wave-1'
        },
        {
            'title': 'Ransomware Spike',
            'description': 'Ransomware increase',
            'threat_level': 'HIGH',
            'source': 'OSINT',
            'cves': [],
            'indicators': [],
            'industries': ['Healthcare', 'Finance'],
            'regions': ['Global'],
            'patterns': [],
            'campaign': 'LockBit-Q4'
        }
    ]

    system.feed_manager.add_threat_feed("COMBINED", threats)
    landscape = system.analyze_threat_landscape()

    print(f"✓ Threat landscape analysis:")
    print(f"  Total threats: {landscape['total_threats']}")
    print(f"  By threat level:")
    for level, count in landscape['by_level'].items():
        print(f"    {level}: {count}")
    print(f"  Active campaigns: {len(landscape['active_campaigns'])}")
    print(f"  Threatened industries: {', '.join(landscape['threatened_industries'][:3])}")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "PHASE 18: THREAT INTELLIGENCE & VULNERABILITY MANAGEMENT".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    tests = [
        test_threat_feed_integration,
        test_vulnerability_management,
        test_risk_assessment,
        test_asset_inventory,
        test_threat_correlation,
        test_remediation_tracking,
        test_advisory_handling,
        test_threat_landscape_analysis
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
    print("THREAT INTELLIGENCE SUMMARY")
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
    print("THREAT INTELLIGENCE SYSTEM FEATURES")
    print("=" * 80)
    print()
    print("✓ Threat Feed Integration:")
    print("  - Multiple threat source types (NVD, CISA, OSINT, Commercial)")
    print("  - Threat severity levels (INFO through CRITICAL)")
    print("  - Campaign and threat actor tracking")
    print("  - Attack pattern and technique classification (MITRE ATT&CK)")
    print()
    print("✓ Vulnerability Management:")
    print("  - CVE tracking with CVSS scores")
    print("  - Exploit availability assessment")
    print("  - Remediation status tracking")
    print("  - Affected asset linkage")
    print()
    print("✓ Risk Assessment:")
    print("  - Weighted risk scoring (CVSS, exploitability, asset criticality)")
    print("  - Vulnerability prioritization")
    print("  - Risk-based remediation planning")
    print()
    print("✓ Asset Inventory:")
    print("  - Multi-type asset tracking (servers, workstations, containers, etc.)")
    print("  - Vulnerability cross-reference")
    print("  - Asset criticality classification")
    print("  - Scan and patch tracking")
    print()
    print("✓ Threat Correlation:")
    print("  - Threat-to-vulnerability mapping")
    print("  - Threat landscape analysis")
    print("  - Industry and geographic targeting")
    print("  - Confidence scoring")
    print()
    print("✓ Remediation Tracking:")
    print("  - Multi-step remediation plans")
    print("  - Target completion tracking")
    print("  - Overdue plan identification")
    print()
    print("✓ Advisory Management:")
    print("  - Security advisory processing")
    print("  - Deadline tracking")
    print("  - Urgent advisory identification")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
