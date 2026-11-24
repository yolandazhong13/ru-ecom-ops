#!/bin/bash

# Helm Chart Validation Script
# Validates the ru-ecom-ops Helm chart across all environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HELM_CHART_DIR="$PROJECT_ROOT/helm/ru-ecom-ops"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

validate_helm_installed() {
  if ! command -v helm &> /dev/null; then
    log_error "Helm is not installed. Please install Helm v3.0+ to continue."
    exit 1
  fi

  HELM_VERSION=$(helm version --short)
  log_info "Using Helm: $HELM_VERSION"
}

validate_chart_structure() {
  log_info "Validating chart structure..."

  local required_files=(
    "Chart.yaml"
    "values.yaml"
    "values-dev.yaml"
    "values-staging.yaml"
    "values-prod.yaml"
    "templates/_helpers.tpl"
    "templates/prometheus-config.yaml"
    "templates/prometheus-deployment.yaml"
    "templates/alertmanager-deployment.yaml"
  )

  for file in "${required_files[@]}"; do
    if [[ ! -f "$HELM_CHART_DIR/$file" ]]; then
      log_error "Missing required file: $file"
      exit 1
    fi
  done

  log_info "Chart structure validation passed ✓"
}

lint_chart() {
  log_info "Running helm lint..."

  if helm lint "$HELM_CHART_DIR" > /dev/null 2>&1; then
    log_info "Chart linting passed ✓"
  else
    log_error "Chart linting failed"
    helm lint "$HELM_CHART_DIR"
    exit 1
  fi
}

validate_environment() {
  local env=$1
  local values_file="$HELM_CHART_DIR/values-${env}.yaml"

  log_info "Validating environment: $env"

  if [[ ! -f "$values_file" ]]; then
    log_error "Values file not found: $values_file"
    exit 1
  fi

  # Test dry-run template rendering
  if ! helm template ru-ecom-ops "$HELM_CHART_DIR" -f "$values_file" > /dev/null 2>&1; then
    log_error "Template rendering failed for environment: $env"
    helm template ru-ecom-ops "$HELM_CHART_DIR" -f "$values_file"
    exit 1
  fi

  log_info "Environment $env validation passed ✓"
}

generate_manifests() {
  local env=$1
  local output_dir="$PROJECT_ROOT/manifests"
  local values_file="$HELM_CHART_DIR/values-${env}.yaml"

  mkdir -p "$output_dir"

  log_info "Generating manifests for environment: $env"
  helm template ru-ecom-ops "$HELM_CHART_DIR" \
    -f "$values_file" \
    > "$output_dir/ru-ecom-ops-${env}.yaml"

  log_info "Manifests generated: $output_dir/ru-ecom-ops-${env}.yaml"
}

validate_yaml_syntax() {
  local env=$1
  local manifest_file="$PROJECT_ROOT/manifests/ru-ecom-ops-${env}.yaml"

  log_info "Validating YAML syntax for environment: $env"

  if ! kubectl apply -f "$manifest_file" --dry-run=client > /dev/null 2>&1; then
    log_warn "kubectl validation failed (this may require cluster access)"
  else
    log_info "YAML syntax validation passed ✓"
  fi
}

# Main execution
main() {
  echo "========================================"
  echo "Helm Chart Validation - ru-ecom-ops"
  echo "========================================"
  echo

  validate_helm_installed
  validate_chart_structure
  lint_chart

  echo
  log_info "Validating environment-specific configurations..."
  echo

  for env in dev staging prod; do
    validate_environment "$env"
    generate_manifests "$env"
    echo
  done

  echo
  log_info "All validations completed successfully! ✓"
  echo
  echo "Generated manifests:"
  echo "  - $PROJECT_ROOT/manifests/ru-ecom-ops-dev.yaml"
  echo "  - $PROJECT_ROOT/manifests/ru-ecom-ops-staging.yaml"
  echo "  - $PROJECT_ROOT/manifests/ru-ecom-ops-prod.yaml"
  echo
  echo "Next steps:"
  echo "  1. Review manifests for environment-specific settings"
  echo "  2. Create required secrets (Slack, PagerDuty)"
  echo "  3. Deploy to target Kubernetes cluster"
  echo "========================================"
}

main "$@"
