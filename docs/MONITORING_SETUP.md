# Kubernetes Monitoring Setup Guide
## Prometheus + Alertmanager for ru-ecom-ops

## Overview

This guide covers setting up comprehensive monitoring and alerting for the ru-ecom-ops application using:
- **Prometheus**: Metrics collection and time-series storage
- **Alertmanager**: Alert routing, grouping, and notification delivery
- **Custom Recording Rules**: Pre-computed metrics for dashboard efficiency
- **Alerting Rules**: Threshold-based alerts for operational issues

---

## Prerequisites

1. **Kubernetes cluster** with:
   - kubectl configured and authenticated
   - Storage provisioning available (StorageClass: `standard`)
   - Internet access for pulling images from Docker Hub

2. **Namespace**: `ru-ecom-ops` (created by CI/CD pipeline)

3. **For Slack Notifications**:
   - Slack workspace with admin access
   - Channel(s) for alerts (#alerts, #critical-alerts, #monitoring)
   - Slack App with Incoming Webhooks enabled

---

## Installation Steps

### Step 1: Create Slack Webhook Secret (if using Slack notifications)

```bash
# Create secret with Slack webhook URL
kubectl create secret generic alertmanager-secrets \
  --from-literal=slack-webhook-url='https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK/URL' \
  -n ru-ecom-ops

# Verify secret created
kubectl get secrets -n ru-ecom-ops | grep alertmanager
```

### Step 2: Deploy Prometheus

```bash
# Apply Prometheus configuration and deployment
kubectl apply -f k8s/monitoring/prometheus-config.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

# Verify Prometheus is running
kubectl get pods -n ru-ecom-ops -l app=prometheus
kubectl get svc -n ru-ecom-ops | grep prometheus
kubectl get pvc -n ru-ecom-ops | grep prometheus
```

**Health Check:**
```bash
# Port forward to access Prometheus UI
kubectl port-forward -n ru-ecom-ops svc/prometheus 9090:9090

# Open browser to http://localhost:9090
# Check Status → Targets to see if targets are being scraped
```

### Step 3: Deploy Alertmanager

```bash
# Apply Alertmanager configuration and deployment
kubectl apply -f k8s/monitoring/alertmanager-deployment.yaml

# Verify Alertmanager is running
kubectl get pods -n ru-ecom-ops -l app=alertmanager
kubectl get svc -n ru-ecom-ops | grep alertmanager
kubectl get pvc -n ru-ecom-ops | grep alertmanager
```

**Health Check:**
```bash
# Port forward to access Alertmanager UI
kubectl port-forward -n ru-ecom-ops svc/alertmanager 9093:9093

# Open browser to http://localhost:9093
# Check Status to verify configuration is loaded
```

### Step 4: Verify Prometheus is Scraping Metrics

```bash
# Check Prometheus targets
kubectl port-forward -n ru-ecom-ops svc/prometheus 9090:9090

# Navigate to http://localhost:9090/targets
# Verify endpoints show "UP" status:
#   - kubernetes-apiservers
#   - kubernetes-nodes
#   - kubernetes-pods
#   - ru-ecom-ops
#   - kube-state-metrics (if installed)
#   - node-exporter (if installed)
```

---

## Configuration

### Environment-Specific Alerting

Modify alert thresholds in `k8s/monitoring/prometheus-config.yaml` based on environment:

**Development/Staging**: Relaxed thresholds
```yaml
- alert: HighErrorRate
  expr: '(rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) > 0.10'
  for: 10m
```

**Production**: Strict thresholds
```yaml
- alert: HighErrorRate
  expr: '(rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])) > 0.05'
  for: 5m
```

### Adding Custom Metrics

1. **Update application to expose Prometheus metrics:**
   ```python
   # In your Python/Node.js application
   from prometheus_client import Counter, Histogram, Gauge
   
   request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
   request_latency = Histogram('http_request_duration_seconds', 'Request latency', buckets=[0.01, 0.05, 0.1, 0.5, 1])
   active_orders = Gauge('orders_active', 'Currently processing orders')
   ```

2. **Ensure application is annotated for scraping:**
   ```yaml
   # In deployment.yaml
   metadata:
     annotations:
       prometheus.io/scrape: 'true'
       prometheus.io/port: '9090'  # Metrics port
       prometheus.io/path: '/metrics'
   ```

3. **Add scrape config to prometheus-config.yaml** (if needed for custom endpoints)

### Customizing Alert Routes

Edit `k8s/monitoring/alertmanager-deployment.yaml` to add custom routing:

```yaml
routes:
  # Route database alerts to database team
  - match:
      component: database
    receiver: 'database-team'
  
  # Route storage alerts to ops team
  - match:
      component: storage
    receiver: 'ops-team'
```

### Adding Additional Receivers (Email, PagerDuty)

**Email Notifications:**
```yaml
receivers:
- name: 'default'
  email_configs:
  - to: 'alerts@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'your-email@gmail.com'
    auth_password: '${GMAIL_APP_PASSWORD}'
    headers:
      Subject: '{{ .GroupLabels.alertname }}'
```

**PagerDuty Integration:**
```yaml
receivers:
- name: 'critical'
  pagerduty_configs:
  - routing_key: '${PAGERDUTY_ROUTING_KEY}'
    description: '{{ .GroupLabels.alertname }}'
```

---

## Monitoring Dashboards

### Prometheus Built-in Dashboards

Access at `http://localhost:9090/graph`:

1. **Recording Rules**: Shows pre-computed metrics
   ```
   app:request_rate:5m
   app:error_rate:5m
   app:request_latency:p99:5m
   app:memory_usage_ratio:5m
   ```

2. **Alert Status**: Check firing/resolved alerts
   ```
   ALERTS{alertstate="firing"}
   ```

### Grafana Integration (Optional)

To visualize metrics with Grafana:

```bash
# Add Prometheus as data source in Grafana
# URL: http://prometheus:9090

# Create dashboard panels:
# - Request Rate: query 'app:request_rate:5m'
# - Error Rate: query 'app:error_rate:5m'
# - Latency (P99): query 'app:request_latency:p99:5m'
# - Memory Usage: query 'app:memory_usage_ratio:5m'
```

---

## Logging and Debugging

### Check Prometheus Logs

```bash
# View Prometheus pod logs
kubectl logs -f -n ru-ecom-ops deployment/prometheus --all-containers=true

# Check for scrape errors
kubectl port-forward -n ru-ecom-ops svc/prometheus 9090:9090
# Navigate to Status → Targets to see detailed error messages
```

### Check Alertmanager Logs

```bash
# View Alertmanager pod logs
kubectl logs -f -n ru-ecom-ops deployment/alertmanager --all-containers=true

# Check alert delivery status
kubectl port-forward -n ru-ecom-ops svc/alertmanager 9093:9093
# Navigate to http://localhost:9093 to view recent alerts and delivery status
```

### Manual Alert Test

```bash
# Trigger test alert via Alertmanager API
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {"alertname":"TestAlert","severity":"warning"},
    "annotations": {"description":"This is a test alert"}
  }]'
```

---

## Maintenance

### Storage Management

Prometheus and Alertmanager use PersistentVolumeClaims:
- **Prometheus**: 50Gi (configurable via `prometheus-deployment.yaml`)
- **Alertmanager**: 10Gi (configurable via `alertmanager-deployment.yaml`)

**Monitor storage usage:**
```bash
# Check PVC usage
kubectl exec -it -n ru-ecom-ops prometheus-0 -- df -h /prometheus

# Increase storage if needed:
kubectl patch pvc prometheus-storage -n ru-ecom-ops \
  -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

**Configure retention policy in prometheus-deployment.yaml:**
```yaml
args:
  - '--storage.tsdb.retention.time=30d'  # Keep metrics for 30 days
  - '--storage.tsdb.retention.size=50GB' # Or limit by size
```

### Backup and Recovery

**Backup Prometheus data:**
```bash
# Create snapshot
kubectl exec -it -n ru-ecom-ops prometheus-0 -- \
  wget -O- http://localhost:9090/api/v1/admin/tsdb/snapshot

# Or use volume snapshots (cloud provider dependent)
```

**Backup Alertmanager state:**
```bash
# Alert history is stored in /alertmanager
kubectl exec -it -n ru-ecom-ops alertmanager-0 -- \
  tar czf - /alertmanager | tar xzf - -C /backup/
```

### Scaling

**Increase replicas for high availability:**
```bash
kubectl scale deployment prometheus -n ru-ecom-ops --replicas=3
kubectl scale deployment alertmanager -n ru-ecom-ops --replicas=3
```

---

## Troubleshooting

### Prometheus targets showing "DOWN"

**Symptoms:**
- Status → Targets shows targets in "DOWN" state
- No metrics are being collected

**Solutions:**
```bash
# 1. Check if target pods are running
kubectl get pods -n ru-ecom-ops -l app=ru-ecom-ops

# 2. Verify metrics endpoint is accessible
kubectl port-forward -n ru-ecom-ops svc/ru-ecom-ops-app 5000:5000
curl http://localhost:5000/metrics

# 3. Check pod annotations
kubectl get pod -n ru-ecom-ops -o jsonpath='{.items[0].metadata.annotations}'

# 4. Check firewall/network policies
kubectl get networkpolicies -n ru-ecom-ops
```

### Alerts not firing

**Symptoms:**
- Alert rules exist but alerts never trigger
- Expected alerts not showing in Alertmanager

**Solutions:**
```bash
# 1. Check if alert rules are loaded
kubectl port-forward -n ru-ecom-ops svc/prometheus 9090:9090
# Navigate to Status → Rules and verify alert rules are listed

# 2. Verify query expressions return data
# In Prometheus UI, run: 'up{job="ru-ecom-ops"}' - should return 1 or 0

# 3. Check Prometheus logs for errors
kubectl logs -n ru-ecom-ops deployment/prometheus | grep -i error

# 4. Verify Alertmanager is receiving alerts
kubectl logs -n ru-ecom-ops deployment/alertmanager | grep -i received
```

### Slack notifications not arriving

**Symptoms:**
- Alertmanager UI shows alerts
- No messages in Slack channels

**Solutions:**
```bash
# 1. Verify Slack webhook secret is set
kubectl get secret -n ru-ecom-ops alertmanager-secrets -o yaml

# 2. Check Alertmanager logs for webhook errors
kubectl logs -n ru-ecom-ops deployment/alertmanager | grep -i webhook

# 3. Test webhook manually
SECRET=$(kubectl get secret -n ru-ecom-ops alertmanager-secrets -o jsonpath='{.data.slack-webhook-url}' | base64 -d)
curl -X POST "$SECRET" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message from Prometheus"}'

# 4. Verify Slack channel allows webhook posts
# Check Slack app permissions and channel settings
```

### High memory/CPU usage

**Symptoms:**
- Prometheus pod constantly restarting
- High resource usage visible in metrics

**Solutions:**
```bash
# 1. Check if metrics cardinality is too high
# In Prometheus UI: 'count(count by(__name__) ({job="ru-ecom-ops"}))'
# If > 100,000, reduce cardinality by:
#   - Adding metric_relabel_configs to drop unnecessary metrics
#   - Reducing scrape interval if appropriate

# 2. Increase resource limits
kubectl patch deployment prometheus -n ru-ecom-ops --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value":"4Gi"}]'

# 3. Reduce retention period
# Edit prometheus-deployment.yaml and reduce '--storage.tsdb.retention.time=30d' to '7d'
```

---

## Integration with CI/CD

Add health checks to deployment pipeline (`deploy.yml`):

```yaml
- name: Verify monitoring setup
  run: |
    # Wait for Prometheus to be ready
    kubectl wait --for=condition=ready pod \
      -l app=prometheus \
      -n ru-ecom-ops \
      --timeout=300s
    
    # Wait for Alertmanager to be ready
    kubectl wait --for=condition=ready pod \
      -l app=alertmanager \
      -n ru-ecom-ops \
      --timeout=300s
    
    # Verify targets are being scraped
    TARGETS=$(kubectl exec -n ru-ecom-ops \
      $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
      -- curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length')
    
    if [ "$TARGETS" -lt 5 ]; then
      echo "Warning: Only $TARGETS targets are active"
      exit 1
    fi
```

---

## Next Steps

1. **Deploy Grafana** for advanced dashboarding and visualization
2. **Set up Loki** for centralized log aggregation
3. **Configure persistent alerts** with long-term storage
4. **Integrate with incident management** (PagerDuty, Opsgenie)
5. **Implement SLO tracking** using Prometheus metrics
