#!/usr/bin/env python3
"""
Database initialization script for Render deployment
"""
import os
import sys
from app import create_app, db
from app.models import User, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken, Label, Feedback

def init_database():
    """Initialize the database and create all tables"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Checking database connection...")
            # Test database connection
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            print("✓ Database connection successful")
            
            print("Creating database tables...")
            # Create all tables
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Verify tables exist
            tables = db.engine.table_names()
            print(f"✓ Available tables: {', '.join(tables)}")
            
            return True
            
        except Exception as e:
            print(f"✗ Database initialization failed: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1) 