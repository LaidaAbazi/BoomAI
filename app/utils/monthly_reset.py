"""
Monthly reset utility for story usage tracking
"""
from datetime import date
from app.models import db, User


def reset_monthly_usage():
    """
    Reset monthly story usage for all users
    This should be called by a scheduled job (cron, celery, etc.)
    """
    try:
        users = User.query.all()
        reset_count = 0
        
        for user in users:
            # Only reset if it's a new month
            if user.last_reset_date is None or user.last_reset_date.month != date.today().month:
                user.reset_monthly_usage()
                reset_count += 1
        
        db.session.commit()
        print(f"Monthly reset completed. Reset {reset_count} users.")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during monthly reset: {str(e)}")
        return False


if __name__ == "__main__":
    # This can be run directly for testing
    reset_monthly_usage()
