"""
DEPRECATED: Monthly reset utility for story usage tracking

This file is deprecated. Credits now reset automatically on subscription renewal
via the Stripe webhook handler (handle_subscription_payment in app/routes/api.py).

DO NOT use this for scheduled resets - credits reset on each user's billing cycle
when their subscription renews (billing_reason == 'subscription_cycle').

This file is kept for reference only and should not be called by any scheduled jobs.
"""
from datetime import date
from app.models import db, User


def reset_monthly_usage():
    """
    DEPRECATED: This function should not be called by scheduled jobs.
    
    Credits now reset automatically on subscription renewal via Stripe webhooks.
    Each user's credits reset on their individual billing cycle date when their
    subscription renews (handled by handle_subscription_payment in api.py).
    
    No scheduled job is needed - the renewal handler implements this logic.
    """
    print("WARNING: reset_monthly_usage() is deprecated.")
    print("Credits reset automatically on subscription renewal via webhooks.")
    print("DO NOT use this function - it will not be executed.")
    return False


if __name__ == "__main__":
    # This should not be run - credits reset on subscription renewal
    print("This script is deprecated. Credits reset on subscription renewal.")
    print("No scheduled job needed.")
