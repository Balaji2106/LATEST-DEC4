# Databricks Auto-Remediation Setup Guide

## ✅ What Was Created

**File**: `logic-apps/playbook-databricks-with-callback.json`

This is a NEW Databricks Logic App that includes:
1. **Callback functionality** (like ADF)
2. **Status monitoring** (checks every 30 seconds)
3. **Three remediation actions**:
   - `retry_job` - Retriggers failed Databricks job and monitors until complete
   - `restart_cluster` - Restarts cluster and waits until RUNNING
   - `reinstall_libraries` - Restarts cluster to fix library issues

## 🔄 How It Works

```
RCA App sends request
    ↓
Logic App starts remediation
    ↓
Returns immediately with run_id
    ↓
Logic App monitors status (every 30s)
    ↓
When complete → Calls back to RCA app
    ↓
RCA app handles success/retry logic
```

## 📝 Deployment Steps

### Step 1: Deploy the Logic App to Azure

1. Go to Azure Portal
2. Create new Logic App (or update existing)
3. Name: `playbook-databricks-with-callback`
4. Import the JSON file

**PowerShell**:
```powershell
az login

az logic workflow create \
  --resource-group rg_techdemo_2025_Q4 \
  --name playbook-databricks-with-callback \
  --definition @logic-apps/playbook-databricks-with-callback.json \
  --location eastus
```

### Step 2: Configure Parameters

In Azure Portal → Logic App → Parameters:

1. **databricks_workspace_url**:
   ```
   https://adb-4063542298037379.19.azuredatabricks.net
   ```

2. **databricks_token**:
   - Store in Azure Key Vault (recommended)
   - OR paste directly (less secure)

### Step 3: Get the Logic App URL

After deployment:
1. Open Logic App in Azure Portal
2. Click "Logic app designer"
3. Click on the trigger (first box)
4. Copy the "HTTP POST URL"

Example:
```
https://prod-xx.westus.logic.azure.com:443/workflows/...
```

### Step 4: Update RCA App Configuration

Add to your environment variables:

```bash
# For retry_job action
PLAYBOOK_RETRY_JOB=https://prod-xx.westus.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?api-version=...

# For restart_cluster action
PLAYBOOK_RESTART_CLUSTER=https://prod-yy.westus.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?api-version=...

# For reinstall_libraries action
PLAYBOOK_REINSTALL_LIBRARIES=https://prod-zz.westus.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?api-version=...
```

**Note**: You can use the same Logic App URL for all three - it switches based on `remediation_action`.

### Step 5: Verify in RCA Code

The RCA app already has Databricks support in `main.py`:

```python
REMEDIABLE_ERRORS = {
    "DatabricksClusterStartFailure": {
        "action": "restart_cluster",
        "max_retries": 2,
        "backoff_seconds": [60, 180],
        "playbook_url": os.getenv("PLAYBOOK_RESTART_CLUSTER")
    },
    "DatabricksJobExecutionError": {
        "action": "retry_job",
        "max_retries": 3,
        "backoff_seconds": [30, 60, 120],
        "playbook_url": os.getenv("PLAYBOOK_RETRY_JOB")
    },
    "DatabricksLibraryInstallationError": {
        "action": "reinstall_libraries",
        "max_retries": 2,
        "backoff_seconds": [60, 180],
        "playbook_url": os.getenv("PLAYBOOK_REINSTALL_LIBRARIES")
    }
}
```

## 🧪 Testing

### Test 1: Retry Job
```bash
curl -X POST https://your-logic-app-url \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "your-job-id",
    "ticket_id": "TEST-001",
    "error_type": "DatabricksJobExecutionError",
    "original_run_id": "12345",
    "retry_attempt": 1,
    "max_retries": 3,
    "remediation_action": "retry_job",
    "callback_url": "https://your-rca-app.com/api/remediation-callback",
    "timestamp": "2025-12-05T12:00:00Z"
  }'
```

Expected response:
```json
{
  "status": "accepted",
  "message": "Databricks remediation started, will monitor and callback",
  "run_id": "67890",
  "ticket_id": "TEST-001",
  "remediation_action": "retry_job"
}
```

Then after monitoring completes, you'll receive callback:
```json
{
  "ticket_id": "TEST-001",
  "status": "Succeeded",
  "success": true,
  "remediation_run_id": "67890",
  "job_id": "your-job-id",
  "error_type": "DatabricksJobExecutionError",
  "timestamp": "2025-12-05T12:05:00Z"
}
```

### Test 2: Restart Cluster
```bash
curl -X POST https://your-logic-app-url \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": "your-cluster-id",
    "ticket_id": "TEST-002",
    "error_type": "DatabricksClusterStartFailure",
    "retry_attempt": 1,
    "max_retries": 2,
    "remediation_action": "restart_cluster",
    "callback_url": "https://your-rca-app.com/api/remediation-callback",
    "timestamp": "2025-12-05T12:00:00Z"
  }'
```

## 🔍 Monitoring Logic App

View execution history in Azure Portal:
1. Go to Logic App
2. Click "Overview"
3. Scroll to "Run history"
4. Click on any run to see detailed execution

## 🎯 Key Differences from Your Old Logic App

| Feature | Old Logic App | New Logic App |
|---------|--------------|---------------|
| Response | Immediate (sync) | Immediate + callback (async) |
| Monitoring | None | Polls every 30s until complete |
| Callback | None | Calls RCA app when done |
| Retry Logic | None | Handled by RCA app |
| Status Tracking | None | Full status in database |
| Loop Prevention | None | Built into RCA app |

## ⚠️ Important Notes

1. **Callback URL must be publicly accessible** from Azure
2. **Logic App runs for up to 1 hour** monitoring status
3. **RCA app handles retry logic** not the Logic App
4. **Same Logic App** can handle all 3 actions (job/cluster/libraries)
5. **No authentication** on callback (security via secret URL)

## 📊 Complete Flow Example

1. **Databricks job fails** → Azure Monitor alert
2. **RCA app receives webhook** → Checks if auto-remediable
3. **Sends Slack approval** (if high risk) → User clicks approve
4. **Triggers Logic App** with callback URL
5. **Logic App**:
   - Starts job retry
   - Returns run_id immediately
   - Monitors status every 30s
   - Calls back when complete
6. **RCA app receives callback**:
   - If success → Close ticket
   - If failure → Retry (if attempts < max_retries)
   - If max retries → Mark as "Remediation Failed"

## 🔧 Troubleshooting

### Logic App not calling back
- Check callback URL is public
- Check Logic App run history for errors
- Verify network connectivity from Azure

### Job/Cluster not found
- Verify job_id/cluster_id is correct
- Check Databricks token has permissions

### Status stuck in "PENDING"
- Check Databricks workspace is accessible
- Verify token hasn't expired
- Check API rate limits

## 🚀 Next Steps

1. Deploy the Logic App
2. Set environment variables in RCA app
3. Restart RCA app
4. Test with a Databricks failure
5. Check dashboard for remediation status

---

**Created**: 2025-12-05
**Author**: Claude AI Assistant
