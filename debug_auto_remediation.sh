#!/bin/bash
# Databricks Auto-Remediation - Debug Checklist
# Run this script to verify your setup is correct

echo "=========================================="
echo "🔍 Databricks Auto-Remediation Debug"
echo "=========================================="
echo ""

# 1. Check if app is running
echo "1️⃣ Checking if application is running..."
APP_PID=$(ps aux | grep "[u]vicorn main:app" | awk '{print $2}')
if [ -z "$APP_PID" ]; then
    echo "   ❌ Application is NOT running"
    echo "   Action: Start the app first"
else
    echo "   ✅ Application is running (PID: $APP_PID)"
    APP_DIR=$(ps aux | grep "[u]vicorn main:app" | awk '{print $11}')
    echo "   Running from: $APP_DIR"
fi
echo ""

# 2. Check for database
echo "2️⃣ Checking for tickets database..."
if [ -f "/home/sigmoid/Documents/LATEST-DEC4/genai_rca_assistant/data/tickets.db" ]; then
    DB_PATH="/home/sigmoid/Documents/LATEST-DEC4/genai_rca_assistant/data/tickets.db"
    echo "   ✅ Found database at: $DB_PATH"
elif [ -f "/home/sigmoid/Documents/LATEST-DEC4/data/tickets.db" ]; then
    DB_PATH="/home/sigmoid/Documents/LATEST-DEC4/data/tickets.db"
    echo "   ✅ Found database at: $DB_PATH"
else
    echo "   ❌ Database not found"
    echo "   Action: Check database location"
fi
echo ""

# 3. Check if column exists (using Python)
echo "3️⃣ Checking if remediation_exhausted_at column exists..."
python3 << 'PYEOF'
import sqlite3
import os

db_paths = [
    "/home/sigmoid/Documents/LATEST-DEC4/genai_rca_assistant/data/tickets.db",
    "/home/sigmoid/Documents/LATEST-DEC4/data/tickets.db",
]

for db_path in db_paths:
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(tickets)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'remediation_exhausted_at' in columns:
                print(f"   ✅ Column exists in {db_path}")
            else:
                print(f"   ❌ Column MISSING in {db_path}")
                print(f"   Action: Run 'python3 add_missing_column.py'")

            conn.close()
            break
        except Exception as e:
            print(f"   ❌ Error checking database: {e}")
PYEOF
echo ""

# 4. Check if code is up to date
echo "4️⃣ Checking if DatabricksTimeoutError is in code..."
if grep -q "DatabricksTimeoutError" /home/sigmoid/Documents/LATEST-DEC4/genai_rca_assistant/main.py 2>/dev/null; then
    echo "   ✅ DatabricksTimeoutError found in REMEDIABLE_ERRORS"
else
    echo "   ❌ DatabricksTimeoutError NOT found in code"
    echo "   Action: Pull latest code from git"
fi
echo ""

# 5. Check recent tickets
echo "5️⃣ Checking recent Databricks tickets..."
python3 << 'PYEOF'
import sqlite3
import os

db_paths = [
    "/home/sigmoid/Documents/LATEST-DEC4/genai_rca_assistant/data/tickets.db",
    "/home/sigmoid/Documents/LATEST-DEC4/data/tickets.db",
]

for db_path in db_paths:
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, pipeline, error_type, remediation_status, timestamp
                FROM tickets
                WHERE id LIKE 'DBX-%'
                ORDER BY timestamp DESC
                LIMIT 3
            """)
            tickets = cursor.fetchall()

            if tickets:
                print(f"   Recent Databricks tickets:")
                for ticket in tickets:
                    print(f"   - {ticket[0]}: {ticket[2]} | Status: {ticket[3]}")
            else:
                print("   ℹ️  No Databricks tickets found yet")

            conn.close()
            break
        except Exception as e:
            print(f"   ⚠️  Could not query tickets: {e}")
PYEOF
echo ""

echo "=========================================="
echo "📋 NEXT STEPS"
echo "=========================================="
echo ""
echo "If you see any ❌ above:"
echo "1. Stop the app (Ctrl+C)"
echo "2. Run: python3 add_missing_column.py"
echo "3. Restart: cd genai_rca_assistant && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo "4. Test Databricks job failure again"
echo ""
echo "Expected flow:"
echo "✅ Databricks job fails"
echo "✅ Webhook → RCA app"
echo "✅ AI marks auto-remediable"
echo "✅ Error type in REMEDIABLE_ERRORS"
echo "✅ Slack approval message appears"
echo "✅ Click [Approve] → Logic App retries"
echo ""
