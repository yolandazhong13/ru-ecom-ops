# GitHub Actions Setup Verification Guide

This guide provides a step-by-step checklist and verification procedures to ensure your GitHub Actions CI/CD pipeline is properly configured before your first deployment.

---

## Pre-Flight Checklist

### 1. Repository Requirements

- [ ] Repository is on GitHub
- [ ] `.github/workflows/` directory exists with workflow files:
  - [ ] `helm-validate.yml`
  - [ ] `deploy-dev.yml`
  - [ ] `deploy-staging.yml`
  - [ ] `deploy-prod.yml`
- [ ] `scripts/` directory exists with deployment scripts:
  - [ ] `validate-helm-chart.sh`
  - [ ] `deploy-helm-chart.sh`
  - [ ] `verify-deployment.sh`
- [ ] `helm/ru-ecom-ops/` chart directory exists with:
  - [ ] `Chart.yaml`
  - [ ] `values.yaml`
  - [ ] `values-dev.yaml`
  - [ ] `values-staging.yaml`
  - [ ] `values-prod.yaml`
  - [ ] `templates/` directory with Kubernetes manifests

### 2. Kubernetes Cluster Requirements

For each environment (dev, staging, prod):

- [ ] Kubernetes cluster is accessible
- [ ] kubectl can connect to cluster: `kubectl cluster-info`
- [ ] Current user has cluster-admin or appropriate permissions
- [ ] Kubernetes version is 1.24+: `kubectl version --short`

### 3. External Service Requirements

- [ ] Slack workspace has webhook URLs created for notifications
- [ ] PagerDuty account has routing keys (staging & prod)
- [ ] All kubeconfig files are available locally

---

## Secret Creation and Verification

### Create GitHub Secrets

**Navigate to**: Repository Settings → Secrets and variables → Actions

#### 1. Base64-Encode Kubeconfig Files

For each environment, encode the kubeconfig:

```bash
# Development
cat ~/.kube/config-dev | base64 -w0 | pbcopy
# Paste as KUBECONFIG_DEV secret

# Staging
cat ~/.kube/config-staging | base64 -w0 | pbcopy
# Paste as KUBECONFIG_STAGING secret

# Production
cat ~/.kube/config-prod | base64 -w0 | pbcopy
# Paste as KUBECONFIG_PROD secret
```

**Verify encoding** (should not contain spaces or newlines):
```bash
# After pasting into secret, verify length is correct
# Original size × 4/3 ≈ encoded size
wc -c ~/.kube/config-dev
# If original is ~5KB, encoded should be ~6.7KB
```

#### 2. Add Slack Webhooks

For each environment:

```bash
# In Slack: Create Incoming Webhook
# Channel: #deployments (or your preference)
# Copy webhook URL

# Add to GitHub:
SLACK_WEBHOOK_DEV=https://hooks.slack.com/services/T.../B.../X...
SLACK_WEBHOOK_STAGING=https://hooks.slack.com/services/T.../B.../X...
SLACK_WEBHOOK_PROD=https://hooks.slack.com/services/T.../B.../X...
```

**Verify webhook** (test with curl):
```bash
curl -X POST $SLACK_WEBHOOK_DEV \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "✅ Slack webhook test successful",
    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "GitHub Actions webhook configured correctly"}}]
  }'
```

#### 3. Add PagerDuty Routing Keys

For staging and production:

```bash
# In PagerDuty: Services → Integration Keys → Copy Routing Key

PAGERDUTY_ROUTING_KEY_STAGING=your-routing-key
PAGERDUTY_ROUTING_KEY_PROD=your-routing-key
```

### Secret Verification Script

Create `.github/scripts/verify-secrets.sh`:

```bash
#!/bin/bash
set -e

echo "🔍 Verifying GitHub Secrets Configuration..."
echo ""

SECRETS_REQUIRED=(
  "KUBECONFIG_DEV"
  "KUBECONFIG_STAGING"
  "KUBECONFIG_PROD"
  "SLACK_WEBHOOK_DEV"
  "SLACK_WEBHOOK_STAGING"
  "SLACK_WEBHOOK_PROD"
  "PAGERDUTY_ROUTING_KEY_STAGING"
  "PAGERDUTY_ROUTING_KEY_PROD"
)

# Note: This script must be run with GitHub CLI authenticated
# gh auth login

MISSING_SECRETS=()

for secret in "${SECRETS_REQUIRED[@]}"; do
  if gh secret list --repo $GITHUB_REPOSITORY | grep -q "^$secret"; then
    echo "✓ Secret exists: $secret"
  else
    echo "✗ Secret missing: $secret"
    MISSING_SECRETS+=("$secret")
  fi
done

echo ""
if [ ${#MISSING_SECRETS[@]} -eq 0 ]; then
  echo "✅ All required secrets are configured!"
  exit 0
else
  echo "❌ Missing secrets:"
  printf '  - %s\n' "${MISSING_SECRETS[@]}"
  exit 1
fi
```

---

## GitHub Environments Configuration

### Create Environments with Protection Rules

**Navigate to**: Repository Settings → Environments

#### Development Environment

- **Name**: `development`
- **Deployment branches**: `develop`
- **Approval requirements**: None (auto-deploy)
- **Restricted variables**: None required

```bash
# GitHub CLI alternative
gh repo set-default <owner>/<repo>
gh api repos/{owner}/{repo}/environments \
  -f name=development \
  -f deployment_branch_policy='{"protected_branches": false, "custom_deployment_branches": true}' \
  -a custom_deployment_branches='["develop"]'
```

#### Staging Environment

- **Name**: `staging`
- **Deployment branches**: `release/**` (or custom)
- **Approval requirements**: 
  - [ ] Require deployment reviews
  - [ ] Require deployments to succeed before moving to next environment (optional)
- **Reviewers**: Team leads or designated approvers
- **Restrict variables**: None required (inherits repo secrets)

#### Production Environment

- **Name**: `production`
- **Deployment branches**: Custom (protect tags only if possible)
- **Approval requirements**:
  - [ ] Require deployment reviews (at least 1-2 reviewers)
  - [ ] Require deployments to succeed before moving to next environment (optional)
- **Reviewers**: Team leads, architects, or designated approvers
- **Restrict variables**: Consider creating environment-specific overrides

### Environment-Specific Variables (Optional)

Create additional variables in each environment for environment-specific settings:

**Development**:
```
HELM_RELEASE_NAME=ru-ecom-ops
HELM_NAMESPACE=ru-ecom-ops
TIMEOUT_SECONDS=300
```

**Staging**:
```
HELM_RELEASE_NAME=ru-ecom-ops
HELM_NAMESPACE=ru-ecom-ops
TIMEOUT_SECONDS=300
```

**Production**:
```
HELM_RELEASE_NAME=ru-ecom-ops
HELM_NAMESPACE=ru-ecom-ops
TIMEOUT_SECONDS=600
```

---

## Helm Chart Verification

### Validate Chart Structure

```bash
# Run validation script locally
./scripts/validate-helm-chart.sh
```

Expected output:
```
✓ Helm is installed
✓ Chart structure valid
✓ Linting passed
✓ Dev environment validation passed
✓ Staging environment validation passed
✓ Production environment validation passed
```

### Template Rendering

Verify each environment renders correctly:

```bash
# Development
helm template ru-ecom-ops ./helm/ru-ecom-ops \
  -f ./helm/ru-ecom-ops/values-dev.yaml > /tmp/dev-manifest.yaml
wc -l /tmp/dev-manifest.yaml

# Staging
helm template ru-ecom-ops ./helm/ru-ecom-ops \
  -f ./helm/ru-ecom-ops/values-staging.yaml > /tmp/staging-manifest.yaml
wc -l /tmp/staging-manifest.yaml

# Production
helm template ru-ecom-ops ./helm/ru-ecom-ops \
  -f ./helm/ru-ecom-ops/values-prod.yaml > /tmp/prod-manifest.yaml
wc -l /tmp/prod-manifest.yaml
```

All should generate manifests with 50+ lines (indicating valid templates).

---

## Workflow File Verification

### Validate YAML Syntax

```bash
# Install yamllint if needed
brew install yamllint  # macOS
# or: apt-get install yamllint  # Linux

# Validate all workflows
yamllint .github/workflows/

# Expected: No errors
```

### Verify Workflow Triggers

- [ ] `helm-validate.yml` triggers on PR with helm/** path changes
- [ ] `deploy-dev.yml` triggers on push to `develop` branch
- [ ] `deploy-staging.yml` triggers on push to `release/**` branches
- [ ] `deploy-prod.yml` triggers on push of `v*` tags

Test by:
```bash
# Create a release branch
git checkout -b release/v1.0.0

# Make a Helm change
# Push and check if workflow triggers
git push origin release/v1.0.0

# Check GitHub Actions tab for workflow run
```

---

## Cluster Access Verification

### Test Kubeconfig Locally

Before adding to GitHub, verify each kubeconfig works:

```bash
# Development
export KUBECONFIG=~/.kube/config-dev
kubectl cluster-info
kubectl get nodes
kubectl auth can-i get pods --namespace default

# Staging
export KUBECONFIG=~/.kube/config-staging
kubectl cluster-info

# Production
export KUBECONFIG=~/.kube/config-prod
kubectl cluster-info
```

### Test Base64 Encoding/Decoding

Verify the encoded secret can be decoded in the workflow:

```bash
# Locally encode
ENCODED=$(cat ~/.kube/config-dev | base64 -w0)

# Simulate workflow decoding
echo "$ENCODED" | base64 -d > /tmp/test-kubeconfig
kubectl --kubeconfig=/tmp/test-kubeconfig cluster-info
```

---

## Full Integration Test

### Test Development Deployment

1. **Prepare test change**:
   ```bash
   git checkout develop
   git pull origin develop
   
   # Make a minor helm change (e.g., update Prometheus image tag in values-dev.yaml)
   # Commit and push
   git add helm/
   git commit -m "test: verify dev deployment"
   git push origin develop
   ```

2. **Monitor workflow**:
   - Go to GitHub → Actions tab
   - Find the `Deploy to Development` workflow
   - Watch it progress through all steps
   - Should complete in 3-5 minutes

3. **Verify deployment**:
   ```bash
   export KUBECONFIG=~/.kube/config-dev
   kubectl get deployments -n ru-ecom-ops
   kubectl get pods -n ru-ecom-ops
   kubectl logs -n ru-ecom-ops -l app=prometheus --tail=20
   ```

### Test Staging Deployment

1. **Create release branch**:
   ```bash
   git checkout -b release/v1.0.0
   git push origin release/v1.0.0
   ```

2. **Monitor workflow**:
   - Workflow should trigger and wait for approval
   - Go to Actions → Review deployments
   - Click "Approve and deploy"

3. **Verify deployment**:
   ```bash
   export KUBECONFIG=~/.kube/config-staging
   kubectl get deployments -n ru-ecom-ops
   ```

### Test Production Deployment

1. **Create version tag**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

2. **Monitor workflow**:
   - Workflow should run security checks
   - Then wait for approval
   - Should create backup artifact

3. **Review before approval**:
   - Check deployment records artifact
   - Review backup artifact
   - Verify security scan passed

---

## Troubleshooting Setup Issues

### "Permission denied" for kubectl

**Problem**: Workflow fails with kubectl permission error

**Solution**:
```bash
# Check current user permissions in cluster
kubectl auth can-i '*' '*'

# User should have at least:
kubectl auth can-i create deployments --namespace ru-ecom-ops
kubectl auth can-i create secrets --namespace ru-ecom-ops
kubectl auth can-i get pods --namespace ru-ecom-ops
```

### "Secret not found" in GitHub Actions

**Problem**: Workflow says secret is missing even though it's configured

**Solution**:
```bash
# Verify secret is set at repo level, not organization level
gh secret list --repo owner/repo

# Secret names are case-sensitive
# KUBECONFIG_DEV ≠ kubeconfig_dev
```

### "Invalid kubeconfig" error

**Problem**: Workflow fails to decode kubeconfig

**Solution**:
```bash
# Verify base64 encoding is correct (single line, no spaces)
cat ~/.kube/config-dev | base64 -w0 | wc -c
# Should be a long single line

# Test decoding locally
echo "$ENCODED_SECRET" | base64 -d | head -5
# Should show kubeconfig content starting with "apiVersion"
```

### Helm lint fails in workflow

**Problem**: "Chart.yaml not found" or similar errors

**Solution**:
```bash
# Verify chart structure
ls -la helm/ru-ecom-ops/
ls -la helm/ru-ecom-ops/templates/

# Check file permissions
chmod +x scripts/*.sh
git add scripts/
git commit -m "fix: ensure scripts are executable"
git push
```

### Slack webhook test fails

**Problem**: Workflow notifies but notification doesn't appear in Slack

**Solution**:
```bash
# Test webhook URL with curl
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message"}'

# If 200 OK is returned, webhook works
# Check Slack app permissions:
# - Read and write to channels
# - Send direct messages
```

---

## Post-Deployment Verification

### Check Workflow Artifacts

After first successful deployment:

1. **Review deployment records**:
   - Go to Actions → Completed run
   - Download artifacts → `deployment-records` or `production-deployment-records`
   - Verify timestamp, actor, commit info

2. **Check backup artifacts** (production only):
   - Download `production-backup` artifact
   - Verify `backup-prod-values.yaml` and `backup-prod-manifest.yaml` exist
   - Size should match Helm release size

### Monitor Health Checks

```bash
# Check pod readiness
kubectl get pods -n ru-ecom-ops

# Check rollout status
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops
kubectl rollout status deployment/ru-ecom-ops-alertmanager -n ru-ecom-ops

# View recent events
kubectl describe deployment/ru-ecom-ops-prometheus -n ru-ecom-ops
```

### Verify Notifications

- [ ] Success notifications appear in Slack channels
- [ ] Failure notifications trigger immediately
- [ ] PagerDuty incidents created for production issues (if configured)

---

## Final Validation Checklist

Before declaring setup complete:

- [ ] All 9 secrets are created in GitHub
- [ ] All 3 environments are configured with correct branch filters
- [ ] Helm chart structure is valid and renders for all environments
- [ ] Workflow YAML files have valid syntax
- [ ] Kubeconfigs work locally with kubectl
- [ ] Base64 encoding/decoding works correctly
- [ ] Development deployment test passed successfully
- [ ] Staging deployment test passed (with approval)
- [ ] Workflow artifacts are created and accessible
- [ ] Slack notifications work for all environments
- [ ] GitHub Actions logs show no permission errors
- [ ] Team members can approve deployments
- [ ] Documentation has been reviewed and shared with team

---

## Next Steps

Once verification is complete:

1. **Document any customizations** made during setup
2. **Create runbooks** for common operational tasks
3. **Schedule team training** on deployment procedures
4. **Set up monitoring** for deployment frequency and success rates
5. **Establish approval policies** and reviewer groups
6. **Plan first production deployment** with full team

---

## Related Documentation

- [GitHub Actions CI/CD Pipeline Guide](./GITHUB_ACTIONS_CI_CD.md)
- [Helm Deployment Operations](./HELM_DEPLOYMENT_OPERATIONS.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
