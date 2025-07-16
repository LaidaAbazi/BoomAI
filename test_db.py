#!/usr/bin/env python3
"""
Simple database test script
"""
import os
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def test_database():
    """Test database connection and User model"""
    app = create_app()
    
    with app.app_context():
        try:
            # Test database connection
            print("Testing database connection...")
            with db.engine.connect() as conn:
                conn.execute(db.text("SELECT 1"))
            print("✅ Database connection successful")
            
            # Test User model creation
            print("Testing User model creation...")
            test_user = User(
                first_name="Test",
                last_name="User",
                email="test@example.com",
                password_hash=generate_password_hash("password123"),
                company_name="Test Company",
                is_verified=False
            )
            
            db.session.add(test_user)
            db.session.commit()
            print("✅ User creation successful")
            
            # Test User query
            user = User.query.filter_by(email="test@example.com").first()
            if user:
                print(f"✅ User query successful: {user.first_name} {user.last_name}")
            else:
                print("❌ User query failed")
            
            # Clean up
            db.session.delete(test_user)
            db.session.commit()
            print("✅ Test user cleaned up")
            
        except Exception as e:
            print(f"❌ Database test failed: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_database() 