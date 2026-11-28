# Team Training Guide — ru-ecom-ops CI/CD Pipeline

**Audience**: DevOps team members onboarding to the ru-ecom-ops deployment system  
**Prerequisite**: GitHub account with repo access; `gh` CLI installed and authenticated  
**Updated**: 2026-11-28

---

## 1. System Overview

The ru-ecom-ops CI/CD pipeline deploys the order-tracking and reconciliation system to three Kubernetes environments using a staged promotion model:

```
Developer pushes code
       │
       ▼
  develop branch ──► Development (automatic, ~5 min)
       │
       ▼
  release/* branch ──► Staging (manual approval required, ~10 min)
       │
       ▼
  v* tag ──────────► Production (security scan + backup + manual approval, ~15 min)
```

Each environment has its own:
- Kubernetes cluster with dedicated kubeconfig
- Prometheus + Alertmanager stack
- Slack notification channel
- PagerDuty routing key (staging and production only)

---

## 2. Repository Structure

```
ru-ecom-ops/
├── .github/workflows/        # GitHub Actions CI/CD pipelines
│   ├── deploy-dev.yml        # Dev: triggers on push to develop branch
│   ├── deploy-staging.yml    # Staging: triggers on push to release/* branches
│   ├── deploy-prod.yml       # Production: triggers on v* tags
│   └── helm-validate.yml     # On-demand: validate Helm chart only
├── helm/ru-ecom-ops/         # Helm chart
│   ├── Chart.yaml            # Chart version and metadata
│   ├── values.yaml           # Default values
│   ├── values-dev.yaml       # Dev environment overrides
│   ├── values-staging.yaml   # Staging environment overrides
│   ├── values-prod.yaml      # Production environment overrides
│   └── templates/            # Kubernetes resource templates
├── scripts/
│   ├── deploy-helm-chart.sh  # Main deployment script
│   ├── validate-helm-chart.sh# Helm validation script
│   └── verify-deployment.sh  # Post-deploy health check
├── k8s/                      # Base Kubernetes manifests
└── docs/                     # Documentation
```

---

## 3. GitHub Secrets Reference

All secrets are configured at the repository level. Never commit these values.

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `KUBECONFIG_DEV` | Base64-encoded dev cluster kubeconfig | deploy-dev.yml |
| `KUBECONFIG_STAGING` | Base64-encoded staging cluster kubeconfig | deploy-staging.yml |
| `KUBECONFIG_PROD` | Base64-encoded production cluster kubeconfig | deploy-prod.yml |
| `SLACK_WEBHOOK_DEV` | Slack webhook URL for #dev-deployments | deploy-dev.yml |
| `SLACK_WEBHOOK_STAGING` | Slack webhook URL for #staging-deployments | deploy-staging.yml |
| `SLACK_WEBHOOK_PROD` | Slack webhook URL for #prod-deployments | deploy-prod.yml |
| `PAGERDUTY_ROUTING_KEY_STAGING` | PagerDuty routing key for staging alerts | deploy-staging.yml |
| `PAGERDUTY_ROUTING_KEY_PROD` | PagerDuty routing key for production alerts | deploy-prod.yml |

### How to update a secret

```bash
# Update kubeconfig (from local kubeconfig file):
base64 -b 0 -i ~/.kube/config-dev > /tmp/kube-dev.b64   # macOS
base64 -w 0 ~/.kube/config-dev > /tmp/kube-dev.b64       # Linux
gh secret set KUBECONFIG_DEV < /tmp/kube-dev.b64

# Update a URL-type secret:
gh secret set SLACK_WEBHOOK_DEV --body "https://hooks.slack.com/services/..."
```

**Important**: Always use `-b 0` (macOS) or `-w 0` (Linux) when base64-encoding kubeconfigs to prevent line wrapping that can cause decode failures on CI runners.

---

## 4. GitHub Environments

Three environments are configured with deployment protection rules:

| Environment | Protection | Reviewer Required |
|-------------|------------|-------------------|
| `development` | None (auto) | No |
| `staging` | 5-min wait timer | No (but recommended) |
| `production` | Reviewer required | Yes |

Configure environment reviewers at:  
**Repository → Settings → Environments → production → Required reviewers**

---

## 5. Triggering Deployments

### Development Deployment (automatic)

Any push to the `develop` branch that changes `helm/**`, `docs/**`, or `.github/workflows/deploy-dev.yml` automatically triggers a development deployment.

```bash
git checkout develop
# Make changes to helm/ or scripts/
git add .
git commit -m "feat: your change"
git push origin develop
# Workflow triggers automatically, check status:
gh run list --workflow=deploy-dev.yml --limit=5
```

### Staging Deployment (requires approval)

```bash
# Create or update release branch
git checkout main
git checkout -b release/v1.2.0  # or git checkout release/v1.2.0
git push origin release/v1.2.0

# Check workflow is waiting for approval
gh run list --workflow=deploy-staging.yml --limit=5

# Approve the pending run
gh run review <RUN_ID> --approve --body "Approved for staging"
```

### Production Deployment (requires security scan + approval)

```bash
# Create and push a version tag
git checkout main
git tag -a v1.2.0 -m "Release v1.2.0: description of changes"
git push origin v1.2.0

# Monitor the security scan phase
gh run list --workflow=deploy-prod.yml --limit=5
gh run view <RUN_ID>

# After security scan and backup complete, approve
gh run review <RUN_ID> --approve --body "Approved for production"
```

---

## 6. Monitoring a Deployment

### Real-time workflow monitoring

```bash
# Watch a specific run
gh run watch <RUN_ID>

# View logs for a completed run
gh run view <RUN_ID> --log

# View only failed steps
gh run view <RUN_ID> --log-failed
```

### Kubernetes pod status (with cluster access)

```bash
# Set the right context
kubectl config use-context dev    # or staging, prod

# Watch pods
kubectl get pods -n ru-ecom-ops -w

# Check deployment rollout
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops
kubectl rollout status deployment/ru-ecom-ops-alertmanager -n ru-ecom-ops

# View recent pod logs
kubectl logs -n ru-ecom-ops -l app=prometheus --tail=50
```

---

## 7. Rollback Procedure

If a deployment causes issues, roll back using Helm:

```bash
# 1. Check release history
helm history ru-ecom-ops -n ru-ecom-ops

# 2. Roll back to the previous release
helm rollback ru-ecom-ops -n ru-ecom-ops

# 3. Verify rollback
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops
kubectl get pods -n ru-ecom-ops

# 4. Confirm pods are running the previous image
kubectl describe pod <POD_NAME> -n ru-ecom-ops | grep -A 2 "Image:"
```

**Expected rollback time**: < 2 minutes

---

## 8. Troubleshooting Common Issues

### "Helm lint failed"

Run validation locally to see the full error:
```bash
./scripts/validate-helm-chart.sh
```

If `helm` isn't installed:
```bash
brew install helm  # macOS
# or
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash  # Linux
```

### "illegal base64 data" in kubeconfig

The kubeconfig secret has encoding issues. Re-encode it:
```bash
# macOS: use -b 0 to disable line wrapping
base64 -b 0 -i ~/.kube/config-prod > /tmp/kube-prod.b64
gh secret set KUBECONFIG_PROD < /tmp/kube-prod.b64
```

Also verify the kubeconfig cert fields have valid base64 padding:
```python
import yaml, base64
kc = yaml.safe_load(open('/path/to/kubeconfig').read())
for user in kc['users']:
    cert = user['user'].get('client-certificate-data', '')
    try:
        base64.b64decode(cert, validate=True)
        print("cert: OK")
    except Exception as e:
        print(f"cert: FAIL - {e}")
```

### "Unable to connect to the server"

The cluster is unreachable. Verify:
```bash
kubectl cluster-info   # shows API server URL
ping <cluster-hostname>
# Check VPN if cluster is private
```

### Slack notifications not arriving

Check the webhook secret is set:
```bash
gh secret list | grep SLACK
```

If the secret is empty, the curl command silently fails (no URL). Set it:
```bash
gh secret set SLACK_WEBHOOK_DEV --body "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

Add a guard in the workflow to catch this earlier:
```yaml
- name: Notify
  if: env.SLACK_WEBHOOK != ''
  env:
    SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK_DEV }}
  run: curl -X POST "$SLACK_WEBHOOK" ...
```

### Staging approval gate not appearing

The environment may not have the approval requirement configured. Check:
1. GitHub → Repository → Settings → Environments → staging
2. Enable "Required reviewers" and add your team

### Production security scan fails (Trivy findings)

Review the Trivy report in the workflow logs. For test/validation environments, the security check is expected to report findings since this is a mock setup. For production:
1. Address CRITICAL/HIGH severity findings before deploying
2. For false positives, add exceptions in `.trivyignore`

---

## 9. Helm Template Gotchas

These issues were discovered during Phase 9 validation and are documented here for future reference:

### Embedded template engines (Prometheus/Alertmanager)

When embedding Prometheus or Alertmanager templates inside Helm ConfigMaps, escape the inner `{{ }}` expressions:

```yaml
# WRONG - Helm tries to evaluate $labels:
summary: 'Pod {{ $labels.pod }} is crashing'

# CORRECT - Helm passes through as literal text:
summary: 'Pod {{ "{{" }} $labels.pod {{ "}}" }} is crashing'
```

### Slice index access

Go templates do not support bracket notation for slice indexing:

```yaml
# WRONG:
group_wait: {{ .Values.routes[0].groupWait }}

# CORRECT:
group_wait: {{ (index .Values.routes 0).groupWait }}
```

### Sprig vs Go standard library functions

Helm uses the Sprig template library. Standard Go functions like `toUpper` are not available:

| Go standard | Helm/Sprig equivalent |
|-------------|----------------------|
| `strings.ToUpper` / `toUpper` | `upper` |
| `strings.ToLower` / `toLower` | `lower` |
| `strings.TrimSpace` / `trimSpace` | `trim` |
| `strconv.Itoa` / `toString` | `toString` |

Full Sprig reference: http://masterminds.github.io/sprig/

---

## 10. Workflow Diagram

```
Push to develop
    │
    ▼
deploy-dev.yml
    ├── Configure kubeconfig
    ├── Validate Helm chart (helm lint)
    ├── Create Kubernetes secrets
    ├── Deploy with Helm (helm upgrade --install)
    ├── Verify deployment (kubectl rollout status)
    └── Notify Slack (#dev-deployments)

Push to release/*
    │
    ▼
deploy-staging.yml
    ├── Prepare (get version)
    ├── WAIT FOR APPROVAL ◄── Team approves here
    ├── Configure kubeconfig
    ├── Pre-deployment dry run
    ├── Deploy with Helm
    ├── Health checks (5-min timeout)
    ├── Create deployment records artifact
    └── Notify (Slack + PagerDuty)

Push v* tag
    │
    ▼
deploy-prod.yml
    ├── Prepare (get version)
    ├── Security checks (Trivy scan + secrets detection)
    ├── Create backup (kubeconfig dump to artifact)
    ├── WAIT FOR APPROVAL ◄── Team approves here
    ├── Configure kubeconfig
    ├── Pre-deployment dry run
    ├── Deploy with Helm
    ├── Extended health checks (5-min timeout)
    ├── Smoke tests (curl health endpoints)
    ├── Create deployment records artifact
    └── Notify (Slack + PagerDuty)
```

---

## 11. Quick Reference Commands

```bash
# List recent workflow runs
gh run list --limit=10

# Watch a running workflow
gh run watch <RUN_ID>

# Approve a waiting deployment
gh run review <RUN_ID> --approve

# Cancel a running workflow
gh run cancel <RUN_ID>

# Re-run a failed workflow
gh run rerun <RUN_ID>

# View workflow run logs
gh run view <RUN_ID> --log

# List GitHub secrets (names only)
gh secret list

# Check GitHub environments
gh api repos/yolandazhong13/ru-ecom-ops/environments --jq '.environments[].name'

# Validate Helm chart locally
./scripts/validate-helm-chart.sh

# Check deployment status (requires cluster access)
kubectl get all -n ru-ecom-ops

# Roll back last deployment
helm rollback ru-ecom-ops -n ru-ecom-ops
```

---

## 12. Contact and Escalation

| Issue | Contact |
|-------|---------|
| CI/CD pipeline issues | DevOps team (this guide) |
| Kubernetes cluster access | Infrastructure team |
| PagerDuty alert configuration | On-call team |
| Slack webhook URLs | Workspace admin |
| GitHub repository permissions | Repository admin (yolandazhong13) |
