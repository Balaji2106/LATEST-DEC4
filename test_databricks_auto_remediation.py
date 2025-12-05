"""
Databricks Auto-Remediation Test Scripts
Run these in Databricks notebooks to trigger auto-remediable errors
"""

# TEST 1: Library Installation Error (Most Common)
# This will fail because the library doesn't exist
# Should trigger: is_auto_remediable=true, action=reinstall_libraries
def test_library_error():
    """
    Paste this in a Databricks notebook cell and run
    """
    import fake_nonexistent_library_xyz_12345
    print("This won't print")


# TEST 2: Timeout Error (Network/Resource)
# This will timeout and should be auto-remediable
# Should trigger: is_auto_remediable=true, action=retry_job
def test_timeout_error():
    """
    Paste this in a Databricks notebook cell and run
    """
    import time
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()

    # Force a timeout by reading from a slow/non-existent endpoint
    df = spark.read.format("jdbc").options(
        url="jdbc:sqlserver://fake-server-that-does-not-exist-12345.database.windows.net:1433",
        dbtable="nonexistent_table",
        user="fake_user",
        password="fake_password",
        driver="com.microsoft.sqlserver.jdbc.SQLServerDriver"
    ).load()

    df.show()


# TEST 3: Job Execution Error (Transient Spark Failure)
# Should trigger: is_auto_remediable=true, action=retry_job
def test_execution_error():
    """
    Paste this in a Databricks notebook cell and run
    """
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()

    # Create a scenario that causes executor failure
    # Force divide by zero in distributed computation
    df = spark.range(0, 1000000)
    df = df.withColumn("result", 10 / (df.id % 0))  # Will fail with division by zero
    df.collect()


# EASIEST TEST: Simple Library Import Failure
print("""
=============================================================
EASIEST AUTO-REMEDIATION TEST FOR DATABRICKS
=============================================================

Copy and paste this into a Databricks notebook cell:

-----------------------------------------------------------
# Auto-Remediation Test: Library Installation Error
import nonexistent_library_xyz_12345_test_auto_remediation

print("If you see this, something went wrong!")
-----------------------------------------------------------

This will:
1. ✅ Fail with ModuleNotFoundError (simulates DatabricksLibraryInstallationError)
2. ✅ Trigger webhook to RCA app
3. ✅ AI should mark as is_auto_remediable=true
4. ✅ Send Slack approval message with buttons
5. ✅ After approval → trigger Logic App to reinstall_libraries

Expected Slack Message:
🔴 *Auto-Remediation Required* (Pending Approval)
Pipeline: your_databricks_job_name
Error: DatabricksLibraryInstallationError
Action: reinstall_libraries
Risk: Medium
[Approve] [Reject]

=============================================================
""")


# Alternative: Timeout Test (takes longer, 30 seconds)
print("""
=============================================================
ALTERNATIVE TEST: Timeout Error (Slower but Realistic)
=============================================================

Copy and paste this into a Databricks notebook cell:

-----------------------------------------------------------
# Auto-Remediation Test: Timeout Error
import time
import requests

# Force a connection timeout
try:
    response = requests.get(
        "http://fake-server-12345.database.windows.net:9999",
        timeout=30
    )
except Exception as e:
    raise TimeoutError(f"Databricks job timed out: {e}")
-----------------------------------------------------------

This will:
1. ✅ Fail with TimeoutError after 30 seconds
2. ✅ Trigger webhook to RCA app
3. ✅ AI should mark as is_auto_remediable=true
4. ✅ Send Slack approval message
5. ✅ After approval → trigger Logic App to retry_job

=============================================================
""")
