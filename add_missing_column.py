#!/usr/bin/env python3
"""
Quick script to add missing remediation_exhausted_at column to tickets table
Run this from any location - it will find and update the database
"""
import sqlite3
import os
import sys

# Possible database locations
possible_paths = [
    '/home/sigmoid/Documents/LATEST-DEC4/tickets.db',
    '/home/sigmoid/Documents/LATEST-DEC4/genai_rca_assistant/data/tickets.db',
    '/home/sigmoid/Documents/LATEST-DEC4/data/tickets.db',
    '/home/sigmoid/Documents/balaji-aiops-project/data/tickets.db',
    '/home/sigmoid/Documents/balaji-aiops-project/genai_rca_assistant/data/tickets.db',
    'tickets.db',
    'data/tickets.db',
]

db_path = None
for path in possible_paths:
    if os.path.exists(path):
        # Check if it has tables
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets';")
            if cursor.fetchone():
                db_path = path
                conn.close()
                break
            conn.close()
        except:
            continue

if not db_path:
    print("❌ ERROR: Could not find tickets database with tickets table!")
    print("\nSearched locations:")
    for path in possible_paths:
        print(f"  - {path}")
    sys.exit(1)

print(f"✅ Found database at: {db_path}\n")

# Connect and add column
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current columns
cursor.execute('PRAGMA table_info(tickets)')
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

print(f"Current columns ({len(column_names)}):")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Add missing column if needed
if 'remediation_exhausted_at' not in column_names:
    print("\n🔧 Adding remediation_exhausted_at column...")
    try:
        cursor.execute('ALTER TABLE tickets ADD COLUMN remediation_exhausted_at TEXT;')
        conn.commit()
        print("✅ Column added successfully!")

        # Verify
        cursor.execute('PRAGMA table_info(tickets)')
        new_columns = [col[1] for col in cursor.fetchall()]
        if 'remediation_exhausted_at' in new_columns:
            print("✅ Verified: Column exists in database")
        else:
            print("❌ ERROR: Column not found after adding!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR adding column: {e}")
        sys.exit(1)
else:
    print("\nℹ️  Column 'remediation_exhausted_at' already exists - no action needed")

conn.close()
print("\n✅ Database update complete!")
