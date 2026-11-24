# Test Deployment Plan — Phase 9 Validation

**Purpose**: Validate the entire GitHub Actions CI/CD pipeline end-to-end before team onboarding  
**Date**: 2026-11-24  
**Status**: Starting

---

## Overview

This plan tests the complete deployment hierarchy:
1. **Development** (automatic) — validate immediate feedback loop
2. **Staging** (approval-gated) — validate approval workflow and PagerDuty integration
3. **Production** (security + approval-gated) — validate security checks, backups, extended health checks

---

## Pre-Test Checklist

### Local Environment Verification
- [ ] `helm` is installed and working
- [ ] `kubectl` can connect to development cluster
- [ ] `kubectl` can connect to staging cluster
- [ ] `kubectl` can connect to production cluster
- [ ] `jq` is installed for JSON parsing
- [ ] `base64` can encode/decode kubeconfigs

### Repository Setup
- [ ] All 4 GitHub Actions workflow files exist in `.github/workflows/`
- [ ] All 3 deployment scripts exist in `scripts/` and are executable
- [ ] Helm chart exists in `helm/ru-ecom-ops/` with all environment values files
- [ ] Git remote is set to GitHub repository

### GitHub Secrets Configuration
- [ ] `KUBECONFIG_DEV` — base64-encoded dev kubeconfig
- [ ] `KUBECONFIG_STAGING` — base64-encoded staging kubeconfig
- [ ] `KUBECONFIG_PROD` — base64-encoded prod kubeconfig
- [ ] `SLACK_WEBHOOK_DEV` — Slack webhook for dev notifications
- [ ] `SLACK_WEBHOOK_STAGING` — Slack webhook for staging notifications
- [ ] `SLACK_WEBHOOK_PROD` — Slack webhook for prod notifications
- [ ] `PAGERDUTY_ROUTING_KEY_STAGING` — PagerDuty routing key for staging
- [ ] `PAGERDUTY_ROUTING_KEY_PROD` — PagerDuty routing key for production

### GitHub Environments Configuration
- [ ] `development` environment exists (no approval required)
- [ ] `staging` environment exists (approval required)
- [ ] `production` environment exists (approval required, security checks enabled)

---

## Test Phases

### Phase 1: Development Deployment Test

**Trigger**: Push to `develop` branch with Helm chart change

**Expected Workflow**:
1. Git workflow triggers `deploy-dev.yml`
2. Helm chart validates without errors
3. Deployment proceeds without approval (automatic)
4. Completes in 3-5 minutes
5. Slack notification appears in dev channel

**Verification Steps**:
```bash
# 1. Check workflow run status
gh run list --workflow=deploy-dev.yml --limit=1

# 2. Monitor pod deployment
kubectl get pods -n ru-ecom-ops -w

# 3. Verify Prometheus is running
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops

# 4. Check deployment logs
kubectl logs -n ru-ecom-ops -l app=prometheus --tail=20
```

**Success Criteria**:
- ✓ Workflow completes without errors
- ✓ All pods reach Running state
- ✓ Deployment rollout succeeds
- ✓ Slack notification delivered
- ✓ Pod logs show successful startup

**Expected Issues to Document**:
- [ ] Kubeconfig decoding issues
- [ ] Namespace creation problems
- [ ] Secret injection failures
- [ ] Image pull errors
- [ ] Resource limit issues

---

### Phase 2: Staging Deployment Test

**Trigger**: Push to `release/v1.0.0` branch

**Expected Workflow**:
1. Git workflow triggers `deploy-staging.yml`
2. Workflow waits for manual approval
3. Approve deployment via GitHub UI or CLI
4. Pre-deployment dry-run executes
5. Deployment proceeds
6. Health checks run (5-minute timeout)
7. Completes in 5-10 minutes total
8. Slack notification appears in staging channel
9. PagerDuty alert/incident created

**Verification Steps**:
```bash
# 1. Check if workflow is waiting for approval
gh run list --workflow=deploy-staging.yml --limit=1 --status=waiting

# 2. Approve deployment via CLI
gh run view <RUN_ID> --json=url

# 3. Monitor pod deployment
kubectl get pods -n ru-ecom-ops -w

# 4. Check health check status
kubectl rollout status deployment/ru-ecom-ops-alertmanager -n ru-ecom-ops --timeout=5m

# 5. Verify Slack notification
# (Manual check in Slack #staging-deployments channel)

# 6. Verify PagerDuty incident
# (Manual check in PagerDuty dashboard)
```

**Success Criteria**:
- ✓ Workflow waits for approval at approval-check job
- ✓ Deployment proceeds after approval
- ✓ Dry-run validation completes
- ✓ All pods reach Running state
- ✓ Health checks pass with 5-minute timeout
- ✓ Slack notification delivered to staging channel
- ✓ PagerDuty incident created (if configured)
- ✓ Deployment records artifact created

**Expected Issues to Document**:
- [ ] Approval timeout issues
- [ ] Dry-run validation failures
- [ ] Health check timeouts
- [ ] PagerDuty integration problems
- [ ] Slack notification delivery failures

---

### Phase 3: Production Deployment Test

**Trigger**: Push of version tag `v1.0.0`

**Expected Workflow**:
1. Git tag triggers `deploy-prod.yml`
2. Security checks run (Trivy scan, hardcoded secret check)
3. If security checks pass, workflow waits for backup creation
4. Backup created and uploaded to artifacts
5. Manual approval required before deployment
6. Approve deployment via GitHub UI or CLI
7. Pre-deployment dry-run executes
8. Deployment proceeds
9. 5-minute extended health checks run
10. Smoke tests execute (curl health endpoints)
11. Deployment records created
12. Completes in 10-15 minutes total
13. Slack notification appears in prod channel
14. PagerDuty incident created

**Verification Steps**:
```bash
# 1. Check if workflow is in security-checks phase
gh run list --workflow=deploy-prod.yml --limit=1

# 2. Monitor security scan progress
gh run view <RUN_ID> --log-step="security-checks" --no-pager

# 3. Download backup artifact (after backup job completes)
gh run download <RUN_ID> --name production-backup --dir /tmp/prod-backup

# 4. Verify backup contents
ls -la /tmp/prod-backup/
grep -c "kind:" /tmp/prod-backup/backup-prod-manifest.yaml

# 5. Approve deployment when prompted
gh run view <RUN_ID> --json=url

# 6. Monitor deployment progress
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops --timeout=5m
kubectl rollout status deployment/ru-ecom-ops-alertmanager -n ru-ecom-ops --timeout=5m

# 7. Check smoke test results in logs
gh run view <RUN_ID> --log-step="Smoke Tests" --no-pager

# 8. Download deployment records
gh run download <RUN_ID> --name production-deployment-records

# 9. Verify Slack notification
# (Manual check in Slack #prod-deployments channel)

# 10. Verify PagerDuty incident
# (Manual check in PagerDuty dashboard)
```

**Success Criteria**:
- ✓ Security checks pass without CRITICAL/HIGH severity issues
- ✓ Hardcoded secrets check passes
- ✓ Backup artifact created with valid kubeconfig dump
- ✓ Deployment waits for approval after backup
- ✓ Deployment proceeds after approval
- ✓ Dry-run validation completes
- ✓ All pods reach Running state
- ✓ 5-minute extended health checks pass
- ✓ Smoke tests pass (curl health endpoints return success)
- ✓ Deployment records artifact created with actor/commit info
- ✓ Slack notification delivered to prod channel
- ✓ PagerDuty incident created (if configured)

**Expected Issues to Document**:
- [ ] Security scan failures (Trivy findings)
- [ ] Hardcoded secret detection (false positives)
- [ ] Backup creation issues
- [ ] Approval workflow problems
- [ ] Extended health check timeouts
- [ ] Smoke test failures (service connectivity)
- [ ] Artifact retention policy issues
- [ ] PagerDuty integration problems

---

## Rollback Testing

**Purpose**: Verify rollback procedures work in practice

**Testing Approach**:
1. After successful production deployment, manually trigger a rollback
2. Run rollback command and verify it succeeds
3. Verify pods return to previous version
4. Document rollback time and verification steps

**Rollback Steps**:
```bash
# 1. Check helm history to see available releases
kubectl config use-context prod  # or set KUBECONFIG
helm history ru-ecom-ops -n ru-ecom-ops

# 2. Rollback to previous release
helm rollback ru-ecom-ops -n ru-ecom-ops

# 3. Verify rollback completed
kubectl rollout status deployment/ru-ecom-ops-prometheus -n ru-ecom-ops

# 4. Verify pods restarted with previous image
kubectl get pods -n ru-ecom-ops
kubectl describe pod <POD_NAME> -n ru-ecom-ops | grep -A 5 "Image:"
```

**Success Criteria**:
- ✓ Helm rollback command succeeds
- ✓ Pods restart with previous image
- ✓ Services continue responding
- ✓ Total rollback time < 2 minutes

---

## Issue Tracking Template

For each issue encountered during test deployment:

```markdown
### Issue: [Brief Title]

**Phase**: Development | Staging | Production | Rollback

**Symptoms**: [What went wrong]

**Error Messages**: [Exact error output]

**Root Cause**: [What caused the problem]

**Fix Applied**: [Solution implemented]

**Prevention**: [How to prevent in future]

**Severity**: 🟢 Low | 🟡 Medium | 🔴 High | 🟣 Critical

**Documentation Updated**: Yes | No
```

---

## Failure Response Procedures

### If Development Deployment Fails
1. Check GitHub Actions logs for specific error
2. Run `./scripts/validate-helm-chart.sh` locally to diagnose
3. Fix issue in helm chart or scripts
4. Push fix to develop branch
5. Retry deployment

### If Staging Deployment Fails
1. Check approval workflow and GitHub environment configuration
2. Verify PagerDuty routing key is correct
3. Check Slack webhook URL is valid
4. Run health check commands manually
5. Fix issue and retry

### If Production Deployment Fails
1. Check security scan results (Trivy findings)
2. Review backup artifact to ensure backup succeeded
3. Check approval workflow configuration
4. Run smoke tests manually to diagnose service issues
5. If deployment is broken, execute rollback immediately
6. Document root cause and prevention

---

## Success Metrics

After completing all test phases:

**Deployment Reliability**:
- [ ] All 3 deployments completed successfully (100% success rate)
- [ ] No manual interventions required beyond expected approvals
- [ ] All automated health checks passed

**Observability**:
- [ ] All Slack notifications delivered correctly (3 channels)
- [ ] All deployment records created with correct metadata
- [ ] All backups created with correct content (prod only)
- [ ] All artifacts retained with correct retention policies

**Documentation**:
- [ ] All issues encountered documented with root causes
- [ ] All preventive measures identified
- [ ] All workarounds or fixes applied
- [ ] Setup guide updated based on learnings

**Operational Knowledge**:
- [ ] Team member can explain deployment hierarchy
- [ ] Team member can troubleshoot failed deployments
- [ ] Team member can execute rollback procedures
- [ ] Team member can configure new environments

---

## Timeline Estimate

| Phase | Estimated Time | Actual Time |
|-------|-----------------|-------------|
| Pre-test setup | 30 minutes | — |
| Phase 1 (Dev) | 10 minutes | — |
| Phase 2 (Staging) | 15 minutes | — |
| Phase 3 (Production) | 20 minutes | — |
| Rollback Testing | 10 minutes | — |
| Issue Documentation | 15 minutes | — |
| **Total** | **100 minutes** | — |

---

## Next Steps After Test Deployment

1. ✓ Document all issues with root causes
2. ✓ Update verification script based on learnings
3. ✓ Update setup guide with any gotchas discovered
4. ✓ Create troubleshooting guide supplement
5. ✓ Prepare team training materials
6. ✓ Schedule team onboarding session

