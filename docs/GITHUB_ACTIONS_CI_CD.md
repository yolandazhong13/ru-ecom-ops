# GitHub Actions CI/CD Pipeline for Helm Deployments

## Overview

This guide explains how to set up GitHub Actions workflows for automated deployment of the ru-ecom-ops monitoring stack across development, staging, and production environments.

---

## Prerequisites

### Repository Setup

1. **Secrets Configuration**
   - `KUBECONFIG_DEV`: Base64-encoded kubeconfig for dev cluster
   - `KUBECONFIG_STAGING`: Base64-encoded kubeconfig for staging cluster
   - `KUBECONFIG_PROD`: Base64-encoded kubeconfig for production cluster
   - `SLACK_WEBHOOK_DEV`: Slack webhook URL for dev environment
   - `SLACK_WEBHOOK_STAGING`: Slack webhook URL for staging environment
   - `SLACK_WEBHOOK_PROD`: Slack webhook URL for production environment
   - `PAGERDUTY_ROUTING_KEY_STAGING`: PagerDuty routing key for staging
   - `PAGERDUTY_ROUTING_KEY_PROD`: PagerDuty routing key for production

2. **GitHub Environments** (Optional but Recommended)
   - `development`: Auto-deploy on merge to `develop` branch
   - `staging`: Manual approval required for `release/*` branches
   - `production`: Manual approval required for version tags

---

## Workflow Files

### 1. Validate Helm Chart on Pull Request

**File: `.github/workflows/helm-validate.yml`**

This workflow validates the Helm chart whenever a pull request is created or updated.

```yaml
name: Validate Helm Chart

on:
  pull_request:
    paths:
      - 'helm/**'
      - '.github/workflows/helm-validate.yml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Helm
        uses: azure/setup-helm@v3
        with:
          version: v3.12.0
      
      - name: Lint Helm Chart
        run: |
          helm lint ./helm/ru-ecom-ops
      
      - name: Template Validation - Dev
        run: |
          helm template ru-ecom-ops ./helm/ru-ecom-ops \
            -f ./helm/ru-ecom-ops/values-dev.yaml \
            > /tmp/dev-manifest.yaml
          echo "✓ Dev environment manifests generated"
      
      - name: Template Validation - Staging
        run: |
          helm template ru-ecom-ops ./helm/ru-ecom-ops \
            -f ./helm/ru-ecom-ops/values-staging.yaml \
            > /tmp/staging-manifest.yaml
          echo "✓ Staging environment manifests generated"
      
      - name: Template Validation - Prod
        run: |
          helm template ru-ecom-ops ./helm/ru-ecom-ops \
            -f ./helm/ru-ecom-ops/values-prod.yaml \
            > /tmp/prod-manifest.yaml
          echo "✓ Production environment manifests generated"
      
      - name: YAML Syntax Check
        uses: ibiqlik/action-yamllint@v3
        with:
          file_or_dir: helm/ru-ecom-ops
          config_data: |
            extends: default
            rules:
              line-length:
                max: 120
              indentation:
                spaces: 2
      
      - name: Comment on PR
        if: success()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Helm chart validation passed\n\n' +
                    '- Chart linting: **PASSED**\n' +
                    '- Dev environment: **OK**\n' +
                    '- Staging environment: **OK**\n' +
                    '- Production environment: **OK**'
            })

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: 'helm/ru-ecom-ops'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### 2. Deploy to Development

**File: `.github/workflows/deploy-dev.yml`**

This workflow automatically deploys to development on push to the `develop` branch.

```yaml
name: Deploy to Development

on:
  push:
    branches:
      - develop
    paths:
      - 'helm/**'
      - 'docs/**'
      - '.github/workflows/deploy-dev.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: development
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Helm
        uses: azure/setup-helm@v3
        with:
          version: v3.12.0
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: v1.27.0
      
      - name: Configure kubeconfig
        env:
          KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_DEV }}
        run: |
          mkdir -p $HOME/.kube
          echo "$KUBECONFIG_CONTENT" | base64 -d > $HOME/.kube/config
          chmod 600 $HOME/.kube/config
      
      - name: Validate Helm Chart
        run: |
          ./scripts/validate-helm-chart.sh
      
      - name: Create Slack secret
        run: |
          kubectl create namespace ru-ecom-ops --dry-run=client -o yaml | kubectl apply -f -
          kubectl create secret generic alertmanager-secrets \
            --from-literal=slack-webhook-url='${{ secrets.SLACK_WEBHOOK_DEV }}' \
            -n ru-ecom-ops \
            --dry-run=client -o yaml | kubectl apply -f -
      
      - name: Deploy Helm Chart
        run: |
          ./scripts/deploy-helm-chart.sh dev
      
      - name: Verify Deployment
        run: |
          ./scripts/verify-deployment.sh ru-ecom-ops 300
      
      - name: Notify Success
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_DEV }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "✅ Development deployment successful",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Development Deployment Complete*\n\n:white_check_mark: Helm chart deployed successfully\n`Commit:` `${{ github.sha }}`"
                  }
                }
              ]
            }'
      
      - name: Notify Failure
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_DEV }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "❌ Development deployment failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Development Deployment Failed*\n\n:x: Deployment encountered errors\n`Commit:` `${{ github.sha }}`\n`Branch:` `${{ github.ref }}`"
                  }
                }
              ]
            }'
```

### 3. Deploy to Staging

**File: `.github/workflows/deploy-staging.yml`**

This workflow deploys to staging on release branch with manual approval.

```yaml
name: Deploy to Staging

on:
  push:
    branches:
      - 'release/**'
  workflow_dispatch:  # Manual trigger
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging

jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      dry_run: ${{ steps.meta.outputs.dry_run }}
    steps:
      - uses: actions/checkout@v3
      
      - name: Determine version
        id: version
        run: |
          VERSION=$(git describe --tags --always --dirty)
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Set metadata
        id: meta
        run: |
          echo "dry_run=false" >> $GITHUB_OUTPUT

  approval-check:
    runs-on: ubuntu-latest
    environment: staging
    needs: prepare
    steps:
      - run: echo "Approval granted for staging deployment - Version ${{ needs.prepare.outputs.version }}"

  deploy:
    runs-on: ubuntu-latest
    needs: [prepare, approval-check]
    environment: staging
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Helm
        uses: azure/setup-helm@v3
        with:
          version: v3.12.0
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: v1.27.0
      
      - name: Configure kubeconfig
        env:
          KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_STAGING }}
        run: |
          mkdir -p $HOME/.kube
          echo "$KUBECONFIG_CONTENT" | base64 -d > $HOME/.kube/config
          chmod 600 $HOME/.kube/config
      
      - name: Validate Helm Chart
        run: |
          ./scripts/validate-helm-chart.sh
      
      - name: Create Secrets
        run: |
          kubectl create namespace ru-ecom-ops --dry-run=client -o yaml | kubectl apply -f -
          kubectl create secret generic alertmanager-secrets \
            --from-literal=slack-webhook-url='${{ secrets.SLACK_WEBHOOK_STAGING }}' \
            -n ru-ecom-ops \
            --dry-run=client -o yaml | kubectl apply -f -
          kubectl create secret generic alertmanager-pagerduty \
            --from-literal=pagerduty-routing-key='${{ secrets.PAGERDUTY_ROUTING_KEY_STAGING }}' \
            -n ru-ecom-ops \
            --dry-run=client -o yaml | kubectl apply -f -
      
      - name: Dry-run Deployment
        run: |
          ./scripts/deploy-helm-chart.sh staging dry-run
      
      - name: Deploy Helm Chart
        run: |
          ./scripts/deploy-helm-chart.sh staging
      
      - name: Verify Deployment
        run: |
          ./scripts/verify-deployment.sh ru-ecom-ops 300
      
      - name: Health Check - Prometheus
        run: |
          kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops --timeout=5m
      
      - name: Health Check - Alertmanager
        run: |
          kubectl rollout status deployment/ru-ecom-ops-alertmanager -n ru-ecom-ops --timeout=5m
      
      - name: Create Deployment Record
        run: |
          cat > deployment-record-staging.txt << EOF
          Deployment: Staging
          Version: ${{ needs.prepare.outputs.version }}
          Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')
          Triggered by: ${{ github.actor }}
          Commit: ${{ github.sha }}
          Branch: ${{ github.ref_name }}
          EOF
          cat deployment-record-staging.txt
      
      - name: Upload Deployment Record
        uses: actions/upload-artifact@v3
        with:
          name: deployment-records
          path: deployment-record-staging.txt
      
      - name: Notify Slack - Success
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_STAGING }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "✅ Staging deployment successful",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Complete*\n\n:white_check_mark: Version: `${{ needs.prepare.outputs.version }}`\n`Commit:` `${{ github.sha }}`\n`Actor:` `${{ github.actor }}`"
                  }
                }
              ]
            }'
      
      - name: Notify Slack - Failure
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_STAGING }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "❌ Staging deployment failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Failed*\n\n:x: Version: `${{ needs.prepare.outputs.version }}`\n`Commit:` `${{ github.sha }}`\n`Actor:` `${{ github.actor }}`"
                  }
                }
              ]
            }'
```

### 4. Deploy to Production

**File: `.github/workflows/deploy-prod.yml`**

This workflow deploys to production on version tags with manual approval.

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy'
        required: true

jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v3
      
      - name: Determine version
        id: version
        run: |
          if [[ "${{ github.ref }}" == refs/tags/* ]]; then
            VERSION=${GITHUB_REF#refs/tags/}
          else
            VERSION=${{ github.event.inputs.version }}
          fi
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "Deploying version: $VERSION"

  security-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run security scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: 'helm/ru-ecom-ops'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'
      
      - name: Check for hardcoded secrets
        run: |
          if grep -r "password\|secret\|token\|key" helm/ru-ecom-ops/*.yaml | grep -v "^#" ; then
            echo "⚠️  Potential hardcoded secrets detected"
            exit 1
          fi
          echo "✓ No hardcoded secrets found"

  approval-check:
    runs-on: ubuntu-latest
    environment: production
    needs: [prepare, security-checks]
    steps:
      - run: echo "⚠️  Production deployment requires manual approval"
      - run: echo "Approval granted for production deployment - Version ${{ needs.prepare.outputs.version }}"

  backup:
    runs-on: ubuntu-latest
    needs: approval-check
    environment: production
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: v1.27.0
      
      - name: Configure kubeconfig
        env:
          KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_PROD }}
        run: |
          mkdir -p $HOME/.kube
          echo "$KUBECONFIG_CONTENT" | base64 -d > $HOME/.kube/config
          chmod 600 $HOME/.kube/config
      
      - name: Backup Current Release
        run: |
          helm get values ru-ecom-ops -n ru-ecom-ops > backup-prod-values.yaml
          helm get manifest ru-ecom-ops -n ru-ecom-ops > backup-prod-manifest.yaml
          echo "Backup created at $(date)"
      
      - name: Upload Backup
        uses: actions/upload-artifact@v3
        with:
          name: production-backup
          path: |
            backup-prod-values.yaml
            backup-prod-manifest.yaml
          retention-days: 30

  deploy:
    runs-on: ubuntu-latest
    needs: [prepare, backup]
    environment: production
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ needs.prepare.outputs.version }}
      
      - name: Set up Helm
        uses: azure/setup-helm@v3
        with:
          version: v3.12.0
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: v1.27.0
      
      - name: Configure kubeconfig
        env:
          KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_PROD }}
        run: |
          mkdir -p $HOME/.kube
          echo "$KUBECONFIG_CONTENT" | base64 -d > $HOME/.kube/config
          chmod 600 $HOME/.kube/config
      
      - name: Validate Helm Chart
        run: |
          ./scripts/validate-helm-chart.sh
      
      - name: Create Secrets
        run: |
          kubectl create namespace ru-ecom-ops --dry-run=client -o yaml | kubectl apply -f -
          kubectl create secret generic alertmanager-secrets \
            --from-literal=slack-webhook-url='${{ secrets.SLACK_WEBHOOK_PROD }}' \
            -n ru-ecom-ops \
            --dry-run=client -o yaml | kubectl apply -f -
          kubectl create secret generic alertmanager-pagerduty \
            --from-literal=pagerduty-routing-key='${{ secrets.PAGERDUTY_ROUTING_KEY_PROD }}' \
            -n ru-ecom-ops \
            --dry-run=client -o yaml | kubectl apply -f -
      
      - name: Dry-run Deployment
        run: |
          ./scripts/deploy-helm-chart.sh prod dry-run
      
      - name: Deploy Helm Chart
        run: |
          ./scripts/deploy-helm-chart.sh prod
      
      - name: Verify Deployment
        run: |
          ./scripts/verify-deployment.sh ru-ecom-ops 600
      
      - name: Health Check - 5 minutes
        run: |
          kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops --timeout=5m
          kubectl rollout status deployment/ru-ecom-ops-alertmanager -n ru-ecom-ops --timeout=5m
      
      - name: Smoke Tests
        run: |
          # Check Prometheus targets
          kubectl exec -n ru-ecom-ops $(kubectl get pod -n ru-ecom-ops -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
            -- curl -s http://localhost:9090/-/ready
          
          # Check Alertmanager readiness
          kubectl exec -n ru-ecom-ops $(kubectl get pod -n ru-ecom-ops -l app=alertmanager -o jsonpath='{.items[0].metadata.name}') \
            -- curl -s http://localhost:9093/-/ready
      
      - name: Create Deployment Record
        run: |
          cat > deployment-record-prod-${{ needs.prepare.outputs.version }}.txt << EOF
          Deployment: Production
          Version: ${{ needs.prepare.outputs.version }}
          Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')
          Triggered by: ${{ github.actor }}
          Commit: ${{ github.sha }}
          Branch: ${{ github.ref_name }}
          EOF
      
      - name: Upload Deployment Record
        uses: actions/upload-artifact@v3
        with:
          name: production-deployment-records
          path: deployment-record-prod-${{ needs.prepare.outputs.version }}.txt
          retention-days: 90
      
      - name: Notify Slack - Success
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_PROD }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "✅ Production deployment successful",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment Complete*\n\n:white_check_mark: Version: `${{ needs.prepare.outputs.version }}`\n`Commit:` `${{ github.sha }}`\n`Actor:` `${{ github.actor }}`\n:rocket: All systems operational"
                  }
                }
              ]
            }'
      
      - name: Notify Slack - Failure
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_PROD }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "❌ Production deployment failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment Failed*\n\n:x: Version: `${{ needs.prepare.outputs.version }}`\n`Commit:` `${{ github.sha }}`\n`Actor:` `${{ github.actor }}`\n:warning: Check logs and consider rollback"
                  }
                }
              ]
            }'

  rollback-on-failure:
    runs-on: ubuntu-latest
    needs: [prepare, deploy]
    if: failure()
    environment: production
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Helm
        uses: azure/setup-helm@v3
        with:
          version: v3.12.0
      
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: v1.27.0
      
      - name: Configure kubeconfig
        env:
          KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_PROD }}
        run: |
          mkdir -p $HOME/.kube
          echo "$KUBECONFIG_CONTENT" | base64 -d > $HOME/.kube/config
          chmod 600 $HOME/.kube/config
      
      - name: Check Helm History
        run: |
          helm history ru-ecom-ops -n ru-ecom-ops
      
      - name: Manual Rollback Required
        run: |
          echo "⚠️  Automatic rollback is NOT enabled"
          echo "Manual intervention required"
          echo ""
          echo "To rollback, run:"
          echo "  helm rollback ru-ecom-ops -n ru-ecom-ops"
          exit 1
```

---

## Setup Instructions

### 1. Create Secrets in GitHub

```bash
# Navigate to repository Settings → Secrets and variables → Actions

# Add kubeconfigs (base64-encoded)
KUBECONFIG_DEV=$(cat ~/.kube/config-dev | base64 -w0) && echo "KUBECONFIG_DEV: $KUBECONFIG_DEV"
KUBECONFIG_STAGING=$(cat ~/.kube/config-staging | base64 -w0) && echo "KUBECONFIG_STAGING: $KUBECONFIG_STAGING"
KUBECONFIG_PROD=$(cat ~/.kube/config-prod | base64 -w0) && echo "KUBECONFIG_PROD: $KUBECONFIG_PROD"

# Add Slack webhooks
SLACK_WEBHOOK_DEV=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_WEBHOOK_STAGING=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_WEBHOOK_PROD=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Add PagerDuty routing keys
PAGERDUTY_ROUTING_KEY_STAGING=your-pagerduty-routing-key
PAGERDUTY_ROUTING_KEY_PROD=your-pagerduty-routing-key
```

### 2. Create GitHub Environments

```
Settings → Environments → Create environment
  - Name: development
  - Deployment branches: develop
  
  - Name: staging
  - Deployment branches: release/*
  - Add protection rule: Require manual approval
  
  - Name: production
  - Deployment branches: main (protect tags)
  - Add protection rule: Require manual approval
  - Restrict who can review deployments (optional)
```

### 3. Place Workflow Files

```bash
mkdir -p .github/workflows
cp docs/GITHUB_ACTIONS_CI_CD.md .github/workflows/
# Create the individual workflow files from above
```

---

## Deployment Strategies

### Development (Automatic)
- **Trigger**: Push to `develop` branch
- **Approval**: None (automatic)
- **Duration**: ~3-5 minutes
- **Validation**: Basic linting

### Staging (Semi-Automatic)
- **Trigger**: Push to `release/*` branches or manual workflow dispatch
- **Approval**: Required
- **Duration**: ~5-10 minutes
- **Validation**: Full validation + dry-run

### Production (Manual with Approvals)
- **Trigger**: Push of version tags (`v*`) or manual workflow dispatch
- **Approval**: Required (security checks + team approval)
- **Duration**: ~10-15 minutes
- **Validation**: Full security scan + backup + dry-run
- **Rollback**: Manual (creates backup artifact)

---

## Monitoring CI/CD Pipeline

### View Workflow Status
```bash
# In GitHub UI: Actions tab
# Shows all workflow runs with status badges
```

### Troubleshoot Failed Deployments
```bash
# GitHub shows detailed logs for each step
# Download artifacts (backups, deployment records) from Actions
# Check Slack notifications for error details
```

### Manual Interventions

```bash
# If automatic deployment fails and manual fix needed:

# 1. SSH to cluster
# 2. Check pod status
kubectl get pods -n ru-ecom-ops

# 3. Check logs
kubectl logs -n ru-ecom-ops -l app=prometheus --tail=100

# 4. Manually run verification
./scripts/verify-deployment.sh ru-ecom-ops

# 5. Trigger re-run from GitHub Actions UI
```

---

## Best Practices

1. **Always use dry-run for production**
   - Workflow includes dry-run step before actual deployment
   - Review manifests in logs before proceeding

2. **Keep secrets secure**
   - Use GitHub environment protection rules
   - Rotate kubeconfigs regularly
   - Never commit secrets to repository

3. **Tag releases semantically**
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```

4. **Use branch protection rules**
   - Require PR reviews before merge to main/develop
   - Require status checks to pass
   - Restrict who can merge (optional)

5. **Monitor deployment metrics**
   - Track successful vs failed deployments
   - Monitor deployment frequency
   - Analyze rollback frequency
   - Alert on deployment anomalies

6. **Maintain deployment records**
   - Artifacts retained for 30-90 days
   - Track who deployed what, when
   - Review for audit compliance

---

## Troubleshooting

### Kubeconfig Not Found
```
Error: kubeconfig path does not exist
Solution: Verify KUBECONFIG secret is base64-encoded correctly
  echo -n "$(cat ~/.kube/config)" | base64 -w0
```

### Secret Not Found in Cluster
```
Error: Secret 'alertmanager-secrets' not found
Solution: Workflow creates secret from GitHub Secrets
  Verify SLACK_WEBHOOK_* secrets are set in GitHub
```

### Helm Chart Lint Fails
```
Error: Chart.yaml not found
Solution: Verify helm chart directory structure
  ls -la helm/ru-ecom-ops/
```

### Pod Readiness Timeout
```
Error: Pods not ready after 5 minutes
Solution: Check resource availability, check pod logs
  kubectl describe pod -n ru-ecom-ops
  kubectl logs -n ru-ecom-ops -l app=prometheus
```

### Manual Approval Stuck
```
GitHub Actions shows waiting for approval
Solution: 
  1. Go to Actions tab
  2. Click on workflow run
  3. Click "Review deployments"
  4. Select environment and "Approve and deploy"
```

---

## Related Documentation

- [Helm Deployment Operations Guide](./HELM_DEPLOYMENT_OPERATIONS.md)
- [Helm Deployment Guide](./HELM_DEPLOYMENT_GUIDE.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Kubernetes Deployment Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
