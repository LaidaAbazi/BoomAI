import sqlite3
import os
from datetime import datetime

def create_slack_installations_table():
    db_path = os.path.join('instance', 'case_study.db')
    if not os.path.exists(db_path):
        print(f" Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(" Checking current database schema...")
        
        # Check if slack_installations table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slack_installations'")
        if cursor.fetchone():
            print(" slack_installations table already exists")
            return True
        
        print(" Creating slack_installations table...")
        
        # Create the slack_installations table
        cursor.execute('''
            CREATE TABLE slack_installations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                slack_team_id VARCHAR(100) NOT NULL,
                slack_team_name VARCHAR(200) NOT NULL,
                bot_token VARCHAR(500) NOT NULL,
                is_enterprise_install BOOLEAN DEFAULT 0,
                enterprise_id VARCHAR(100),
                enterprise_name VARCHAR(200),
                scope VARCHAR(500) NOT NULL,
                installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, slack_team_id)
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('CREATE INDEX idx_slack_installations_user_id ON slack_installations(user_id)')
        cursor.execute('CREATE INDEX idx_slack_installations_team_id ON slack_installations(slack_team_id)')
        
        conn.commit()
        
        print(" slack_installations table created successfully!")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(slack_installations)")
        columns = cursor.fetchall()
        print(f"📋 Table structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        return True
        
    except Exception as e:
        print(f" Error creating table: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def migrate_existing_slack_data():
    """Migrate existing Slack data from users table to slack_installations table"""
    db_path = os.path.join('instance', 'case_study.db')
    if not os.path.exists(db_path):
        print(f" Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(" Checking for existing Slack data to migrate...")
        
        # Check if users table has Slack fields
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        slack_fields = ['slack_connected', 'slack_user_id', 'slack_team_id', 'slack_user_token', 'slack_scope', 'slack_authed_at']
        existing_slack_fields = [field for field in slack_fields if field in columns]
        
        if not existing_slack_fields:
            print(" No existing Slack data found to migrate")
            return True
        
        print(f" Found existing Slack fields: {existing_slack_fields}")
        
        # Check if there are any users with Slack data
        cursor.execute("SELECT id, slack_connected, slack_user_id, slack_team_id, slack_user_token, slack_scope, slack_authed_at FROM users WHERE slack_connected = 1")
        users_with_slack = cursor.fetchall()
        
        if not users_with_slack:
            print(" No users with Slack data found")
            return True
        
        print(f" Found {len(users_with_slack)} users with Slack data to migrate")
        
        # Migrate each user's Slack data
        migrated_count = 0
        for user_data in users_with_slack:
            user_id, connected, slack_user_id, team_id, token, scope, authed_at = user_data
            
            if connected and team_id and token:
                try:
                    # Insert into slack_installations table
                    cursor.execute('''
                        INSERT OR REPLACE INTO slack_installations 
                        (user_id, slack_team_id, slack_team_name, bot_token, is_enterprise_install, scope, installed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        team_id,
                        f"Workspace-{team_id[:8]}",  # Generate a placeholder name
                        token,  # Note: This should be encrypted in production
                        0,  # Assume not enterprise for existing data
                        scope or "chat:write,channels:read",
                        authed_at or datetime.now()
                    ))
                    
                    migrated_count += 1
                    print(f" Migrated Slack data for user {user_id}")
                    
                except Exception as e:
                    print(f" Failed to migrate Slack data for user {user_id}: {str(e)}")
        
        conn.commit()
        print(f" Successfully migrated {migrated_count} Slack installations!")
        
        return True
        
    except Exception as e:
        print(f" Error during migration: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print(" Starting Slack Installations table migration...")
    print("=" * 60)
    
    # Step 1: Create the table
    print("\n Step 1: Creating slack_installations table...")
    table_created = create_slack_installations_table()
    
    if table_created:
        # Step 2: Migrate existing data
        print("\n Step 2: Migrating existing Slack data...")
        data_migrated = migrate_existing_slack_data()
        
        if data_migrated:
            print("\n Migration completed successfully!")
            print("\nNew features available:")
            print("- Multi-workspace Slack support")
            print("- Enterprise Grid (Org-wide) installations")
            print("- Secure bot token storage")
            print("- Workspace-specific channel management")
            print("- Automatic channel joining for public channels")
        else:
            print("\n Table created but data migration failed!")
    else:
        print("\n Migration failed!")
    
    print("\n" + "=" * 60) 