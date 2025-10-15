#!/usr/bin/env python3
"""
Database migration script to add the missing slack_connected column
"""

import sqlite3
import os

def migrate_database():
    """Add the missing slack_connected column to the users table"""
    
    # Get the database path
    db_path = os.path.join('instance', 'case_study.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking current database schema...")
        
        # Check if the slack_connected column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"📋 Current columns: {columns}")
        
        # Check if slack_connected column exists
        if 'slack_connected' not in columns:
            print("➕ Adding missing slack_connected column...")
            cursor.execute("ALTER TABLE users ADD COLUMN slack_connected BOOLEAN DEFAULT 0")
            print("✅ Added slack_connected column")
        else:
            print("✅ slack_connected column already exists")
        
        # Also check for other missing Slack columns
        missing_columns = []
        expected_slack_columns = [
            ('slack_user_id', 'TEXT'),
            ('slack_user_token', 'TEXT'),
            ('slack_team_id', 'TEXT'),
            ('slack_scope', 'TEXT'),
            ('slack_authed_at', 'DATETIME')
        ]
        
        for column_name, column_type in expected_slack_columns:
            if column_name not in columns:
                missing_columns.append((column_name, column_type))
        
        # Add any other missing Slack columns
        for column_name, column_type in missing_columns:
            print(f"➕ Adding missing {column_name} column...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
            print(f"✅ Added {column_name} column")
        
        # Commit the changes
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Updated columns: {updated_columns}")
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting Slack columns database migration...")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("\n📝 Added/verified columns:")
        print("- slack_connected: Boolean flag for Slack connection status")
        print("- slack_user_id: Slack user identifier")
        print("- slack_user_token: Encrypted Slack user token")
        print("- slack_team_id: Slack workspace/team ID")
        print("- slack_scope: Granted OAuth scopes")
        print("- slack_authed_at: OAuth completion timestamp")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above.")
    
    print("\n" + "=" * 60) 