#!/usr/bin/env python3
"""
Database migration script to add frontend_callback_url column to oauth_states table
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
    
    # Handle Render's PostgreSQL URL format
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
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
    
    elif database_url.startswith("postgresql://"):
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

def table_exists(conn, db_type, table_name):
    """Check if a table exists"""
    cursor = conn.cursor()
    
    if db_type == 'sqlite':
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    else:  # postgresql
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        return cursor.fetchone()[0]

def get_existing_columns(conn, db_type, table_name):
    """Get list of existing columns in the specified table"""
    cursor = conn.cursor()
    
    if db_type == 'sqlite':
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
    else:  # postgresql
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
        """, (table_name,))
        columns = {row[0]: row[1] for row in cursor.fetchall()}
    
    return columns

def migrate_database():
    """Add frontend_callback_url column to oauth_states table"""
    
    conn, db_type = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("🔍 Checking if oauth_states table exists...")
        
        if not table_exists(conn, db_type, 'oauth_states'):
            print("❌ oauth_states table does not exist. Please run create_oauth_states_table.py first.")
            conn.close()
            return False
        
        print("🔍 Checking current database schema...")
        
        # Get existing columns
        existing_columns = get_existing_columns(conn, db_type, 'oauth_states')
        print(f"📋 Current columns in oauth_states table: {list(existing_columns.keys())}")
        
        # Check if frontend_callback_url column already exists
        if 'frontend_callback_url' in existing_columns:
            print("✅ frontend_callback_url column already exists. No migration needed.")
            conn.close()
            return True
        
        # Add the frontend_callback_url column
        print("➕ Adding frontend_callback_url column...")
        
        try:
            if db_type == 'postgresql':
                cursor.execute('ALTER TABLE oauth_states ADD COLUMN frontend_callback_url VARCHAR(500)')
            else:  # sqlite
                cursor.execute('ALTER TABLE oauth_states ADD COLUMN frontend_callback_url VARCHAR(500)')
            
            print("✅ Added column: frontend_callback_url")
        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                print("⚠️  Column frontend_callback_url already exists, skipping...")
            else:
                print(f"❌ Error adding column frontend_callback_url: {str(e)}")
                raise
        
        # Commit the changes
        conn.commit()
        
        # Verify the changes
        updated_columns = get_existing_columns(conn, db_type, 'oauth_states')
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
    print("Add frontend_callback_url to oauth_states Table Migration")
    print("=" * 60)
    success = migrate_database()
    sys.exit(0 if success else 1)

