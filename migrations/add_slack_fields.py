#!/usr/bin/env python3
"""
Database migration script to add new Slack integration fields
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add new Slack fields to the users table"""
    
    # Get the database path
    db_path = os.path.join('instance', 'case_study.db')
    
    if not os.path.exists(db_path):
        print(f" Database not found at {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(" Checking current database schema...")
        
        # Check if the new columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns: {columns}")
        
        # Add new columns if they don't exist
        new_columns = [
            ('slack_team_id', 'TEXT'),
            ('slack_scope', 'TEXT'),
            ('slack_authed_at', 'DATETIME')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f" Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                print(f" Added column: {column_name}")
            else:
                print(f" Column already exists: {column_name}")
        
        # Commit the changes
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"Updated columns: {updated_columns}")
        
        print(" Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f" Error during migration: {str(e)}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print(" Starting Slack fields database migration...")
    print("=" * 50)
    
    success = migrate_database()
    
    if success:
        print("\n Migration completed successfully!")
        print("\nNew fields added:")
        print("- slack_team_id: Store Slack workspace/team ID")
        print("- slack_scope: Store granted OAuth scopes")
        print("- slack_authed_at: Store OAuth completion timestamp")
    else:
        print("\n Migration failed!")
        print("Please check the error messages above.")
    
    print("\n" + "=" * 50) 