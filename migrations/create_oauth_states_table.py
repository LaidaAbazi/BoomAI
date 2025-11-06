#!/usr/bin/env python3
"""
Database migration script to create oauth_states table for OAuth state management
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

def migrate_database():
    """Create oauth_states table if it doesn't exist"""
    
    conn, db_type = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("🔍 Checking if oauth_states table exists...")
        
        if table_exists(conn, db_type, 'oauth_states'):
            print("✅ oauth_states table already exists. No migration needed.")
            conn.close()
            return True
        
        print("➕ Creating oauth_states table...")
        
        if db_type == 'postgresql':
            # PostgreSQL table creation
            cursor.execute("""
                CREATE TABLE oauth_states (
                    id SERIAL PRIMARY KEY,
                    state VARCHAR(255) NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    redirect_uri VARCHAR(500) NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    CONSTRAINT fk_oauth_states_user 
                        FOREIGN KEY (user_id) 
                        REFERENCES users(id) 
                        ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_oauth_states_state ON oauth_states(state)")
            cursor.execute("CREATE INDEX idx_oauth_states_user_id ON oauth_states(user_id)")
            cursor.execute("CREATE INDEX idx_oauth_states_expires_at ON oauth_states(expires_at)")
            
        else:  # sqlite
            # SQLite table creation
            cursor.execute("""
                CREATE TABLE oauth_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state VARCHAR(255) NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    redirect_uri VARCHAR(500) NOT NULL,
                    content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    used BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_oauth_states_state ON oauth_states(state)")
            cursor.execute("CREATE INDEX idx_oauth_states_user_id ON oauth_states(user_id)")
            cursor.execute("CREATE INDEX idx_oauth_states_expires_at ON oauth_states(expires_at)")
        
        # Commit the changes
        conn.commit()
        
        print("✅ oauth_states table created successfully!")
        print("✅ Indexes created successfully!")
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
    print("OAuth States Table Migration")
    print("=" * 60)
    success = migrate_database()
    sys.exit(0 if success else 1)

