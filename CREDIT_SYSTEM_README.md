# Story Credit System Implementation

This document describes the implementation of the story credit system for tracking user story usage and managing extra credits.

## Overview

The system enforces subscription requirements and tracks:
- **Subscription requirement**: Users must have active subscription to access any features
- Monthly story allowance (10 stories per month for $99/month plan)
- Extra story credits ($6.90 per story)
- Monthly reset functionality

## Database Changes

### New User Model Fields
- `stories_used_this_month`: Integer, tracks stories used in current month
- `extra_credits`: Integer, tracks purchased extra credits
- `last_reset_date`: Date, tracks when monthly usage was last reset
- `has_active_subscription`: Boolean, tracks if user has active monthly subscription
- `subscription_start_date`: Date, tracks when subscription was activated

### Migration
Run the migration to add the new fields:
```bash
# The migration file is located at:
migrations/versions/add_story_tracking_fields.py
```

## API Endpoints

### 1. Stripe Webhook
**POST** `/api/stripe/webhook`

Handles Stripe webhook events for automatic payment processing.

**Events Handled:**
- `checkout.session.completed`: Processes successful payments
- `invoice.payment_succeeded`: Handles recurring subscription payments

**Metadata Required:**
- `user_id`: User ID for tracking
- `payment_type`: "subscription" or "extra_credits"
- `quantity`: Number of extra credits (for extra_credits type)

### 2. Get Credit Status
**GET** `/api/credits/status`

Get current credit status for authenticated user.

**Response:**
```json
{
  "stories_used_this_month": 3,
  "extra_credits": 5,
  "can_create_story": true,
  "can_buy_extra_credits": false,
  "needs_subscription": false,
  "has_active_subscription": true,
  "stories_remaining": 7,
  "last_reset_date": "2025-01-01"
}
```

## User Model Methods

### `can_create_story()`
Returns `True` if user has active subscription and credits available.

### `can_buy_extra_credits()`
Returns `True` if user has used all 10 monthly stories and can purchase extra credits.

### `needs_subscription()`
Returns `True` if user needs to subscribe to monthly plan.

### `record_story_creation()`
Records story creation and updates counters:
- Uses monthly allowance first (if < 10 stories used)
- Uses extra credits if monthly allowance exhausted
- Raises `ValueError` if no credits available

### `add_extra_credits(quantity)`
Adds extra story credits to user account.

### `reset_monthly_usage()`
Resets monthly story usage (called by scheduled job).

## Frontend Integration

### Subscription Wall
- **Route**: `/subscription-required`
- **Template**: `templates/subscription_wall.html`
- **Purpose**: Shows when user doesn't have active subscription
- **Features**: Beautiful landing page with pricing and features

### Credit Status Banner
- Shows when user cannot create stories
- Displays remaining credits
- Links to Stripe Payment Link for extra credits

### Story Creation Flow
- "TELL THE STORY" button checks subscription and credits
- User completes the solution provider interview
- Credit is consumed when solution provider interview is saved (story fully generated)
- If no subscription or credits available, user gets appropriate error message

### Access Control
- **Dashboard**: Redirects to subscription wall if no active subscription
- **API Routes**: All major routes require active subscription
- **Error Handling**: Graceful redirects to subscription wall

## Configuration

### Environment Variables
Add to your `.env` file:
```env
# Stripe webhook configuration
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
```

### Stripe Webhook Setup
1. **Go to Stripe Dashboard** → Webhooks
2. **Add endpoint:** `https://yourapp.com/api/stripe/webhook`
3. **Select events:** `checkout.session.completed`, `invoice.payment_succeeded`
4. **Copy webhook secret** to your `.env` file
5. **Configure Payment Links** with metadata:
   - `user_id`: User ID for tracking
   - `payment_type`: "subscription" or "extra_credits"
   - `quantity`: Number of extra credits (for extra_credits type)

### Stripe Payment Links
Update the Stripe Payment Link URLs in your templates:
```javascript
// Replace these URLs with your actual Stripe Payment Links
const baseUrl = 'https://buy.stripe.com/your-payment-link';
const metadata = `?prefilled_data[metadata][user_id]=${userId}&prefilled_data[metadata][payment_type]=subscription`;
```

## Monthly Reset

### Manual Reset
```python
from app.utils.monthly_reset import reset_monthly_usage
reset_monthly_usage()
```

### Scheduled Reset
Set up a cron job or scheduled task to run monthly:
```bash
# Example cron job (runs on 1st of each month at midnight)
0 0 1 * * /path/to/python /path/to/app/utils/monthly_reset.py
```

## Testing

### Test Stripe Webhook
```bash
# Test webhook endpoint (requires Stripe CLI for local testing)
stripe listen --forward-to localhost:10000/api/stripe/webhook
```

### Test Credit Status
```bash
curl -X GET http://localhost:10000/api/credits/status \
  -H "Authorization: Bearer your-jwt-token"
```

### Test Payment Links
1. **Monthly Subscription**: Click "Monthly Plan" button in dashboard
2. **Extra Credits**: Click "Buy Extra Stories" button in dashboard
3. **Check webhook logs** for successful processing

## Security Notes

- Stripe webhook signature verification required
- User authentication required for status endpoint
- All database operations are wrapped in transactions
- Input validation on all endpoints
- Webhook events are processed securely with proper error handling

## Error Handling

- Graceful error messages for insufficient credits
- Database rollback on errors
- Proper HTTP status codes
- Frontend alerts for user feedback
