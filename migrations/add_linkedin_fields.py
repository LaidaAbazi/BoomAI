#!/usr/bin/env python3
"""
Database migration script to add LinkedIn integration fields to users table
Supports both SQLite and PostgreSQL databases
"""

import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    """Get database connection based on DATABASE_URL"""
    database_url = os.getenv("DATABASE_URL", "")
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return None, None
    
    # Parse the database URL
    parsed = urlparse(database_url)
    
    if database_url.startswith("sqlite:///"):
        # SQLite database
        import sqlite3
        db_path = database_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            print(f"❌ SQLite database not found at {db_path}")
            return None, None
        conn = sqlite3.connect(db_path)
        return conn, 'sqlite'
    
    elif database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        # PostgreSQL database
        try:
            import psycopg2
        except ImportError:
            print("❌ psycopg2 not installed. Install it with: pip install psycopg2-binary")
            return None, None
        
        try:
            conn = psycopg2.connect(database_url)
            return conn, 'postgresql'
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {str(e)}")
            return None, None
    
    else:
        print(f"❌ Unsupported database URL format: {database_url}")
        return None, None

def get_existing_columns(conn, db_type):
    """Get list of existing columns in users table"""
    cursor = conn.cursor()
    
    if db_type == 'sqlite':
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
    else:  # postgresql
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        columns = {row[0]: row[1] for row in cursor.fetchall()}
    
    return columns

def migrate_database():
    """Add LinkedIn integration fields to the users table"""
    
    conn, db_type = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("🔍 Checking current database schema...")
        
        # Get existing columns
        existing_columns = get_existing_columns(conn, db_type)
        print(f"📋 Current columns in users table: {list(existing_columns.keys())}")
        
        # Define LinkedIn columns to add (PostgreSQL-compatible types)
        if db_type == 'postgresql':
            linkedin_columns = [
                ('linkedin_connected', 'BOOLEAN', 'FALSE'),
                ('linkedin_member_id', 'VARCHAR(100)', None),
                ('linkedin_access_token', 'VARCHAR(500)', None),
                ('linkedin_refresh_token', 'VARCHAR(500)', None),
                ('linkedin_scope', 'VARCHAR(500)', None),
                ('linkedin_name', 'VARCHAR(200)', None),
                ('linkedin_email', 'VARCHAR(255)', None),
                ('linkedin_token_expires_at', 'TIMESTAMP WITH TIME ZONE', None),
                ('linkedin_authed_at', 'TIMESTAMP WITH TIME ZONE', None)
            ]
        else:  # sqlite
            linkedin_columns = [
                ('linkedin_connected', 'BOOLEAN', '0'),
                ('linkedin_member_id', 'VARCHAR(100)', None),
                ('linkedin_access_token', 'VARCHAR(500)', None),
                ('linkedin_refresh_token', 'VARCHAR(500)', None),
                ('linkedin_scope', 'VARCHAR(500)', None),
                ('linkedin_name', 'VARCHAR(200)', None),
                ('linkedin_email', 'VARCHAR(255)', None),
                ('linkedin_token_expires_at', 'DATETIME', None),
                ('linkedin_authed_at', 'DATETIME', None)
            ]
        
        missing_columns = []
        for column_name, column_type, default_value in linkedin_columns:
            if column_name not in existing_columns:
                missing_columns.append((column_name, column_type, default_value))
                print(f"➕ Will add column: {column_name} ({column_type})")
            else:
                print(f"✓ Column already exists: {column_name}")
        
        if not missing_columns:
            print("✅ All LinkedIn columns already exist. No migration needed.")
            conn.close()
            return True
        
        # Add missing columns
        for column_name, column_type, default_value in missing_columns:
            try:
                print(f"➕ Adding column: {column_name}...")
                
                if db_type == 'postgresql':
                    if default_value:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_type} DEFAULT {default_value}')
                    else:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_type}')
                else:  # sqlite
                    if default_value:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_type} DEFAULT {default_value}')
                    else:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_type}')
                
                print(f"✅ Added column: {column_name}")
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    print(f"⚠️  Column {column_name} already exists, skipping...")
                else:
                    print(f"❌ Error adding column {column_name}: {str(e)}")
                    raise
        
        # Commit the changes
        conn.commit()
        
        # Verify the changes
        updated_columns = get_existing_columns(conn, db_type)
        print(f"📋 Updated columns: {list(updated_columns.keys())}")
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("LinkedIn Integration Fields Migration")
    print("=" * 60)
    success = migrate_database()
    sys.exit(0 if success else 1)

