#!/bin/bash

# Helm Chart Deployment Script
# Deploys the ru-ecom-ops monitoring stack to a target environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HELM_CHART_DIR="$PROJECT_ROOT/helm/ru-ecom-ops"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-}"
NAMESPACE="ru-ecom-ops"
RELEASE_NAME="ru-ecom-ops"
DRY_RUN="${2:-false}"

# Functions
log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
  echo -e "\n${BLUE}========== $1 ==========${NC}\n"
}

show_usage() {
  cat << EOF
Usage: $0 <environment> [dry-run]

Arguments:
  environment    Target environment (dev, staging, prod)
  dry-run       Optional: Set to 'true' for dry-run mode (default: false)

Examples:
  $0 dev              # Deploy to development
  $0 staging          # Deploy to staging
  $0 prod dry-run     # Dry-run deployment to production
  $0 prod true        # Dry-run deployment to production

EOF
}

validate_environment() {
  if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment not specified"
    show_usage
    exit 1
  fi

  if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    echo "Valid environments: dev, staging, prod"
    exit 1
  fi
}

check_prerequisites() {
  log_section "Checking Prerequisites"

  # Check Helm
  if ! command -v helm &> /dev/null; then
    log_error "Helm is not installed. Please install Helm v3.0+"
    exit 1
  fi
  log_info "Helm found: $(helm version --short)"

  # Check kubectl
  if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed"
    exit 1
  fi
  log_info "kubectl found: $(kubectl version --client --short 2>/dev/null || echo 'connected')"

  # Check cluster connection
  if ! kubectl cluster-info > /dev/null 2>&1; then
    log_error "Cannot connect to Kubernetes cluster. Check kubeconfig."
    exit 1
  fi
  log_info "Kubernetes cluster accessible"

  # Check namespace
  if ! kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    log_warn "Namespace '$NAMESPACE' does not exist. It will be created."
  else
    log_info "Namespace '$NAMESPACE' exists"
  fi
}

check_secrets() {
  log_section "Checking Secrets"

  # Check Slack secret
  if ! kubectl get secret alertmanager-secrets -n "$NAMESPACE" > /dev/null 2>&1; then
    log_warn "Secret 'alertmanager-secrets' not found in namespace '$NAMESPACE'"
    log_warn "Slack notifications will not work without this secret"
    log_warn "Create it with: kubectl create secret generic alertmanager-secrets --from-literal=slack-webhook-url='https://...' -n $NAMESPACE"
  else
    log_info "Secret 'alertmanager-secrets' found"
  fi

  # Check PagerDuty secret (only for staging/prod)
  if [[ "$ENVIRONMENT" != "dev" ]]; then
    if ! kubectl get secret alertmanager-pagerduty -n "$NAMESPACE" > /dev/null 2>&1; then
      log_warn "Secret 'alertmanager-pagerduty' not found in namespace '$NAMESPACE'"
      log_warn "PagerDuty integration will not work without this secret"
      log_warn "Create it with: kubectl create secret generic alertmanager-pagerduty --from-literal=pagerduty-routing-key='...' -n $NAMESPACE"
    else
      log_info "Secret 'alertmanager-pagerduty' found"
    fi
  fi
}

get_values_file() {
  local values_file="$HELM_CHART_DIR/values-${ENVIRONMENT}.yaml"

  if [[ ! -f "$values_file" ]]; then
    log_error "Values file not found: $values_file"
    exit 1
  fi

  echo "$values_file"
}

dry_run_deployment() {
  local values_file=$(get_values_file)

  log_section "Dry-Run: Template Rendering"

  log_info "Rendering templates for environment: $ENVIRONMENT"
  helm template "$RELEASE_NAME" "$HELM_CHART_DIR" \
    -n "$NAMESPACE" \
    -f "$values_file" \
    --debug
}

deploy() {
  local values_file=$(get_values_file)

  log_section "Deploying to $ENVIRONMENT"

  # Create namespace if it doesn't exist
  if ! kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    log_info "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
  fi

  # Check if release exists
  if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
    log_info "Release exists. Upgrading..."
    helm upgrade "$RELEASE_NAME" "$HELM_CHART_DIR" \
      -n "$NAMESPACE" \
      -f "$values_file" \
      --wait \
      --timeout 5m
  else
    log_info "Release does not exist. Installing..."
    helm install "$RELEASE_NAME" "$HELM_CHART_DIR" \
      -n "$NAMESPACE" \
      -f "$values_file" \
      --wait \
      --timeout 5m
  fi

  log_info "Deployment complete!"
}

verify_deployment() {
  log_section "Verifying Deployment"

  log_info "Checking pod status..."
  kubectl get pods -n "$NAMESPACE" -l app=prometheus,app=alertmanager

  log_info "Checking services..."
  kubectl get svc -n "$NAMESPACE"

  log_info "Checking PersistentVolumeClaims..."
  kubectl get pvc -n "$NAMESPACE"

  log_info "Release status:"
  helm status "$RELEASE_NAME" -n "$NAMESPACE"
}

show_next_steps() {
  log_section "Next Steps"

  echo "1. Verify pods are running:"
  echo "   kubectl get pods -n $NAMESPACE -w"
  echo
  echo "2. Access Prometheus:"
  echo "   kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-prometheus 9090:9090"
  echo "   Then open: http://localhost:9090"
  echo
  echo "3. Access Alertmanager:"
  echo "   kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-alertmanager 9093:9093"
  echo "   Then open: http://localhost:9093"
  echo
  echo "4. Check logs:"
  echo "   kubectl logs -n $NAMESPACE -l app=prometheus --tail=50"
  echo "   kubectl logs -n $NAMESPACE -l app=alertmanager --tail=50"
  echo
}

# Main execution
main() {
  echo "========================================"
  echo "Helm Chart Deployment - ru-ecom-ops"
  echo "Environment: $ENVIRONMENT"
  echo "========================================"

  validate_environment
  check_prerequisites
  check_secrets

  if [[ "$DRY_RUN" == "true" || "$DRY_RUN" == "dry-run" ]]; then
    dry_run_deployment
  else
    deploy
    verify_deployment
    show_next_steps
  fi

  log_info "Deployment process completed successfully! ✓"
}

main "$@"
