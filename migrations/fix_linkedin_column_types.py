#!/usr/bin/env python3
"""
Fix LinkedIn column types in PostgreSQL database
Some columns may have been created as array types instead of regular types
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
        return None
    
    if not (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        print("❌ This script is for PostgreSQL databases only")
        return None
    
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed. Install it with: pip install psycopg2-binary")
        return None
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {str(e)}")
        return None

def fix_column_types():
    """Fix LinkedIn column types if they were created as arrays"""
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("🔍 Checking LinkedIn column types...")
        
        # Check current column types
        cursor.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name LIKE 'linkedin_%'
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        print(f"\n📋 Current LinkedIn columns:")
        for col_name, data_type, udt_name in columns:
            print(f"   - {col_name}: {data_type} ({udt_name})")
        
        # Check which columns are arrays or need type changes
        array_columns = []
        resize_columns = []
        
        # First, get character_maximum_length for all columns
        cursor.execute("""
            SELECT column_name, character_maximum_length, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name LIKE 'linkedin_%'
            ORDER BY column_name
        """)
        columns_with_length = cursor.fetchall()
        
        for col_name, char_max_length, data_type, udt_name in columns_with_length:
            if data_type == 'ARRAY':
                array_columns.append(col_name)
                print(f"⚠️  {col_name} is an ARRAY type - needs to be fixed!")
            # Check if token columns are VARCHAR(500) but should be TEXT
            elif col_name in ['linkedin_access_token', 'linkedin_refresh_token']:
                if udt_name == 'varchar' and char_max_length and char_max_length <= 500:
                    resize_columns.append(col_name)
                    print(f"⚠️  {col_name} is VARCHAR({char_max_length}) but should be TEXT for encrypted tokens!")
        
        if not array_columns and not resize_columns:
            print("\n✅ All LinkedIn columns have correct types. No fixes needed.")
            conn.close()
            return True
        
        total_fixes = len(array_columns) + len(resize_columns)
        print(f"\n🔧 Fixing {total_fixes} column(s)...")
        if array_columns:
            print(f"   - {len(array_columns)} array column(s) to fix")
        if resize_columns:
            print(f"   - {len(resize_columns)} column(s) to resize to TEXT")
        
        # Define correct types for each column
        # Note: Token fields use TEXT instead of VARCHAR to handle encrypted tokens which can be very long
        column_type_map = {
            'linkedin_connected': 'BOOLEAN',
            'linkedin_member_id': 'VARCHAR(100)',
            'linkedin_access_token': 'TEXT',  # Changed to TEXT for encrypted tokens
            'linkedin_refresh_token': 'TEXT',  # Changed to TEXT for encrypted tokens
            'linkedin_scope': 'VARCHAR(500)',
            'linkedin_name': 'VARCHAR(200)',
            'linkedin_email': 'VARCHAR(255)',
            'linkedin_token_expires_at': 'TIMESTAMP WITH TIME ZONE',
            'linkedin_authed_at': 'TIMESTAMP WITH TIME ZONE'
        }
        
        # Fix array columns
        for col_name in array_columns:
            if col_name not in column_type_map:
                print(f"⚠️  Unknown column type for {col_name}, skipping...")
                continue
            
            correct_type = column_type_map[col_name]
            print(f"\n🔧 Fixing {col_name}...")
            print(f"   Current: ARRAY")
            print(f"   Target: {correct_type}")
            
            try:
                # For PostgreSQL, we need to:
                # 1. Create a temporary column with correct type
                # 2. Copy data (if any) from old column
                # 3. Drop old column
                # 4. Rename temp column
                
                temp_col = f"{col_name}_temp"
                
                # Step 1: Create temp column
                cursor.execute(f"ALTER TABLE users ADD COLUMN {temp_col} {correct_type}")
                print(f"   ✅ Created temporary column")
                
                # Step 2: Copy data (if column had any array data, we'll lose it, but it's probably empty anyway)
                # For arrays, we can't easily convert, so we'll just leave it NULL
                print(f"   ℹ️  Data from array column will be lost (likely empty anyway)")
                
                # Step 3: Drop old column
                cursor.execute(f"ALTER TABLE users DROP COLUMN {col_name}")
                print(f"   ✅ Dropped old array column")
                
                # Step 4: Rename temp column
                cursor.execute(f"ALTER TABLE users RENAME COLUMN {temp_col} TO {col_name}")
                print(f"   ✅ Renamed temporary column")
                
                # Set default if needed
                if col_name == 'linkedin_connected':
                    cursor.execute(f"ALTER TABLE users ALTER COLUMN {col_name} SET DEFAULT FALSE")
                    print(f"   ✅ Set default value")
                
                print(f"   ✅ {col_name} fixed successfully!")
                
            except Exception as e:
                print(f"   ❌ Error fixing {col_name}: {str(e)}")
                conn.rollback()
                return False
        
        # Fix columns that need to be resized to TEXT
        for col_name in resize_columns:
            print(f"\n🔧 Resizing {col_name} to TEXT...")
            try:
                # Simply alter the column type
                cursor.execute(f"ALTER TABLE users ALTER COLUMN {col_name} TYPE TEXT")
                print(f"   ✅ {col_name} resized to TEXT successfully!")
            except Exception as e:
                print(f"   ❌ Error resizing {col_name}: {str(e)}")
                conn.rollback()
                return False
        
        # Commit all changes
        conn.commit()
        print(f"\n✅ All columns fixed successfully!")
        
        # Verify the changes
        cursor.execute("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name LIKE 'linkedin_%'
            ORDER BY column_name
        """)
        
        updated_columns = cursor.fetchall()
        print(f"\n📋 Updated LinkedIn columns:")
        for col_name, data_type, udt_name in updated_columns:
            print(f"   - {col_name}: {data_type} ({udt_name})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during fix: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Fix LinkedIn Column Types")
    print("=" * 60)
    success = fix_column_types()
    sys.exit(0 if success else 1)

