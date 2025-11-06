#!/usr/bin/env python3
"""
Quick fix for LinkedIn token columns - change from VARCHAR(500) to TEXT
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def fix_token_columns():
    """Change linkedin_access_token and linkedin_refresh_token to TEXT"""
    
    database_url = os.getenv("DATABASE_URL", "")
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    if not (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        print("❌ This script is for PostgreSQL databases only")
        return False
    
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed. Install it with: pip install psycopg2-binary")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔧 Fixing LinkedIn token columns...")
        
        # Fix access_token
        try:
            print("   Fixing linkedin_access_token...")
            cursor.execute("ALTER TABLE users ALTER COLUMN linkedin_access_token TYPE TEXT")
            print("   ✅ linkedin_access_token changed to TEXT")
        except Exception as e:
            print(f"   ⚠️  Error fixing linkedin_access_token: {str(e)}")
            # Continue anyway
        
        # Fix refresh_token
        try:
            print("   Fixing linkedin_refresh_token...")
            cursor.execute("ALTER TABLE users ALTER COLUMN linkedin_refresh_token TYPE TEXT")
            print("   ✅ linkedin_refresh_token changed to TEXT")
        except Exception as e:
            print(f"   ⚠️  Error fixing linkedin_refresh_token: {str(e)}")
            # Continue anyway
        
        conn.commit()
        print("\n✅ Token columns fixed successfully!")
        
        # Verify
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('linkedin_access_token', 'linkedin_refresh_token')
        """)
        
        results = cursor.fetchall()
        print("\n📋 Updated columns:")
        for col_name, data_type, max_length in results:
            print(f"   - {col_name}: {data_type} (max_length: {max_length})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Fix LinkedIn Token Column Sizes")
    print("=" * 60)
    success = fix_token_columns()
    sys.exit(0 if success else 1)

