#!/bin/bash

#############################################
# GitHub Actions CI/CD Setup Verification
#############################################
# This script verifies all components of the
# GitHub Actions setup are properly configured
# before running production deployments.
#############################################

set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
log_info() {
  echo -e "${BLUE}ℹ${NC} $1"
}

log_pass() {
  echo -e "${GREEN}✓${NC} $1"
  ((PASSED++))
}

log_fail() {
  echo -e "${RED}✗${NC} $1"
  ((FAILED++))
}

log_warn() {
  echo -e "${YELLOW}!${NC} $1"
  ((WARNINGS++))
}

log_section() {
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

separator() {
  echo ""
}

#############################################
# Verification Functions
#############################################

verify_prerequisites() {
  log_section "1. Verifying Prerequisites"

  # Check required commands
  commands=("git" "kubectl" "helm" "yq" "jq")

  for cmd in "${commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
      VERSION=$(get_version "$cmd")
      log_pass "$cmd is installed ($VERSION)"
    else
      log_fail "$cmd is not installed"
    fi
  done

  # Check GitHub CLI
  if command -v gh &> /dev/null; then
    log_pass "GitHub CLI is installed"

    # Check if authenticated
    if gh auth status &> /dev/null; then
      GITHUB_USER=$(gh api user --jq '.login' 2>/dev/null || echo "unknown")
      log_pass "GitHub CLI is authenticated (user: $GITHUB_USER)"
    else
      log_fail "GitHub CLI is not authenticated"
      log_info "Run: gh auth login"
    fi
  else
    log_warn "GitHub CLI is not installed (optional but recommended)"
  fi
}

get_version() {
  case $1 in
    git)
      git --version 2>/dev/null | awk '{print $3}'
      ;;
    kubectl)
      kubectl version --client --short 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' | head -1 || echo "unknown"
      ;;
    helm)
      helm version --short 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' | head -1 || echo "unknown"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

verify_repository_structure() {
  log_section "2. Verifying Repository Structure"

  # Check required directories
  REQUIRED_DIRS=(
    ".github/workflows"
    "helm/ru-ecom-ops"
    "helm/ru-ecom-ops/templates"
    "scripts"
  )

  for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
      log_pass "Directory exists: $dir"
    else
      log_fail "Directory missing: $dir"
    fi
  done

  # Check required workflow files
  WORKFLOWS=(
    ".github/workflows/helm-validate.yml"
    ".github/workflows/deploy-dev.yml"
    ".github/workflows/deploy-staging.yml"
    ".github/workflows/deploy-prod.yml"
  )

  for workflow in "${WORKFLOWS[@]}"; do
    if [ -f "$workflow" ]; then
      log_pass "Workflow file exists: $workflow"
    else
      log_fail "Workflow file missing: $workflow"
    fi
  done

  # Check required scripts
  SCRIPTS=(
    "scripts/validate-helm-chart.sh"
    "scripts/deploy-helm-chart.sh"
    "scripts/verify-deployment.sh"
  )

  for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
      log_pass "Script exists: $script"
      if [ -x "$script" ]; then
        log_pass "  └─ Script is executable"
      else
        log_warn "  └─ Script is not executable (chmod +x)"
      fi
    else
      log_fail "Script missing: $script"
    fi
  done

  # Check Helm chart structure
  CHART_FILES=(
    "helm/ru-ecom-ops/Chart.yaml"
    "helm/ru-ecom-ops/values.yaml"
    "helm/ru-ecom-ops/values-dev.yaml"
    "helm/ru-ecom-ops/values-staging.yaml"
    "helm/ru-ecom-ops/values-prod.yaml"
  )

  for file in "${CHART_FILES[@]}"; do
    if [ -f "$file" ]; then
      log_pass "Chart file exists: $file"
    else
      log_fail "Chart file missing: $file"
    fi
  done
}

verify_helm_chart() {
  log_section "3. Verifying Helm Chart"

  # Lint chart
  if helm lint helm/ru-ecom-ops &> /dev/null; then
    log_pass "Helm chart linting passed"
  else
    log_fail "Helm chart linting failed"
    helm lint helm/ru-ecom-ops
    return 1
  fi

  # Test template rendering for each environment
  ENVIRONMENTS=("dev" "staging" "prod")

  for env in "${ENVIRONMENTS[@]}"; do
    VALUES_FILE="helm/ru-ecom-ops/values-${env}.yaml"
    TEMP_MANIFEST="/tmp/${env}-manifest-verify.yaml"

    if helm template ru-ecom-ops helm/ru-ecom-ops \
      -f "$VALUES_FILE" > "$TEMP_MANIFEST" 2>&1; then
      MANIFEST_SIZE=$(wc -l < "$TEMP_MANIFEST")
      log_pass "Helm template rendering passed for $env ($MANIFEST_SIZE lines)"
      rm -f "$TEMP_MANIFEST"
    else
      log_fail "Helm template rendering failed for $env"
    fi
  done
}

verify_workflow_yaml() {
  log_section "4. Verifying Workflow YAML Syntax"

  # Check if yamllint is available
  if ! command -v yamllint &> /dev/null; then
    log_warn "yamllint not installed (skipping YAML syntax check)"
    log_info "Install with: brew install yamllint (macOS) or apt-get install yamllint (Linux)"
    return 0
  fi

  WORKFLOWS=(
    ".github/workflows/helm-validate.yml"
    ".github/workflows/deploy-dev.yml"
    ".github/workflows/deploy-staging.yml"
    ".github/workflows/deploy-prod.yml"
  )

  for workflow in "${WORKFLOWS[@]}"; do
    if yamllint "$workflow" &> /dev/null; then
      log_pass "YAML syntax valid: $workflow"
    else
      log_fail "YAML syntax invalid: $workflow"
    fi
  done
}

verify_github_secrets() {
  log_section "5. Verifying GitHub Secrets"

  # Check if gh is available and authenticated
  if ! command -v gh &> /dev/null; then
    log_warn "GitHub CLI not available (cannot verify secrets)"
    return 0
  fi

  if ! gh auth status &> /dev/null; then
    log_warn "GitHub CLI not authenticated (cannot verify secrets)"
    return 0
  fi

  REPO=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')

  if [ -z "$REPO" ]; then
    log_fail "Could not determine GitHub repository"
    return 1
  fi

  log_info "Checking secrets for repository: $REPO"

  REQUIRED_SECRETS=(
    "KUBECONFIG_DEV"
    "KUBECONFIG_STAGING"
    "KUBECONFIG_PROD"
    "SLACK_WEBHOOK_DEV"
    "SLACK_WEBHOOK_STAGING"
    "SLACK_WEBHOOK_PROD"
    "PAGERDUTY_ROUTING_KEY_STAGING"
    "PAGERDUTY_ROUTING_KEY_PROD"
  )

  for secret in "${REQUIRED_SECRETS[@]}"; do
    if gh secret list --repo "$REPO" 2>/dev/null | grep -q "^$secret"; then
      log_pass "Secret configured: $secret"
    else
      log_fail "Secret missing: $secret"
    fi
  done
}

verify_kubeconfig() {
  log_section "6. Verifying Kubernetes Configurations"

  KUBECONFIGS=(
    "~/.kube/config-dev:KUBECONFIG_DEV"
    "~/.kube/config-staging:KUBECONFIG_STAGING"
    "~/.kube/config-prod:KUBECONFIG_PROD"
  )

  for item in "${KUBECONFIGS[@]}"; do
    FILE="${item%%:*}"
    SECRET_NAME="${item##*:}"
    FILE_EXPANDED="${FILE/#\~/$HOME}"

    if [ ! -f "$FILE_EXPANDED" ]; then
      log_warn "Kubeconfig not found: $FILE (required for $SECRET_NAME)"
      continue
    fi

    log_pass "Kubeconfig file exists: $FILE"

    # Test kubeconfig locally
    if KUBECONFIG="$FILE_EXPANDED" kubectl cluster-info &> /dev/null; then
      CLUSTER_NAME=$(KUBECONFIG="$FILE_EXPANDED" kubectl config current-context 2>/dev/null || echo "unknown")
      log_pass "  └─ Kubeconfig is valid (context: $CLUSTER_NAME)"
    else
      log_fail "  └─ Kubeconfig is invalid or unreachable"
    fi

    # Test base64 encoding
    if command -v base64 &> /dev/null; then
      ENCODED=$(cat "$FILE_EXPANDED" | base64 -w0)
      ENCODED_SIZE=${#ENCODED}
      ORIGINAL_SIZE=$(wc -c < "$FILE_EXPANDED")

      # Verify encoding/decoding cycle
      DECODED=$(echo "$ENCODED" | base64 -d)
      if [ "$(echo "$DECODED" | wc -c)" -eq "$ORIGINAL_SIZE" ]; then
        log_pass "  └─ Base64 encoding/decoding verified ($ENCODED_SIZE bytes encoded)"
      else
        log_fail "  └─ Base64 encoding/decoding cycle failed"
      fi
    fi
  done
}

verify_slack_webhooks() {
  log_section "7. Verifying Slack Webhooks"

  if ! command -v gh &> /dev/null; then
    log_warn "GitHub CLI not available (cannot verify Slack webhooks)"
    return 0
  fi

  if ! gh auth status &> /dev/null; then
    log_warn "GitHub CLI not authenticated (cannot verify Slack webhooks)"
    return 0
  fi

  REPO=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')

  SLACK_WEBHOOKS=(
    "SLACK_WEBHOOK_DEV"
    "SLACK_WEBHOOK_STAGING"
    "SLACK_WEBHOOK_PROD"
  )

  for webhook_secret in "${SLACK_WEBHOOKS[@]}"; do
    # Note: We can't directly read secret values, only check if they exist
    if gh secret list --repo "$REPO" 2>/dev/null | grep -q "^$webhook_secret"; then
      log_pass "Slack webhook secret configured: $webhook_secret"
      log_info "  └─ To test webhook, run: curl -X POST \$<SECRET_VALUE> -H 'Content-Type: application/json' -d '{\"text\":\"test\"}'"
    else
      log_fail "Slack webhook secret missing: $webhook_secret"
    fi
  done
}

verify_pagerduty_keys() {
  log_section "8. Verifying PagerDuty Configuration"

  if ! command -v gh &> /dev/null; then
    log_warn "GitHub CLI not available (cannot verify PagerDuty keys)"
    return 0
  fi

  if ! gh auth status &> /dev/null; then
    log_warn "GitHub CLI not authenticated (cannot verify PagerDuty keys)"
    return 0
  fi

  REPO=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')

  PD_KEYS=(
    "PAGERDUTY_ROUTING_KEY_STAGING"
    "PAGERDUTY_ROUTING_KEY_PROD"
  )

  for pd_key in "${PD_KEYS[@]}"; do
    if gh secret list --repo "$REPO" 2>/dev/null | grep -q "^$pd_key"; then
      log_pass "PagerDuty key configured: $pd_key"
    else
      log_fail "PagerDuty key missing: $pd_key"
    fi
  done
}

verify_github_environments() {
  log_section "9. Verifying GitHub Environments"

  if ! command -v gh &> /dev/null; then
    log_warn "GitHub CLI not available (cannot verify environments)"
    return 0
  fi

  if ! gh auth status &> /dev/null; then
    log_warn "GitHub CLI not authenticated (cannot verify environments)"
    return 0
  fi

  REPO=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')

  ENVIRONMENTS=("development" "staging" "production")

  for env in "${ENVIRONMENTS[@]}"; do
    if gh api repos/"$REPO"/environments/"$env" &> /dev/null; then
      log_pass "Environment configured: $env"
    else
      log_warn "Environment not found: $env"
    fi
  done
}

generate_report() {
  log_section "Setup Verification Summary"

  echo ""
  echo "Passed:  ${GREEN}$PASSED${NC}"
  echo "Failed:  ${RED}$FAILED${NC}"
  echo "Warnings: ${YELLOW}$WARNINGS${NC}"
  echo ""

  if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Your setup is ready.${NC}"
    return 0
  else
    echo -e "${RED}✗ $FAILED checks failed. Please review the output above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  1. Missing secrets: Add via GitHub Settings → Secrets and variables → Actions"
    echo "  2. Missing files: Create required Helm charts and workflow files"
    echo "  3. Script permissions: Run 'chmod +x scripts/*.sh'"
    echo "  4. Kubeconfig issues: Verify file exists and is valid with kubectl"
    return 1
  fi
}

#############################################
# Main Execution
#############################################

main() {
  echo ""
  echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║   GitHub Actions CI/CD Setup Verification Script           ║${NC}"
  echo -e "${BLUE}║   Verifying Helm Deployment Pipeline Configuration        ║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""

  verify_prerequisites
  verify_repository_structure
  verify_helm_chart
  verify_workflow_yaml
  verify_github_secrets
  verify_kubeconfig
  verify_slack_webhooks
  verify_pagerduty_keys
  verify_github_environments

  generate_report
}

main
