#!/usr/bin/env python3
"""
Database connection test script for debugging deployment issues
"""
import os
import sys
from app import create_app, db
from app.models import User

def test_database():
    """Test database connection and table creation"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== Database Connection Test ===")
            
            # Test 1: Basic connection
            print("1. Testing basic database connection...")
            from sqlalchemy import text
            result = db.session.execute(text("SELECT 1"))
            print(f"   ✓ Connection successful: {result.fetchone()}")
            
            # Test 2: Check if tables exist
            print("2. Checking existing tables...")
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   ✓ Found tables: {tables}")
            
            # Test 3: Check if users table exists and has correct structure
            print("3. Checking users table structure...")
            if 'users' in tables:
                columns = inspector.get_columns('users')
                print(f"   ✓ Users table columns: {[col['name'] for col in columns]}")
            else:
                print("   ✗ Users table not found!")
            
            # Test 4: Try to create tables
            print("4. Attempting to create tables...")
            db.create_all()
            print("   ✓ Tables created/verified successfully")
            
            # Test 5: Check tables again after creation
            print("5. Checking tables after creation...")
            inspector = inspect(db.engine)
            tables_after = inspector.get_table_names()
            print(f"   ✓ Tables after creation: {tables_after}")
            
            # Test 6: Try to query users table
            print("6. Testing user query...")
            user_count = User.query.count()
            print(f"   ✓ User count: {user_count}")
            
            # Test 7: Try to create a test user
            print("7. Testing user creation...")
            from werkzeug.security import generate_password_hash
            test_user = User(
                first_name="Test",
                last_name="User",
                email="test@example.com",
                password_hash=generate_password_hash("testpassword123")
            )
            db.session.add(test_user)
            db.session.commit()
            print("   ✓ Test user created successfully")
            
            # Clean up test user
            db.session.delete(test_user)
            db.session.commit()
            print("   ✓ Test user cleaned up")
            
            print("\n=== All tests passed! ===")
            return True
            
        except Exception as e:
            print(f"\n=== Test failed! ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}")
            return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1) 