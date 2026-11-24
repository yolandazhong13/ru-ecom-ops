#!/bin/bash

# Helm Chart Deployment Verification Script
# Verifies that the ru-ecom-ops monitoring stack is properly deployed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

NAMESPACE="${1:-ru-ecom-ops}"
RELEASE_NAME="ru-ecom-ops"
CHECK_TIMEOUT="${2:-300}" # 5 minutes default

# Functions
log_info() {
  echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
  echo -e "${RED}[✗]${NC} $1"
}

log_section() {
  echo -e "\n${BLUE}========== $1 ==========${NC}\n"
}

check_namespace() {
  log_section "Namespace Status"

  if kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    log_info "Namespace '$NAMESPACE' exists"
    kubectl describe namespace "$NAMESPACE" | grep -E "Name:|Status:"
    return 0
  else
    log_error "Namespace '$NAMESPACE' not found"
    return 1
  fi
}

check_helm_release() {
  log_section "Helm Release Status"

  if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
    log_info "Helm release '$RELEASE_NAME' found"
    helm status "$RELEASE_NAME" -n "$NAMESPACE"
    return 0
  else
    log_error "Helm release '$RELEASE_NAME' not found"
    return 1
  fi
}

check_pods() {
  log_section "Pod Status"

  local pods_ready=0
  local pods_total=0

  local pod_list=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

  if [[ -z "$pod_list" ]]; then
    log_error "No pods found in namespace '$NAMESPACE'"
    return 1
  fi

  for pod in $pod_list; do
    local ready=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    local phase=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.phase}')

    pods_total=$((pods_total + 1))

    if [[ "$ready" == "True" && "$phase" == "Running" ]]; then
      pods_ready=$((pods_ready + 1))
      log_info "Pod $pod is ready (Running)"
    else
      log_warn "Pod $pod status: $phase (Ready: $ready)"
    fi
  done

  echo -e "\nPods Ready: $pods_ready/$pods_total"

  if [[ $pods_ready -eq $pods_total ]]; then
    return 0
  else
    return 1
  fi
}

check_services() {
  log_section "Service Status"

  local services=$(kubectl get svc -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

  if [[ -z "$services" ]]; then
    log_error "No services found in namespace '$NAMESPACE'"
    return 1
  fi

  for svc in $services; do
    local svc_type=$(kubectl get svc "$svc" -n "$NAMESPACE" -o jsonpath='{.spec.type}')
    local cluster_ip=$(kubectl get svc "$svc" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    local endpoints=$(kubectl get endpoints "$svc" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)

    if [[ -n "$cluster_ip" && "$cluster_ip" != "None" ]]; then
      log_info "Service $svc: Type=$svc_type, ClusterIP=$cluster_ip, Endpoints=$endpoints"
    else
      log_warn "Service $svc: No ClusterIP assigned"
    fi
  done

  return 0
}

check_persistent_volumes() {
  log_section "PersistentVolumeClaim Status"

  local pvcs=$(kubectl get pvc -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

  if [[ -z "$pvcs" ]]; then
    log_warn "No PersistentVolumeClaims found (this is expected if persistence is disabled)"
    return 0
  fi

  for pvc in $pvcs; do
    local status=$(kubectl get pvc "$pvc" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
    local size=$(kubectl get pvc "$pvc" -n "$NAMESPACE" -o jsonpath='{.spec.resources.requests.storage}')

    if [[ "$status" == "Bound" ]]; then
      log_info "PVC $pvc: Status=$status, Size=$size"
    else
      log_warn "PVC $pvc: Status=$status (expected: Bound)"
    fi
  done

  return 0
}

check_secrets() {
  log_section "Secret Status"

  if kubectl get secret alertmanager-secrets -n "$NAMESPACE" > /dev/null 2>&1; then
    log_info "Secret 'alertmanager-secrets' found"
  else
    log_warn "Secret 'alertmanager-secrets' not found (Slack notifications will not work)"
  fi

  if kubectl get secret alertmanager-pagerduty -n "$NAMESPACE" > /dev/null 2>&1; then
    log_info "Secret 'alertmanager-pagerduty' found"
  else
    log_warn "Secret 'alertmanager-pagerduty' not found (PagerDuty integration will not work)"
  fi
}

check_resource_usage() {
  log_section "Resource Usage"

  if ! command -v kubectl &> /dev/null; then
    log_warn "kubectl metrics not available"
    return 0
  fi

  if kubectl top pods -n "$NAMESPACE" > /dev/null 2>&1; then
    kubectl top pods -n "$NAMESPACE"
  else
    log_warn "Metrics server not available (run 'kubectl top pods' manually to check)"
  fi
}

check_logs() {
  log_section "Recent Logs"

  local pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

  for pod in $pods; do
    echo -e "\n${BLUE}--- Logs for pod: $pod ---${NC}"
    kubectl logs "$pod" -n "$NAMESPACE" --tail=20 2>/dev/null || log_warn "Could not retrieve logs for $pod"
  done
}

wait_for_pods() {
  log_section "Waiting for Pods to be Ready"

  echo "Waiting up to $CHECK_TIMEOUT seconds for pods to be ready..."

  if kubectl wait --for=condition=Ready pod \
     -l "app in (prometheus,alertmanager)" \
     -n "$NAMESPACE" \
     --timeout="${CHECK_TIMEOUT}s" 2>/dev/null; then
    log_info "All pods are ready!"
    return 0
  else
    log_warn "Timeout waiting for pods to be ready"
    return 1
  fi
}

generate_access_commands() {
  log_section "Access Commands"

  echo "To access the services, run:"
  echo
  echo "Prometheus:"
  echo "  kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-prometheus 9090:9090"
  echo "  Then open: http://localhost:9090"
  echo
  echo "Alertmanager:"
  echo "  kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-alertmanager 9093:9093"
  echo "  Then open: http://localhost:9093"
  echo
  echo "View logs:"
  echo "  kubectl logs -n $NAMESPACE -l app=prometheus -f"
  echo "  kubectl logs -n $NAMESPACE -l app=alertmanager -f"
  echo
}

generate_summary() {
  log_section "Deployment Summary"

  echo "Namespace: $NAMESPACE"
  echo "Release: $RELEASE_NAME"
  echo "Deployment Time: $(date)"
  echo

  local pod_count=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
  echo "Total Pods: $pod_count"

  local svc_count=$(kubectl get svc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
  echo "Total Services: $svc_count"

  local pvc_count=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
  echo "Total PersistentVolumeClaims: $pvc_count"
}

# Main execution
main() {
  echo "========================================"
  echo "Helm Deployment Verification"
  echo "========================================"

  local overall_status=0

  check_namespace || overall_status=1
  check_helm_release || overall_status=1
  wait_for_pods || log_warn "Pods did not become ready within timeout"
  check_pods || overall_status=1
  check_services || overall_status=1
  check_persistent_volumes || overall_status=1
  check_secrets || overall_status=1
  check_resource_usage || true
  check_logs || true
  generate_access_commands
  generate_summary

  echo
  echo "========================================"
  if [[ $overall_status -eq 0 ]]; then
    log_info "All checks passed! Deployment is healthy."
  else
    log_warn "Some checks failed. Review the output above."
  fi
  echo "========================================"

  return $overall_status
}

main "$@"
