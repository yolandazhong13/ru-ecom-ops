# Helm Deployment Guide for ru-ecom-ops Monitoring Stack

## Overview

This guide covers deploying the ru-ecom-ops monitoring stack (Prometheus + Alertmanager) using Helm charts. The chart supports multi-environment deployments with environment-specific configurations for development, staging, and production.

---

## Prerequisites

1. **Kubernetes Cluster** (v1.19+)
   - kubectl configured and authenticated
   - Storage provisioning available (StorageClass: `standard`)

2. **Helm** (v3.0+)
   ```bash
   helm version
   ```

3. **Namespace** - Create the target namespace (or Helm will create it)
   ```bash
   kubectl create namespace ru-ecom-ops
   ```

4. **Slack Integration** (optional)
   - Slack workspace with admin access
   - Incoming Webhook URL for notifications
   - Channels: #alerts, #critical-alerts, #monitoring

5. **PagerDuty Integration** (optional)
   - PagerDuty account with integration key
   - Routing key for critical alerts

---

## Quick Start

### 1. Create Slack Webhook Secret

```bash
# Create secret with Slack webhook URL
kubectl create secret generic alertmanager-secrets \
  --from-literal=slack-webhook-url='https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK/URL' \
  -n ru-ecom-ops

# Verify secret created
kubectl get secrets -n ru-ecom-ops | grep alertmanager
```

### 2. Deploy to Development Environment

```bash
# Navigate to Helm chart directory
cd helm/ru-ecom-ops

# Install with development values
helm install ru-ecom-ops . \
  -n ru-ecom-ops \
  -f values-dev.yaml

# Verify deployment
kubectl get pods -n ru-ecom-ops
kubectl get svc -n ru-ecom-ops
```

### 3. Deploy to Staging Environment

```bash
helm install ru-ecom-ops . \
  -n ru-ecom-ops \
  -f values-staging.yaml
```

### 4. Deploy to Production Environment

```bash
helm install ru-ecom-ops . \
  -n ru-ecom-ops \
  -f values-prod.yaml
```

---

## Helm Chart Structure

```
helm/ru-ecom-ops/
├── Chart.yaml                          # Chart metadata
├── values.yaml                         # Default values
├── values-dev.yaml                    # Development overrides
├── values-staging.yaml                # Staging overrides
├── values-prod.yaml                   # Production overrides
├── templates/
│   ├── _helpers.tpl                  # Template helpers
│   ├── prometheus-config.yaml        # Prometheus ConfigMaps
│   ├── prometheus-deployment.yaml    # Prometheus Deployment
│   └── alertmanager-deployment.yaml  # Alertmanager Deployment
└── README.md                          # Chart documentation
```

---

## Configuration Management

### Default Values (`values.yaml`)

The base configuration provides sensible defaults for all components:

```yaml
namespace: ru-ecom-ops
prometheus:
  replicaCount: 2
  persistence:
    size: 50Gi
  retention:
    time: 30d
alertmanager:
  replicaCount: 2
  slack:
    enabled: true
```

### Environment-Specific Overrides

Override specific values per environment:

```bash
# Development: Relaxed thresholds, lower resources
helm install ru-ecom-ops . -f values-dev.yaml

# Staging: Moderate resources, intermediate thresholds
helm install ru-ecom-ops . -f values-staging.yaml

# Production: Maximum resources, strict thresholds
helm install ru-ecom-ops . -f values-prod.yaml
```

### Custom Values at Deploy Time

Override values directly on the command line:

```bash
helm install ru-ecom-ops . \
  --set prometheus.replicaCount=3 \
  --set prometheus.persistence.size=100Gi \
  --set alertmanager.slack.webhookUrlSecret=custom-secret
```

---

## Common Helm Operations

### 1. Install Chart

```bash
helm install <release-name> <chart-path> \
  -n <namespace> \
  -f <values-file>
```

### 2. Upgrade Chart

```bash
# Upgrade to latest chart version
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops

# Upgrade with new values
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  -f values-prod.yaml
```

### 3. Rollback Deployment

```bash
# List release history
helm history ru-ecom-ops -n ru-ecom-ops

# Rollback to previous release
helm rollback ru-ecom-ops 1 -n ru-ecom-ops

# Rollback to specific revision
helm rollback ru-ecom-ops 2 -n ru-ecom-ops
```

### 4. Uninstall Chart

```bash
helm uninstall ru-ecom-ops -n ru-ecom-ops
```

### 5. Dry Run / Template Preview

```bash
# Preview rendered templates
helm template ru-ecom-ops ./helm/ru-ecom-ops \
  -f values-prod.yaml

# Validate chart without installing
helm lint ./helm/ru-ecom-ops
```

---

## Verifying Deployment

### 1. Check Pod Status

```bash
# Watch pods starting
kubectl get pods -n ru-ecom-ops -w

# View pod details
kubectl describe pod -n ru-ecom-ops -l app=prometheus
```

### 2. Check Service Endpoints

```bash
# List services
kubectl get svc -n ru-ecom-ops

# Check service endpoints
kubectl get endpoints -n ru-ecom-ops
```

### 3. Access Prometheus UI

```bash
# Port forward to Prometheus
kubectl port-forward -n ru-ecom-ops svc/ru-ecom-ops-prometheus 9090:9090

# Access browser: http://localhost:9090
# Check Status → Targets to verify scraping
```

### 4. Access Alertmanager UI

```bash
# Port forward to Alertmanager
kubectl port-forward -n ru-ecom-ops svc/ru-ecom-ops-alertmanager 9093:9093

# Access browser: http://localhost:9093
# Check Status to verify configuration is loaded
```

### 5. Verify PersistentVolumeClaims

```bash
# Check PVC status
kubectl get pvc -n ru-ecom-ops

# Check PVC disk usage
kubectl exec -n ru-ecom-ops \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- df -h /prometheus
```

---

## Scaling and Resizing

### 1. Scale Replicas

```bash
# Scale Prometheus replicas
kubectl scale deployment -n ru-ecom-ops \
  --replicas=3 \
  ru-ecom-ops-prometheus

# Scale Alertmanager replicas
kubectl scale deployment -n ru-ecom-ops \
  --replicas=3 \
  ru-ecom-ops-alertmanager
```

### 2. Increase Storage

```bash
# Increase Prometheus storage
kubectl patch pvc -n ru-ecom-ops \
  ru-ecom-ops-prometheus-storage \
  -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# Increase Alertmanager storage
kubectl patch pvc -n ru-ecom-ops \
  ru-ecom-ops-alertmanager-storage \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

### 3. Update Resource Limits

```bash
# Using Helm upgrade
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  --set prometheus.resources.limits.memory=4Gi \
  --set prometheus.resources.requests.memory=1Gi
```

---

## Troubleshooting

### 1. Pod Not Starting

```bash
# Check pod logs
kubectl logs -n ru-ecom-ops -l app=prometheus --tail=50

# Check pod events
kubectl describe pod -n ru-ecom-ops -l app=prometheus

# Check resource availability
kubectl top nodes
kubectl top pods -n ru-ecom-ops
```

### 2. PersistentVolume Issues

```bash
# Check PVC status
kubectl get pvc -n ru-ecom-ops

# Check PV status
kubectl get pv

# Check storage class availability
kubectl get storageclass

# Describe PVC for events
kubectl describe pvc -n ru-ecom-ops ru-ecom-ops-prometheus-storage
```

### 3. Network Connectivity

```bash
# Check service DNS resolution
kubectl exec -n ru-ecom-ops -it \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- nslookup ru-ecom-ops-alertmanager

# Test connectivity to Alertmanager
kubectl exec -n ru-ecom-ops -it \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- wget -O- http://ru-ecom-ops-alertmanager:9093/-/ready
```

### 4. Helm Release Issues

```bash
# Check release status
helm status ru-ecom-ops -n ru-ecom-ops

# View release values
helm get values ru-ecom-ops -n ru-ecom-ops

# View rendered manifests
helm get manifest ru-ecom-ops -n ru-ecom-ops

# Check for helm hooks
helm get hooks ru-ecom-ops -n ru-ecom-ops
```

---

## CI/CD Integration

### GitOps with ArgoCD

```bash
# Create ArgoCD Application for Helm chart
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ru-ecom-ops-monitoring
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/ru-ecom-ops
    targetRevision: main
    path: helm/ru-ecom-ops
    helm:
      releaseName: ru-ecom-ops
      values: |
        global:
          environment: production
  destination:
    server: https://kubernetes.default.svc
    namespace: ru-ecom-ops
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

### GitHub Actions CI/CD Pipeline

```yaml
name: Deploy Monitoring Stack
on:
  push:
    branches: [main]
    paths:
      - 'helm/ru-ecom-ops/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Helm Lint
        run: helm lint ./helm/ru-ecom-ops
      
      - name: Helm Dry Run
        run: |
          helm template ru-ecom-ops ./helm/ru-ecom-ops \
            -f helm/ru-ecom-ops/values-prod.yaml | \
            kubectl --kubeconfig=${{ secrets.KUBECONFIG }} \
            apply -n ru-ecom-ops -f - --dry-run=client
      
      - name: Helm Install/Upgrade
        run: |
          helm upgrade --install ru-ecom-ops ./helm/ru-ecom-ops \
            --kubeconfig=${{ secrets.KUBECONFIG }} \
            -n ru-ecom-ops \
            -f helm/ru-ecom-ops/values-prod.yaml
```

---

## Disaster Recovery

### 1. Backup Helm Release

```bash
# Export helm values and manifests
helm get values ru-ecom-ops -n ru-ecom-ops > backup-values.yaml
helm get manifest ru-ecom-ops -n ru-ecom-ops > backup-manifests.yaml

# Backup Prometheus data
kubectl exec -it -n ru-ecom-ops \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot
```

### 2. Restore from Backup

```bash
# Restore Helm release
helm upgrade --install ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  -f backup-values.yaml

# Restore Prometheus data (if using volume snapshots)
# Follow cloud provider-specific procedures
```

### 3. Disaster Recovery Plan

1. **Data Loss**: Restore from PVC snapshots or backups
2. **Configuration Loss**: Redeploy from Helm chart version control
3. **Complete Cluster Loss**: Redeploy entire stack using Helm and stored configurations
4. **Service Degradation**: Scale up replicas or increase resources per instructions above

---

## Best Practices

1. **Version Control**: Store Helm charts and values in git
2. **Environment Parity**: Use values files to maintain consistency
3. **Monitoring**: Monitor Helm deployments and pod health
4. **Testing**: Use `helm lint` and `helm template` before deploying
5. **Rollback Strategy**: Always maintain previous release history
6. **Documentation**: Keep deployment documentation up-to-date
7. **Security**: Use secrets for sensitive data (webhook URLs, API keys)
8. **Resource Limits**: Define resource requests and limits appropriately
9. **High Availability**: Use multiple replicas and pod anti-affinity
10. **Backups**: Regular backups of Prometheus data and configurations

---

## References

- [Helm Documentation](https://helm.sh/docs/)
- [Helm Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Prometheus Helm Chart](https://github.com/prometheus-community/helm-charts)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/alertmanager/)
