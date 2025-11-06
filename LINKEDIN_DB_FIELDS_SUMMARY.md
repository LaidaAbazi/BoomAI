# LinkedIn Database Fields - Summary

## Overview
Previously, the LinkedIn integration was only storing tokens temporarily in the session and clearing them after posting. This meant users had to re-authenticate every time they wanted to share to LinkedIn. Now, LinkedIn connection data is properly persisted in the database, similar to Slack and Teams integrations.

## New Database Fields Added to User Model

### Connection Status
- **`linkedin_connected`** (Boolean, default=False)
  - Indicates whether the user has connected their LinkedIn account
  - Similar to `slack_connected` and `teams_connected`

### Authentication Data
- **`linkedin_member_id`** (String(100), nullable)
  - LinkedIn Member ID (the "sub" field from OAuth)
  - Required for creating UGC posts on LinkedIn
  - Similar to `slack_user_id` and `teams_user_id`

- **`linkedin_access_token`** (String(500), nullable, encrypted)
  - Encrypted access token for LinkedIn API calls
  - Allows posting without re-authentication
  - Similar to `slack_user_token` and `teams_user_token`

- **`linkedin_refresh_token`** (String(500), nullable, encrypted)
  - Encrypted refresh token (if available from LinkedIn)
  - Can be used to refresh expired access tokens
  - Note: Currently LinkedIn may not provide refresh tokens unless `offline_access` scope is requested

- **`linkedin_scope`** (String(500), nullable)
  - Stores the granted OAuth scopes
  - Current scope: "openid profile w_member_social"
  - Similar to `slack_scope` and `teams_scope`

### User Information
- **`linkedin_name`** (String(200), nullable)
  - LinkedIn display name from user profile
  - Useful for displaying connected account info

- **`linkedin_email`** (String(255), nullable)
  - LinkedIn email (if available from OAuth)
  - May not always be provided depending on user's privacy settings

### Token Management
- **`linkedin_token_expires_at`** (DateTime, nullable)
  - Timestamp when the access token expires
  - Calculated from `expires_in` value from OAuth response
  - Used to check if token refresh is needed

- **`linkedin_authed_at`** (DateTime, nullable)
  - Timestamp when OAuth was completed
  - Useful for tracking when the connection was established
  - Similar to `slack_authed_at` and `teams_authed_at`

## Service Methods Added

### Encryption Methods
- **`encrypt_token(token)`** - Encrypts tokens before storing in database
- **`decrypt_token(encrypted_token)`** - Decrypts stored tokens for use

### Token Management
- **`save_user_token(user_id, token_data, user_info)`** - Saves LinkedIn connection data to database
  - Called automatically during OAuth callback
  - Encrypts tokens before storage
  - Calculates token expiration time

- **`get_user_token(user_id)`** - Retrieves and decrypts access token
  - Checks if token is expired
  - Returns None if token expired or user not connected
  - Can be used for future automatic posting features

- **`disconnect_linkedin(user_id)`** - Removes LinkedIn connection
  - Clears all LinkedIn-related fields
  - Useful for allowing users to disconnect/reconnect

## Benefits

1. **Persistent Connection**: Users don't need to re-authenticate every time
2. **Better UX**: Can check connection status and show connected account info
3. **Token Management**: Track token expiration and handle refresh (future enhancement)
4. **Consistency**: Matches the pattern used by Slack and Teams integrations
5. **Security**: Tokens are encrypted at rest using Fernet encryption

## Database Migration Required

⚠️ **Important**: You'll need to create and run a database migration to add these new columns to the `users` table.

Example migration (using Flask-Migrate):
```bash
flask db migrate -m "Add LinkedIn integration fields to User model"
flask db upgrade
```

Or if using raw SQL (SQLite example):
```sql
ALTER TABLE users ADD COLUMN linkedin_connected BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN linkedin_member_id VARCHAR(100);
ALTER TABLE users ADD COLUMN linkedin_access_token VARCHAR(500);
ALTER TABLE users ADD COLUMN linkedin_refresh_token VARCHAR(500);
ALTER TABLE users ADD COLUMN linkedin_scope VARCHAR(500);
ALTER TABLE users ADD COLUMN linkedin_name VARCHAR(200);
ALTER TABLE users ADD COLUMN linkedin_email VARCHAR(255);
ALTER TABLE users ADD COLUMN linkedin_token_expires_at DATETIME;
ALTER TABLE users ADD COLUMN linkedin_authed_at DATETIME;
```

## Future Enhancements

1. **Token Refresh**: Implement automatic token refresh when expired
2. **Connection Status UI**: Show LinkedIn connection status in user settings
3. **Disconnect Feature**: Allow users to disconnect LinkedIn from settings
4. **Auto-posting**: Use stored tokens for automatic posting without OAuth flow
5. **Multiple Accounts**: Support multiple LinkedIn accounts per user (if needed)

## Environment Variable

Make sure `LINKEDIN_TOKEN_ENCRYPTION_KEY` is set in your environment variables. If not set, a temporary key will be generated (not recommended for production).

