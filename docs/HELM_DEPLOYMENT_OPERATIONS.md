# Helm Deployment Operations Guide

## Overview

This guide provides operational procedures for deploying and managing the ru-ecom-ops monitoring stack using Helm across development, staging, and production environments.

---

## Quick Reference

| Task | Command |
|------|---------|
| Validate Chart | `./scripts/validate-helm-chart.sh` |
| Deploy to Dev | `./scripts/deploy-helm-chart.sh dev` |
| Deploy to Staging | `./scripts/deploy-helm-chart.sh staging` |
| Deploy to Production | `./scripts/deploy-helm-chart.sh prod` |
| Dry-run Production | `./scripts/deploy-helm-chart.sh prod dry-run` |
| Verify Deployment | `./scripts/verify-deployment.sh ru-ecom-ops` |

---

## Prerequisites

### Required Tools

1. **Helm v3.0+**
   ```bash
   brew install helm  # macOS
   # or visit https://helm.sh/docs/intro/install/
   ```

2. **kubectl v1.19+**
   ```bash
   brew install kubernetes-cli  # macOS
   # or visit https://kubernetes.io/docs/tasks/tools/
   ```

3. **Kubeconfig** - Properly configured with access to target Kubernetes clusters

### Required Kubernetes Resources

1. **Namespace** - `ru-ecom-ops` (will be created if it doesn't exist)
2. **StorageClass** - `standard` (must exist in the cluster)
3. **Secrets** - For Slack and PagerDuty integrations

---

## Deployment Workflow

### Step 1: Validate Chart Configuration

Before deploying, validate the Helm chart structure and templates:

```bash
./scripts/validate-helm-chart.sh
```

This script:
- Checks Helm installation
- Validates chart structure
- Runs `helm lint`
- Validates all three environments (dev, staging, prod)
- Generates manifests in the `manifests/` directory

### Step 2: Create Required Secrets

#### Slack Integration Secret

```bash
kubectl create secret generic alertmanager-secrets \
  --from-literal=slack-webhook-url='https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK/URL' \
  -n ru-ecom-ops
```

#### PagerDuty Integration Secret (Staging & Production)

```bash
kubectl create secret generic alertmanager-pagerduty \
  --from-literal=pagerduty-routing-key='YOUR_PAGERDUTY_ROUTING_KEY' \
  -n ru-ecom-ops
```

**Note:** Development environment does not require PagerDuty secret.

### Step 3: Deploy to Target Environment

#### Deploy to Development

```bash
./scripts/deploy-helm-chart.sh dev
```

**Characteristics:**
- 1 replica for each component
- 7-day retention, 10Gi storage
- Relaxed alert thresholds
- PagerDuty disabled
- Slack-only notifications

#### Deploy to Staging

```bash
./scripts/deploy-helm-chart.sh staging
```

**Characteristics:**
- 2 replicas for each component
- 14-day retention, 25Gi storage
- Intermediate alert thresholds
- PagerDuty enabled
- Moderate resource allocation

#### Deploy to Production (with dry-run first)

```bash
# Dry-run to preview changes
./scripts/deploy-helm-chart.sh prod dry-run

# Actual deployment
./scripts/deploy-helm-chart.sh prod
```

**Characteristics:**
- 3 replicas for each component (full HA)
- 30-day retention, 50Gi storage
- Strict alert thresholds
- PagerDuty enabled
- Maximum resource allocation
- Required pod anti-affinity

### Step 4: Verify Deployment

After deployment, verify the stack is healthy:

```bash
./scripts/verify-deployment.sh ru-ecom-ops
```

This script checks:
- Namespace and Helm release status
- Pod readiness and health
- Service endpoints
- PersistentVolumeClaim status
- Secrets configuration
- Resource usage
- Recent logs

---

## Common Operations

### Access Prometheus UI

```bash
kubectl port-forward -n ru-ecom-ops svc/ru-ecom-ops-prometheus 9090:9090
# Then open: http://localhost:9090
```

**Useful dashboards:**
- Status → Targets: View scrape targets and their status
- Status → Configuration: View Prometheus configuration
- Alerts: View active alerts and their state

### Access Alertmanager UI

```bash
kubectl port-forward -n ru-ecom-ops svc/ru-ecom-ops-alertmanager 9093:9093
# Then open: http://localhost:9093
```

**Useful features:**
- Status: View alertmanager configuration and clustering status
- Alerts: View grouped alerts
- Silences: Create manual alert silences

### View Pod Logs

```bash
# Prometheus logs
kubectl logs -n ru-ecom-ops -l app=prometheus --tail=50

# Alertmanager logs
kubectl logs -n ru-ecom-ops -l app=alertmanager --tail=50

# Stream logs in real-time
kubectl logs -n ru-ecom-ops -l app=prometheus -f
```

### Check Pod Status

```bash
# Get all pods
kubectl get pods -n ru-ecom-ops

# Watch pod changes
kubectl get pods -n ru-ecom-ops -w

# Detailed pod information
kubectl describe pod -n ru-ecom-ops -l app=prometheus
```

### Scale Replicas

```bash
# Scale Prometheus replicas
kubectl scale deployment -n ru-ecom-ops \
  --replicas=5 \
  ru-ecom-ops-prometheus

# Scale Alertmanager replicas
kubectl scale deployment -n ru-ecom-ops \
  --replicas=5 \
  ru-ecom-ops-alertmanager
```

### Check Storage Usage

```bash
# Check PVC status
kubectl get pvc -n ru-ecom-ops

# Check pod disk usage
kubectl exec -n ru-ecom-ops \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- df -h /prometheus
```

### Update Configuration Values

```bash
# Upgrade release with new values
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  -f ./helm/ru-ecom-ops/values-prod.yaml

# Upgrade specific values
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  --set prometheus.replicaCount=4 \
  --set alertmanager.resources.limits.memory=2Gi
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod -n ru-ecom-ops -l app=prometheus

# Check resource availability
kubectl top nodes
kubectl top pods -n ru-ecom-ops

# Check logs
kubectl logs -n ru-ecom-ops -l app=prometheus --previous
```

**Common causes:**
- Insufficient CPU/memory resources
- Storage not available (PVC not bound)
- Image pull errors
- Security policies blocking pod creation

### PersistentVolume Not Binding

```bash
# Check PVC status
kubectl describe pvc -n ru-ecom-ops ru-ecom-ops-prometheus-storage

# Check storage class
kubectl get storageclass

# Check PV availability
kubectl get pv
```

**Solutions:**
- Verify StorageClass exists and is available
- Check cluster storage capacity
- Ensure accessMode is compatible with storage backend

### Network Connectivity Issues

```bash
# Test DNS resolution
kubectl exec -n ru-ecom-ops \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- nslookup ru-ecom-ops-alertmanager

# Test service connectivity
kubectl exec -n ru-ecom-ops \
  $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
  -- curl -v http://ru-ecom-ops-alertmanager:9093/-/ready
```

### Alerts Not Routing to Slack/PagerDuty

```bash
# Verify secrets exist
kubectl get secrets -n ru-ecom-ops

# Check secret values (decoded)
kubectl get secret alertmanager-secrets -n ru-ecom-ops -o jsonpath='{.data.slack-webhook-url}' | base64 -d

# Check alertmanager configuration
kubectl exec -n ru-ecom-ops \
  $(kubectl get pod -n ru-ecom-ops -l app=alertmanager -o jsonpath='{.items[0].metadata.name}') \
  -- cat /etc/alertmanager/alertmanager.yml

# Check alertmanager logs for errors
kubectl logs -n ru-ecom-ops -l app=alertmanager | grep -i "slack\|pagerduty\|error"
```

---

## Maintenance Tasks

### Backup Helm Release

```bash
# Export current values
helm get values ru-ecom-ops -n ru-ecom-ops > backup-values-prod.yaml

# Export manifests
helm get manifest ru-ecom-ops -n ru-ecom-ops > backup-manifests-prod.yaml
```

### Update Helm Chart Version

```bash
# Check current version
helm list -n ru-ecom-ops

# Upgrade to latest chart
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  -f ./helm/ru-ecom-ops/values-prod.yaml
```

### Rollback Deployment

```bash
# View deployment history
helm history ru-ecom-ops -n ru-ecom-ops

# Rollback to previous release
helm rollback ru-ecom-ops 1 -n ru-ecom-ops

# Rollback to specific revision
helm rollback ru-ecom-ops 2 -n ru-ecom-ops
```

### Clean Up Old Releases

```bash
# List all releases
helm list -n ru-ecom-ops -a

# Delete old release
helm delete ru-ecom-ops-old -n ru-ecom-ops
```

---

## High Availability Deployment

### Production Configuration

The production environment is configured for high availability:

| Component | Replicas | Anti-Affinity | Storage |
|-----------|----------|---------------|---------|
| Prometheus | 3 | Required | 50Gi (30-day) |
| Alertmanager | 3 | Required | 10Gi |

**Key features:**
- Required pod anti-affinity ensures pods spread across different nodes
- 15-second scrape intervals for high-resolution metrics
- 1% error rate threshold (strict monitoring)
- All critical alerts route to PagerDuty

### Scaling the Stack

To increase production capacity:

```bash
# Scale Prometheus to 5 replicas
helm upgrade ru-ecom-ops ./helm/ru-ecom-ops \
  -n ru-ecom-ops \
  -f ./helm/ru-ecom-ops/values-prod.yaml \
  --set prometheus.replicaCount=5 \
  --set prometheus.persistence.size=100Gi

# Monitor the upgrade
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops
```

---

## Environment Comparison

### Alert Thresholds by Environment

| Alert | Dev | Staging | Prod |
|-------|-----|---------|------|
| Error Rate | 10% | 5% | 1% |
| Latency | 1000ms | 500ms | 100ms |
| Memory Usage | 90% | 80% | 85% |
| CPU Throttling | 50% | 30% | 10% |

### Resource Allocation

| Environment | Prometheus (CPU/Memory) | Alertmanager (CPU/Memory) |
|-------------|------------------------|--------------------------|
| Dev | 100m/128Mi - 500m/512Mi | 50m/64Mi - 200m/256Mi |
| Staging | 250m/256Mi - 1000m/1Gi | 100m/128Mi - 500m/512Mi |
| Prod | 500m/512Mi - 2000m/2Gi | 200m/256Mi - 1000m/1Gi |

### Retention Policy

| Environment | Retention | Storage | Scrape Interval |
|-------------|-----------|---------|-----------------|
| Dev | 7 days | 10Gi | 30s |
| Staging | 14 days | 25Gi | 30s |
| Prod | 30 days | 50Gi | 15s |

---

## Best Practices

1. **Always validate before deploying**
   - Run `validate-helm-chart.sh` before each deployment
   - Use `--dry-run` for production changes

2. **Test in staging first**
   - Deploy changes to staging environment first
   - Verify alerts trigger correctly
   - Monitor for 24-48 hours before production

3. **Maintain secrets securely**
   - Use encrypted secret stores (e.g., HashiCorp Vault, AWS Secrets Manager)
   - Rotate secrets regularly
   - Never commit secrets to version control

4. **Monitor deployments**
   - Run `verify-deployment.sh` after each deployment
   - Check pod logs for errors
   - Verify alert routing is working

5. **Document changes**
   - Keep deployment notes with dates and changes
   - Document manual interventions
   - Update runbooks when procedures change

6. **Backup regularly**
   - Export Helm release configurations
   - Backup Prometheus data before major upgrades
   - Store backups in multiple locations

7. **Plan for disasters**
   - Test rollback procedures regularly
   - Maintain detailed runbooks
   - Document recovery procedures

---

## Support & Resources

- **Helm Documentation**: https://helm.sh/docs/
- **Prometheus Documentation**: https://prometheus.io/docs/
- **Alertmanager Documentation**: https://prometheus.io/docs/alerting/alertmanager/
- **Kubernetes Documentation**: https://kubernetes.io/docs/

---

## Deployment Checklist

- [ ] Helm and kubectl installed and configured
- [ ] Kubeconfig points to correct cluster
- [ ] Chart structure validated (`validate-helm-chart.sh`)
- [ ] Required secrets created in target namespace
- [ ] Dry-run performed for production deployments
- [ ] StorageClass verified as available
- [ ] Resource limits documented and approved
- [ ] Deployment executed (`deploy-helm-chart.sh`)
- [ ] Deployment verified (`verify-deployment.sh`)
- [ ] Pods healthy and running
- [ ] Alerting channels (Slack/PagerDuty) tested
- [ ] Service endpoints accessible
- [ ] Prometheus targets scraping correctly
- [ ] Deployment documented with timestamp and changes
