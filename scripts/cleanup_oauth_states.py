#!/usr/bin/env python3
"""
Utility script to clean up expired OAuth states from the database.
This should be run periodically (e.g., via a cron job or scheduled task).
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app import create_app
from app.models import db
from app.services.linkedin_oauth_service import LinkedInOAuthService

def cleanup_states():
    """Clean up expired OAuth states"""
    app = create_app()
    
    with app.app_context():
        oauth_service = LinkedInOAuthService()
        deleted_count = oauth_service.cleanup_expired_states(older_than_hours=24)
        
        print(f"✅ Cleanup completed. Deleted {deleted_count} expired OAuth states.")
        return deleted_count

if __name__ == "__main__":
    print("=" * 60)
    print("OAuth States Cleanup Script")
    print("=" * 60)
    try:
        deleted = cleanup_states()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

