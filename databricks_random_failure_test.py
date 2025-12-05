"""
Databricks Auto-Remediation Test - Random Failure
This script randomly fails 70% of the time, so retries will eventually succeed

Perfect for testing:
1. Initial failure → webhook → Slack approval
2. Retry 1 (70% chance fails) → webhook → cooldown check
3. Retry 2 (70% chance fails) → webhook → cooldown check
4. Eventually passes → auto-remediation successful ✅

HOW TO USE:
1. Paste this code in a Databricks notebook
2. Run it - it will likely fail (70% chance)
3. Check Slack for approval message
4. Click [Approve] button
5. Logic App retries the job
6. It might fail again (70% chance) or succeed (30% chance)
7. Keep retrying until it passes!
"""

import random
import time
from datetime import datetime

def random_databricks_job():
    """
    Simulates a Databricks job that randomly fails
    Failure rate: 70% (random > 0.7 means pass)
    """

    print("=" * 60)
    print(f"🚀 Starting Databricks Job at {datetime.now()}")
    print("=" * 60)

    # Generate random number between 0 and 1
    random_value = random.random()

    print(f"📊 Random value: {random_value:.4f}")
    print(f"✅ Success threshold: > 0.7")

    # Simulate some processing time
    time.sleep(2)

    if random_value > 0.7:
        # SUCCESS CASE (30% chance)
        print("=" * 60)
        print("✅ SUCCESS! Job completed successfully!")
        print(f"🎉 Random value {random_value:.4f} > 0.7")
        print("=" * 60)
        return True
    else:
        # FAILURE CASE (70% chance)
        print("=" * 60)
        print("❌ FAILURE! Job failed!")
        print(f"💥 Random value {random_value:.4f} <= 0.7")
        print("=" * 60)

        # Randomly choose which type of error to raise
        error_type = random.choice([
            "library",
            "timeout",
            "execution"
        ])

        if error_type == "library":
            raise ImportError(
                f"DatabricksLibraryInstallationError: Failed to install library 'random-lib-{int(random_value*1000)}'. "
                f"This is a transient error that can be fixed by reinstalling libraries. "
                f"Random value: {random_value:.4f}"
            )
        elif error_type == "timeout":
            raise TimeoutError(
                f"DatabricksTimeoutError: Job execution timed out after {int(random_value*100)} seconds. "
                f"This is a transient network/resource issue. Retry should resolve it. "
                f"Random value: {random_value:.4f}"
            )
        else:
            raise RuntimeError(
                f"DatabricksJobExecutionError: Spark executor failed with code {int(random_value*1000)}. "
                f"This is a transient cluster resource issue. Retry should resolve it. "
                f"Random value: {random_value:.4f}"
            )


# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    try:
        random_databricks_job()
    except Exception as e:
        print(f"\n🔥 Exception caught: {type(e).__name__}")
        print(f"📝 Message: {str(e)}")
        # Re-raise to trigger Databricks failure and webhook
        raise


# ========================================
# COPY THIS TO DATABRICKS NOTEBOOK
# ========================================

"""
PASTE THIS IN YOUR DATABRICKS NOTEBOOK:

-----------------------------------------------------------
import random
import time
from datetime import datetime

print(f"🚀 Starting Random Failure Test at {datetime.now()}")

# Generate random number (70% chance of failure)
random_value = random.random()
print(f"📊 Random value: {random_value:.4f} (success if > 0.7)")

time.sleep(2)

if random_value > 0.7:
    print("✅ SUCCESS! Job completed!")
else:
    print("❌ FAILURE! Raising error...")
    error_types = [
        ("ImportError", f"DatabricksLibraryInstallationError: Failed to install library. Random: {random_value:.4f}"),
        ("TimeoutError", f"DatabricksTimeoutError: Job timed out. Random: {random_value:.4f}"),
        ("RuntimeError", f"DatabricksJobExecutionError: Executor failed. Random: {random_value:.4f}")
    ]
    error_type, error_msg = random.choice(error_types)

    if error_type == "ImportError":
        raise ImportError(error_msg)
    elif error_type == "TimeoutError":
        raise TimeoutError(error_msg)
    else:
        raise RuntimeError(error_msg)
-----------------------------------------------------------

EXPECTED BEHAVIOR:

Run 1 (70% chance):
  ❌ Fails → Triggers webhook → AI marks auto-remediable → Slack approval message

Click [Approve] in Slack:
  → Logic App retries the job

Run 2 (70% chance):
  ❌ Might fail again → Webhook → Cooldown check → Waits

Run 3 (70% chance):
  ✅ Likely succeeds! → Logic App callback → Ticket marked resolved

After 3-4 retries, statistically should pass (0.7^4 = 24% chance of 4 failures)

This tests:
- ✅ Random failure triggering webhook
- ✅ AI correctly marking as auto-remediable
- ✅ Slack approval flow
- ✅ Logic App retry mechanism
- ✅ Loop prevention (cooldown between retries)
- ✅ Eventually successful remediation
"""
