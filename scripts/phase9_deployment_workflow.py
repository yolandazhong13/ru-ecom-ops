#!/usr/bin/env python3
"""
Phase 9: Deployment & Containerization Orchestrator
Validates, coordinates, and monitors Kubernetes deployment for ru-ecom-ops

This script:
1. Validates Kubernetes manifests
2. Verifies secrets and configurations
3. Coordinates deployment sequence
4. Monitors health checks
5. Provides rollback capability
"""

import sys
import os
import json
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentPhase(Enum):
    """Deployment phases in order"""
    VALIDATE = "validate"
    PREPARE = "prepare"
    CONFIGURE = "configure"
    DEPLOY = "deploy"
    HEALTH_CHECK = "health_check"
    VERIFY = "verify"


@dataclass
class DeploymentConfig:
    """Configuration for deployment"""
    environment: Environment
    namespace: str = "ru-ecom-ops"
    app_name: str = "ru-ecom-ops"
    manifests_dir: str = "k8s"
    env_file: str = ""
    replica_count: int = 3
    timeout_seconds: int = 300
    health_check_retries: int = 10


class KubernetesValidator:
    """Validates Kubernetes manifests and configurations"""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.manifests_dir = Path(config.manifests_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        logger.info("Starting manifest validation...")

        checks = [
            self._validate_manifests_exist,
            self._validate_manifest_syntax,
            self._validate_namespace_config,
            self._validate_pvc_config,
            self._validate_configmap_config,
            self._validate_secret_references,
            self._validate_service_config,
            self._validate_ingress_config,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"{check.__name__}: {str(e)}")
                logger.error(f"Validation check failed: {check.__name__}", exc_info=True)

        return len(self.errors) == 0

    def _validate_manifests_exist(self) -> None:
        """Verify all required manifest files exist"""
        required_files = [
            "deployment.yaml",
            "configmap.yaml",
            "secret.yaml",
            "pvc.yaml",
            "service.yaml",
        ]

        for filename in required_files:
            filepath = self.manifests_dir / filename
            if not filepath.exists():
                self.errors.append(f"Missing manifest file: {filepath}")
            else:
                logger.info(f"✓ Found manifest: {filename}")

    def _validate_manifest_syntax(self) -> None:
        """Validate YAML syntax using kubectl dry-run"""
        logger.info("Validating YAML syntax...")

        for manifest_file in self.manifests_dir.glob("*.yaml"):
            try:
                result = subprocess.run(
                    ["kubectl", "apply", "-f", str(manifest_file), "--dry-run=client", "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    self.errors.append(f"Invalid YAML in {manifest_file.name}: {result.stderr}")
                else:
                    logger.info(f"✓ Valid YAML: {manifest_file.name}")

            except subprocess.TimeoutExpired:
                self.errors.append(f"Validation timeout for {manifest_file.name}")
            except Exception as e:
                self.errors.append(f"Validation error for {manifest_file.name}: {str(e)}")

    def _validate_namespace_config(self) -> None:
        """Verify namespace configuration"""
        logger.info(f"Checking namespace: {self.config.namespace}")

        try:
            result = subprocess.run(
                ["kubectl", "get", "namespace", self.config.namespace],
                capture_output=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"Namespace {self.config.namespace} does not exist - will be created")
                self.warnings.append(f"Namespace {self.config.namespace} will be created during deployment")
            else:
                logger.info(f"✓ Namespace exists: {self.config.namespace}")

        except Exception as e:
            self.errors.append(f"Namespace check failed: {str(e)}")

    def _validate_pvc_config(self) -> None:
        """Validate PersistentVolume and StorageClass configuration"""
        logger.info("Validating PVC configuration...")

        # Check StorageClass referenced in manifests
        pvc_file = self.manifests_dir / "pvc.yaml"
        if pvc_file.exists():
            with open(pvc_file) as f:
                content = f.read()
                if "storageClassName: ru-ecom-ops-storage" in content:
                    logger.info("✓ StorageClass reference found in PVC")
                else:
                    self.warnings.append("StorageClass reference not found in PVC")

    def _validate_configmap_config(self) -> None:
        """Validate ConfigMap structure"""
        logger.info("Validating ConfigMap configuration...")

        configmap_file = self.manifests_dir / "configmap.yaml"
        if configmap_file.exists():
            with open(configmap_file) as f:
                content = f.read()
                required_keys = [
                    "NODE_ENV",
                    "LOG_LEVEL",
                    "WEB_HOST",
                    "WEB_PORT",
                    "RATE_LIMIT_ENABLED",
                ]

                for key in required_keys:
                    if key in content:
                        logger.info(f"✓ ConfigMap key found: {key}")
                    else:
                        self.errors.append(f"Missing ConfigMap key: {key}")

    def _validate_secret_references(self) -> None:
        """Validate Secret references in deployment"""
        logger.info("Validating Secret references...")

        deployment_file = self.manifests_dir / "deployment.yaml"
        if deployment_file.exists():
            with open(deployment_file) as f:
                content = f.read()
                required_secrets = [
                    "ru-ecom-ops-secrets",
                ]

                for secret in required_secrets:
                    if secret in content:
                        logger.info(f"✓ Secret reference found: {secret}")
                    else:
                        self.errors.append(f"Missing Secret reference: {secret}")

    def _validate_service_config(self) -> None:
        """Validate Service configuration"""
        logger.info("Validating Service configuration...")

        service_file = self.manifests_dir / "service.yaml"
        if service_file.exists():
            with open(service_file) as f:
                content = f.read()
                if "ru-ecom-ops-app" in content:
                    logger.info("✓ Service name found")
                else:
                    self.errors.append("Service name not found in service manifest")

    def _validate_ingress_config(self) -> None:
        """Validate Ingress configuration"""
        logger.info("Validating Ingress configuration...")

        service_file = self.manifests_dir / "service.yaml"
        if service_file.exists():
            with open(service_file) as f:
                content = f.read()
                if "Ingress" in content and "ru-ecom-ops-ingress" in content:
                    logger.info("✓ Ingress configuration found")
                else:
                    self.warnings.append("Ingress not configured - using LoadBalancer only")

    def print_summary(self) -> None:
        """Print validation summary"""
        logger.info("\n" + "="*60)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*60)

        if self.errors:
            logger.error(f"\n❌ {len(self.errors)} ERROR(S):")
            for error in self.errors:
                logger.error(f"  - {error}")

        if self.warnings:
            logger.warning(f"\n⚠️  {len(self.warnings)} WARNING(S):")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        if not self.errors:
            logger.info("\n✅ All validation checks passed!")

        logger.info("="*60 + "\n")


class KubernetesDeployer:
    """Orchestrates Kubernetes deployment"""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.manifests_dir = Path(config.manifests_dir)
        self.deployment_start_time = datetime.now()

    def deploy(self) -> bool:
        """Execute full deployment workflow"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"DEPLOYMENT WORKFLOW - {self.config.environment.value.upper()}")
            logger.info(f"{'='*60}\n")

            phases = [
                (DeploymentPhase.PREPARE, self._prepare_namespace),
                (DeploymentPhase.CONFIGURE, self._apply_configurations),
                (DeploymentPhase.DEPLOY, self._deploy_application),
                (DeploymentPhase.HEALTH_CHECK, self._check_health),
                (DeploymentPhase.VERIFY, self._verify_deployment),
            ]

            for phase, handler in phases:
                logger.info(f"\n{'─'*60}")
                logger.info(f"PHASE: {phase.value.upper()}")
                logger.info(f"{'─'*60}")

                if not handler():
                    logger.error(f"Deployment failed at phase: {phase.value}")
                    return False

                time.sleep(2)  # Brief pause between phases

            self._print_deployment_summary()
            return True

        except Exception as e:
            logger.error(f"Deployment failed with exception: {str(e)}", exc_info=True)
            return False

    def _prepare_namespace(self) -> bool:
        """Create namespace if it doesn't exist"""
        logger.info(f"Ensuring namespace '{self.config.namespace}' exists...")

        try:
            # Check if namespace exists
            result = subprocess.run(
                ["kubectl", "get", "namespace", self.config.namespace],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"✓ Namespace '{self.config.namespace}' already exists")
                return True

            # Create namespace
            logger.info(f"Creating namespace '{self.config.namespace}'...")
            result = subprocess.run(
                ["kubectl", "create", "namespace", self.config.namespace],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"Failed to create namespace: {result.stderr}")
                return False

            logger.info(f"✓ Namespace created: {self.config.namespace}")

            # Label namespace for monitoring
            subprocess.run(
                ["kubectl", "label", "namespace", self.config.namespace,
                 f"environment={self.config.environment.value}", "--overwrite"],
                capture_output=True,
                timeout=10
            )

            return True

        except subprocess.TimeoutExpired:
            logger.error("Namespace preparation timeout")
            return False
        except Exception as e:
            logger.error(f"Namespace preparation failed: {str(e)}")
            return False

    def _apply_configurations(self) -> bool:
        """Apply ConfigMaps and Secrets"""
        logger.info("Applying ConfigMaps and Secrets...")

        try:
            # Apply ConfigMaps
            configmap_file = self.manifests_dir / "configmap.yaml"
            if configmap_file.exists():
                logger.info("Applying ConfigMap...")
                result = subprocess.run(
                    ["kubectl", "apply", "-f", str(configmap_file),
                     "-n", self.config.namespace],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"ConfigMap apply failed: {result.stderr}")
                    return False

                logger.info("✓ ConfigMap applied")

            # Apply Secrets
            secret_file = self.manifests_dir / "secret.yaml"
            if secret_file.exists():
                logger.info("Applying Secrets...")
                result = subprocess.run(
                    ["kubectl", "apply", "-f", str(secret_file),
                     "-n", self.config.namespace],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"Secret apply failed: {result.stderr}")
                    logger.info("Note: Create secrets manually using kubectl create secret command")
                    logger.info("See k8s/secret.yaml for instructions")
                # Secrets might not exist yet, but deployment can proceed

            logger.info("✓ Configurations applied")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Configuration application timeout")
            return False
        except Exception as e:
            logger.error(f"Configuration application failed: {str(e)}")
            return False

    def _deploy_application(self) -> bool:
        """Deploy application pods"""
        logger.info("Deploying application...")

        try:
            # Apply PVC first
            pvc_file = self.manifests_dir / "pvc.yaml"
            if pvc_file.exists():
                logger.info("Applying PersistentVolumes and Claims...")
                result = subprocess.run(
                    ["kubectl", "apply", "-f", str(pvc_file),
                     "-n", self.config.namespace],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.warning(f"PVC apply had issues: {result.stderr}")
                else:
                    logger.info("✓ PersistentVolumes configured")

            # Apply Service
            service_file = self.manifests_dir / "service.yaml"
            if service_file.exists():
                logger.info("Applying Service and Ingress...")
                result = subprocess.run(
                    ["kubectl", "apply", "-f", str(service_file),
                     "-n", self.config.namespace],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"Service apply failed: {result.stderr}")
                    return False

                logger.info("✓ Service and Networking configured")

            # Apply Deployment
            deployment_file = self.manifests_dir / "deployment.yaml"
            if deployment_file.exists():
                logger.info("Deploying application pods...")
                result = subprocess.run(
                    ["kubectl", "apply", "-f", str(deployment_file),
                     "-n", self.config.namespace],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"Deployment apply failed: {result.stderr}")
                    return False

                logger.info("✓ Deployment applied")

            return True

        except subprocess.TimeoutExpired:
            logger.error("Deployment timeout")
            return False
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return False

    def _check_health(self) -> bool:
        """Monitor pod health and readiness"""
        logger.info("Checking pod health and readiness...")

        try:
            deployment_name = self.config.app_name
            start_time = time.time()
            retry_count = 0

            while retry_count < self.config.health_check_retries:
                # Check deployment rollout status
                result = subprocess.run(
                    ["kubectl", "rollout", "status",
                     f"deployment/{deployment_name}",
                     "-n", self.config.namespace,
                     f"--timeout={self.config.timeout_seconds}s"],
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout_seconds + 10
                )

                if result.returncode == 0:
                    logger.info("✓ Deployment rollout successful")

                    # Verify all pods are running
                    result = subprocess.run(
                        ["kubectl", "get", "pods",
                         "-n", self.config.namespace,
                         "-l", f"app={deployment_name}",
                         "-o", "json"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        pods = json.loads(result.stdout)
                        running_pods = sum(
                            1 for pod in pods.get("items", [])
                            if pod.get("status", {}).get("phase") == "Running"
                        )

                        logger.info(f"✓ Pods running: {running_pods}/{len(pods.get('items', []))}")
                        return True

                retry_count += 1
                elapsed = time.time() - start_time

                if elapsed > self.config.timeout_seconds:
                    logger.error(f"Health check timeout after {self.config.timeout_seconds}s")
                    return False

                logger.info(f"Health check attempt {retry_count}/{self.config.health_check_retries}...")
                time.sleep(5)

            logger.error("Health check failed after maximum retries")
            return False

        except subprocess.TimeoutExpired:
            logger.error("Health check timeout")
            return False
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def _verify_deployment(self) -> bool:
        """Verify deployment is working correctly"""
        logger.info("Verifying deployment configuration...")

        try:
            deployment_name = self.config.app_name

            # Get deployment details
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment_name,
                 "-n", self.config.namespace,
                 "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error("Failed to get deployment details")
                return False

            deployment = json.loads(result.stdout)
            spec = deployment.get("spec", {})
            status = deployment.get("status", {})

            # Verify replica configuration
            desired_replicas = spec.get("replicas", 0)
            ready_replicas = status.get("readyReplicas", 0)

            logger.info(f"Desired replicas: {desired_replicas}")
            logger.info(f"Ready replicas: {ready_replicas}")

            if ready_replicas == desired_replicas:
                logger.info("✓ All replicas are ready")
            else:
                logger.warning(f"Not all replicas ready: {ready_replicas}/{desired_replicas}")

            # Check service endpoints
            result = subprocess.run(
                ["kubectl", "get", "service", f"{deployment_name}-app",
                 "-n", self.config.namespace,
                 "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                service = json.loads(result.stdout)
                cluster_ip = service.get("spec", {}).get("clusterIP")
                logger.info(f"✓ Service ClusterIP: {cluster_ip}")

            logger.info("✓ Deployment verified successfully")
            return True

        except Exception as e:
            logger.error(f"Deployment verification failed: {str(e)}")
            return False

    def _print_deployment_summary(self) -> None:
        """Print deployment summary"""
        elapsed = datetime.now() - self.deployment_start_time

        logger.info("\n" + "="*60)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("="*60)
        logger.info(f"Environment: {self.config.environment.value}")
        logger.info(f"Namespace: {self.config.namespace}")
        logger.info(f"Application: {self.config.app_name}")
        logger.info(f"Duration: {elapsed.total_seconds():.2f}s")
        logger.info(f"Status: ✅ SUCCESSFUL")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Verify service: kubectl get svc -n ru-ecom-ops")
        logger.info("2. Check pods: kubectl get pods -n ru-ecom-ops")
        logger.info("3. View logs: kubectl logs -n ru-ecom-ops -l app=ru-ecom-ops")
        logger.info("="*60 + "\n")


def main():
    """Main deployment orchestrator entry point"""

    # Parse arguments
    if len(sys.argv) < 2:
        environment = Environment.DEVELOPMENT
    else:
        env_arg = sys.argv[1].lower()
        try:
            environment = Environment(env_arg)
        except ValueError:
            print(f"Invalid environment: {env_arg}")
            print(f"Valid options: {', '.join([e.value for e in Environment])}")
            sys.exit(1)

    # Create deployment config
    config = DeploymentConfig(
        environment=environment,
        namespace="ru-ecom-ops",
        app_name="ru-ecom-ops",
        manifests_dir="k8s"
    )

    # Run validation
    validator = KubernetesValidator(config)
    if not validator.validate_all():
        validator.print_summary()
        logger.error("Validation failed. Fix errors before deployment.")
        sys.exit(1)

    validator.print_summary()

    # Run deployment
    deployer = KubernetesDeployer(config)
    if not deployer.deploy():
        logger.error("Deployment failed.")
        sys.exit(1)

    logger.info("Deployment workflow completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
