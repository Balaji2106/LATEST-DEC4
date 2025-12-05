# Auto-Remediation with Loop Prevention - Complete Guide

## Overview

This system implements intelligent auto-remediation for Azure Data Factory (ADF) pipeline failures with multiple layers of protection to prevent infinite loops and ticket spam.

## How It Works

### 1. Error Detection Flow

```
ADF Pipeline Fails
    ↓
Azure Monitor Alert
    ↓
Webhook → POST /azure-monitor
    ↓
AI RCA Analysis (Gemini)
    ↓
Policy Engine Decision
    ↓
[Requires Approval?] → Slack Button → User Clicks → Auto-Remediation
[Low Risk?] → Auto-Remediation (Immediate)
```

### 2. Slack Approval Flow

When an error is detected as auto-remediable but requires human approval (high risk/impact):

1. **Slack Notification Sent** with two buttons:
   - ✅ **Approve Auto-Remediation** (Green)
   - ❌ **Reject & Manual Fix** (Red)

2. **User clicks Approve**:
   - System triggers auto-remediation
   - Pipeline is re-run via Azure Logic App
   - Logic App monitors completion and sends callback

3. **User clicks Reject**:
   - Ticket marked as `remediation_status='rejected'`
   - Manual intervention required
   - No automatic retries

**Configuration**: The AI determines if approval is required based on:
- Error severity (Critical → requires approval)
- Business impact (High → requires approval)
- Remediation risk level (High → requires approval)

### 3. Auto-Remediation Retry Flow

```
Remediation Triggered
    ↓
Azure Logic App Retries Pipeline
    ↓
Logic App Monitors Status (30s intervals)
    ↓
[Success] → Callback → Close Ticket
[Failure] → Callback → Check Retry Count
    ↓
[Retries Available] → Wait (backoff) → Retry
[Max Retries Exceeded] → Mark as 'Remediation Failed' → Manual Intervention
```

## 🛡️ Loop Prevention Mechanisms

### Layer 1: Exact run_id Deduplication
- **Purpose**: Prevent duplicate tickets for the same pipeline run
- **How**: Checks `tickets.run_id` before creating new ticket
- **Result**: Returns `duplicate_ignored` status

### Layer 2: Remediation run_id Tracking
- **Purpose**: Prevent retry failures from creating new tickets
- **How**: Checks `remediation_attempts.remediation_run_id` table
- **When**: When webhook receives alert for a retry attempt
- **Result**: Returns `remediation_retry_ignored` status
- **Note**: Callback handler manages retry logic, not webhook

### Layer 3: Active Remediation Detection
- **Purpose**: Ignore webhooks during active remediation
- **How**: Checks for active remediation on same pipeline (last 20 min)
- **Query**: `remediation_status IN ('pending', 'in_progress', 'awaiting_approval')`
- **Result**: Returns `ignored_during_remediation` status

### Layer 4: Cooldown Period Enforcement
- **Purpose**: Prevent spam after exhausted retries
- **How**: After max retries exhausted, pipeline enters cooldown
- **Duration**: 30 minutes (configurable via `PIPELINE_COOLDOWN_MINUTES`)
- **Behavior**: New failures for same pipeline are ignored during cooldown
- **Result**: Returns `ignored_cooldown` status
- **Reason**: Forces manual intervention before new auto-remediation attempts

### Layer 5: Circuit Breaker (Global)
- **Purpose**: Prevent system overload
- **How**: Limits concurrent remediations globally
- **Threshold**: 10 concurrent remediations (configurable via `MAX_CONCURRENT_REMEDIATIONS`)
- **When**: Checked before triggering any new remediation
- **Result**: Returns error `Circuit breaker: Too many concurrent remediations`

### Layer 6: Max Retries Per Error Type
- **Purpose**: Limit retry attempts per error
- **Configuration**:
  ```python
  REMEDIABLE_ERRORS = {
      "GatewayTimeout": {
          "max_retries": 3,
          "backoff_seconds": [30, 60, 120]
      },
      "ThrottlingError": {
          "max_retries": 5,
          "backoff_seconds": [30, 60, 120, 300, 600]
      }
  }
  ```
- **Behavior**: After max retries, ticket marked as `remediation_status='applied_not_solved'`

## 🎯 Key Statuses

### Remediation Status Values
- **`pending`**: Auto-remediation eligible, not yet started
- **`awaiting_approval`**: Slack approval request sent, waiting for user
- **`in_progress`**: Remediation actively running
- **`succeeded`**: Remediation completed successfully
- **`applied_not_solved`**: Max retries exhausted, issue persists
- **`rejected`**: User rejected auto-remediation via Slack

### Ticket Status Values
- **`open`**: New issue, not acknowledged
- **`in_progress`**: Being worked on (either manual or auto-remediation failed)
- **`acknowledged`**: Human acknowledged ticket
- **`closed`**: Issue resolved

## 📊 Monitoring & Health

### Dashboard Features
1. **Remediation Health Banner**:
   - Status: Healthy / Degraded / Critical
   - Success Rate (last 24 hours)
   - Active Remediations Count
   - Pipelines in Cooldown
   - Circuit Breaker Status

2. **Remediation Failed Tab**:
   - Shows tickets with `remediation_status='applied_not_solved'`
   - Indicates manual intervention required

### API Endpoints

#### `/api/remediation-health`
Returns comprehensive health metrics:
```json
{
  "status": "healthy",
  "active_remediations": {
    "count": 2,
    "limit": 10,
    "utilization_pct": 20.0
  },
  "circuit_breaker": {
    "active": false,
    "threshold": 10
  },
  "last_24h_stats": {
    "total_attempts": 15,
    "succeeded": 12,
    "failed": 3,
    "success_rate_pct": 80.0
  },
  "cooldown": {
    "pipelines_count": 1,
    "cooldown_minutes": 30,
    "pipelines": [...]
  },
  "loop_prevention": {
    "webhooks_ignored_last_hour": 5
  }
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Enable/disable auto-remediation
AUTO_REMEDIATION_ENABLED=true

# Circuit breaker - max concurrent remediations (0 = unlimited)
MAX_CONCURRENT_REMEDIATIONS=10

# Cooldown period after exhausted retries (minutes)
PIPELINE_COOLDOWN_MINUTES=30

# Logic App URLs for remediation playbooks
PLAYBOOK_RETRY_PIPELINE=https://prod-xx.logic.azure.com/workflows/.../
PLAYBOOK_RESTART_CLUSTER=https://prod-yy.logic.azure.com/workflows/.../
PLAYBOOK_RETRY_JOB=https://prod-zz.logic.azure.com/workflows/.../

# Public URL for callbacks (must be accessible from Azure)
PUBLIC_BASE_URL=https://your-rca-app.com

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_ALERT_CHANNEL=#alerts
```

## 🚫 What Won't Cause Loops

The following scenarios are **safe** and will NOT create infinite loops:

### ✅ Scenario 1: Pipeline fails during remediation
- **What happens**: Azure Monitor sends webhook for retry failure
- **Protection**: Layer 2 (Remediation run_id Tracking)
- **Result**: Webhook ignored, callback handler manages retry logic

### ✅ Scenario 2: Multiple alerts for same failure
- **What happens**: Azure sends duplicate alerts for same run_id
- **Protection**: Layer 1 (Exact run_id Deduplication)
- **Result**: Subsequent webhooks ignored

### ✅ Scenario 3: Pipeline keeps failing after retries
- **What happens**: All retry attempts exhausted
- **Protection**: Layer 4 (Cooldown Period) + Layer 6 (Max Retries)
- **Result**:
  - Ticket marked as `applied_not_solved`
  - 30-minute cooldown activated
  - New failures ignored during cooldown
  - Manual intervention required

### ✅ Scenario 4: Too many concurrent remediations
- **What happens**: System trying to remediate 10+ pipelines simultaneously
- **Protection**: Layer 5 (Circuit Breaker)
- **Result**: New remediation attempts blocked until capacity available

### ✅ Scenario 5: Webhook during active remediation
- **What happens**: Alert arrives while remediation in progress
- **Protection**: Layer 3 (Active Remediation Detection)
- **Result**: Webhook ignored, existing remediation continues

## 📈 Success Metrics

### How to measure effectiveness:
1. **Success Rate**: Check `/api/remediation-health` for 24h success rate
2. **MTTR Reduction**: Compare avg resolution time before/after auto-remediation
3. **Manual Interventions**: Count tickets in "Remediation Failed" tab
4. **Loop Prevention**: Check `webhooks_ignored_last_hour` metric

### Expected behavior:
- ✅ Success rate > 70% = Healthy
- ⚠️ Success rate 40-70% = Degraded (review error types)
- ❌ Success rate < 40% = Critical (disable auto-remediation, investigate)

## 🐛 Troubleshooting

### Issue: Legitimate failures being ignored

**Symptoms**: New pipeline failure doesn't create ticket

**Possible causes**:
1. Pipeline in cooldown period (check audit trail for `webhook_ignored_cooldown`)
2. Active remediation for same pipeline (check `remediation_status`)
3. Duplicate run_id (check if ticket already exists)

**Solution**: Check audit trail with `ticket_id` or `pipeline_name`

### Issue: Circuit breaker frequently activating

**Symptoms**: Many remediations blocked, health status "critical"

**Possible causes**:
1. Too many pipelines failing simultaneously
2. `MAX_CONCURRENT_REMEDIATIONS` set too low
3. Remediations taking too long (check Logic App performance)

**Solution**:
- Increase `MAX_CONCURRENT_REMEDIATIONS`
- Optimize Logic App monitoring intervals
- Review pipeline error rates

### Issue: Remediations always failing

**Symptoms**: All attempts fail, success rate near 0%

**Possible causes**:
1. Wrong error type classification
2. Logic App configuration issue
3. Permissions issue in Azure
4. Backoff delays too short

**Solution**:
- Check Logic App execution history
- Verify Azure permissions
- Review error type configuration in `REMEDIABLE_ERRORS`
- Increase backoff delays

## 🔐 Security Considerations

### Webhook Security
- **No authentication**: Azure Monitor Action Groups don't support custom headers
- **Protection**: Keep webhook URL secret, use Azure NSG if possible
- **Validation**: Payload structure validated before processing

### Callback Security
- **No authentication**: Logic Apps don't easily support OAuth
- **Protection**: Callback URL contains secret path component
- **Validation**: ticket_id validated against database

## 📝 Audit Trail

All major events are logged to `audit_trail` table:

- `Ticket Created`
- `auto_remediation_triggered`
- `auto_remediation_attempt_failed`
- `auto_remediation_applied_but_not_solved`
- `approval_requested`
- `approval_granted`
- `approval_rejected`
- `webhook_ignored_during_remediation`
- `webhook_ignored_cooldown`
- `remediation_retry_webhook_ignored`
- `remediation_circuit_breaker`

Use audit trail to debug loop issues or track remediation history.

## 🎓 Best Practices

1. **Set realistic max_retries**: 3-5 attempts for most errors
2. **Use exponential backoff**: Give systems time to recover
3. **Monitor health endpoint**: Set up alerts if success rate drops
4. **Review failed remediations weekly**: Identify patterns
5. **Keep cooldown period reasonable**: 30 minutes allows breathing room
6. **Test approval flow**: Ensure Slack integration works
7. **Document custom error types**: Update this guide when adding new remediable errors

## 📚 Related Files

- **`genai_rca_assistant/main.py`**: Core logic (lines 2344-2505 for loop prevention)
- **`genai_rca_assistant/dashboard.html`**: Dashboard with health monitoring
- **`logic-apps/playbook-retry-adf-pipeline-with-callback-FIXED.json`**: Remediation Logic App
- **Database schema**: Tables `tickets`, `remediation_attempts`, `audit_trail`

---

**Last Updated**: 2025-12-05
**Version**: 2.0 (with enhanced loop prevention and Slack approval)
