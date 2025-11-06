# LinkedIn OAuth Multi-Host Setup Guide

This guide explains how to set up and use the LinkedIn OAuth integration with support for multiple hosts (localhost, Render, and other external hosts).

## Overview

The implementation follows the standard OAuth 2.0 flow with secure state management:

1. **Front End**: Redirects user to LinkedIn's authorization URL with `client_id`, `redirect_uri`, `scope`, and a generated `state` value
2. **State Storage**: Saves the generated state in the database (not session) along with timestamp, user ID, and redirect URI
3. **LinkedIn Redirect**: LinkedIn sends back the authorization code and the same state to your `redirect_uri`
4. **Back End Validation**: Verifies that the returned state matches the one stored in the database and is still valid (not expired, not used)
5. **Token Exchange**: Exchanges the authorization code for an access token using the same `redirect_uri`
6. **Content Posting**: Uses the access token to perform actions like posting content, fully from the back end

## Key Features

- ✅ **Database-backed state storage** - States are stored in the database, not sessions, enabling multi-host support
- ✅ **CSRF protection** - State validation prevents CSRF attacks
- ✅ **Multi-host support** - Works with localhost, Render, and any other external host
- ✅ **State expiration** - States expire after 10 minutes (configurable)
- ✅ **Replay attack prevention** - States are marked as used after validation
- ✅ **Automatic cleanup** - Utility script to clean up expired states

## Database Setup

### 1. Create the OAuth States Table

Run the migration script to create the `oauth_states` table:

```bash
python migrations/create_oauth_states_table.py
```

This creates a table with the following structure:
- `id` - Primary key
- `state` - Unique state value (indexed)
- `user_id` - Foreign key to users table
- `redirect_uri` - The redirect URI used for this OAuth request
- `content` - Optional content to be posted (stored with state)
- `created_at` - Timestamp when state was created
- `expires_at` - Timestamp when state expires
- `used` - Boolean flag to prevent replay attacks

### 2. Verify the Table

The migration script will output success messages if the table is created correctly.

## Environment Variables

### Required Variables

Set these in your `.env` file or environment:

```bash
# LinkedIn OAuth Credentials
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# Token Encryption Key (generate a secure key)
LINKEDIN_TOKEN_ENCRYPTION_KEY=your_encryption_key_here
```

### Redirect URI Configuration

You can configure multiple redirect URIs in two ways:

#### Option 1: Multiple Redirect URIs (Recommended)

Set `LINKEDIN_REDIRECT_URIS` as a comma-separated list:

```bash
LINKEDIN_REDIRECT_URIS=http://localhost:10000/linkedin/callback,https://your-app.onrender.com/linkedin/callback,https://your-domain.com/linkedin/callback
```

#### Option 2: Single Redirect URI (Backward Compatible)

Set `LINKEDIN_REDIRECT_URI` for a single redirect URI:

```bash
LINKEDIN_REDIRECT_URI=https://your-app.onrender.com/linkedin/callback
```

**Important**: Each redirect URI must be registered in your LinkedIn app settings at [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps).

## LinkedIn App Configuration

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Select your app
3. Go to the "Auth" tab
4. Under "Redirect URLs", add all your redirect URIs:
   - `http://localhost:10000/linkedin/callback` (for local development)
   - `https://your-app.onrender.com/linkedin/callback` (for Render)
   - `https://your-domain.com/linkedin/callback` (for production)
5. Save the changes

## Usage

### Front-End Integration

The front-end should call the `/linkedin/share/init` endpoint to start the OAuth flow:

```javascript
// Example: Initialize LinkedIn OAuth flow
async function initLinkedInShare(content) {
    const response = await fetch('/linkedin/share/init', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${your_jwt_token}` // If using JWT auth
        },
        body: JSON.stringify({ content: content })
    });
    
    const data = await response.json();
    if (data.success) {
        // Redirect user to LinkedIn authorization page
        window.location.href = data.oauth_url;
    } else {
        console.error('Failed to initialize LinkedIn share:', data.error);
    }
}
```

### OAuth Flow

1. **User clicks "Share to LinkedIn"** → Front-end calls `/linkedin/share/init`
2. **Backend generates state** → Stores in database with expiration
3. **User redirected to LinkedIn** → Authorizes the app
4. **LinkedIn redirects back** → To `/linkedin/callback` with `code` and `state`
5. **Backend validates state** → Checks database for valid, non-expired, unused state
6. **Token exchange** → Exchanges code for access token
7. **User redirected to form** → Confirms and posts content

### Backend API Endpoints

#### `POST /linkedin/share/init`

Initializes the OAuth flow. Stores state and content in database.

**Request:**
```json
{
    "content": "Your LinkedIn post content here"
}
```

**Response:**
```json
{
    "success": true,
    "oauth_url": "https://www.linkedin.com/oauth/v2/authorization?..."
}
```

#### `GET /linkedin/callback`

Handles the OAuth callback from LinkedIn. Validates state, exchanges code for token.

**Query Parameters:**
- `code` - Authorization code from LinkedIn
- `state` - State parameter for CSRF protection
- `error` - Error code if authorization failed

**Response:**
- Redirects to `/linkedin/share/form` on success
- Redirects to `/linkedin/share/status?error=...` on failure

#### `GET /linkedin/share/form`

Displays a form for user confirmation before posting.

#### `POST /linkedin/share/post`

Creates the LinkedIn post after user confirmation.

## State Management

### State Lifecycle

1. **Creation**: State is created when `/linkedin/share/init` is called
   - Valid for 10 minutes (configurable)
   - Stored in database with user ID, redirect URI, and content

2. **Validation**: State is validated when `/linkedin/callback` is called
   - Must exist in database
   - Must not be expired
   - Must not be used
   - Must match user ID (if provided)

3. **Marking as Used**: After successful validation, state is marked as used
   - Prevents replay attacks
   - State cannot be reused

### Cleanup

Expired states should be cleaned up periodically. Run the cleanup script:

```bash
python scripts/cleanup_oauth_states.py
```

You can schedule this as a cron job or scheduled task:

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/your/app && python scripts/cleanup_oauth_states.py
```

Or integrate it into your application's scheduled tasks.

## Security Considerations

1. **State Validation**: Never bypass state validation. It's critical for CSRF protection.

2. **State Expiration**: States expire after 10 minutes. Adjust `expiration_minutes` in `create_oauth_state()` if needed.

3. **State Uniqueness**: Each state is unique and can only be used once.

4. **Redirect URI Matching**: The redirect URI used in token exchange must match the one stored with the state.

5. **Token Encryption**: Access tokens are encrypted before storage using Fernet (symmetric encryption).

6. **HTTPS in Production**: Always use HTTPS in production. LinkedIn requires HTTPS for production redirect URIs.

## Troubleshooting

### "Invalid or expired state" Error

- Check that the state hasn't expired (default: 10 minutes)
- Verify the state exists in the database
- Ensure the state hasn't been used already
- Check that the user ID matches

### "Token exchange failed" Error

- Verify the redirect URI matches exactly what was registered in LinkedIn
- Check that the authorization code hasn't expired (usually valid for a few minutes)
- Ensure `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` are correct

### "No redirect URI configured" Error

- Set `LINKEDIN_REDIRECT_URIS` or `LINKEDIN_REDIRECT_URI` environment variable
- Ensure at least one redirect URI is configured

### Redirect URI Mismatch

- Verify all redirect URIs are registered in LinkedIn Developer Portal
- Check that the redirect URI in the request matches exactly (including protocol, host, port, path)
- For localhost, ensure you're using `http://` not `https://`

## Testing

### Local Development

1. Set `LINKEDIN_REDIRECT_URIS` to include `http://localhost:10000/linkedin/callback`
2. Register this URI in LinkedIn Developer Portal
3. Start your app: `python run.py`
4. Test the OAuth flow from `http://localhost:10000`

### Render Deployment

1. Set `LINKEDIN_REDIRECT_URIS` to include `https://your-app.onrender.com/linkedin/callback`
2. Register this URI in LinkedIn Developer Portal
3. Deploy to Render
4. Test the OAuth flow from your Render URL

### Multiple Hosts

The system automatically detects the host from the request and uses the appropriate redirect URI. You can test from multiple hosts as long as:

1. All redirect URIs are registered in LinkedIn Developer Portal
2. All redirect URIs are listed in `LINKEDIN_REDIRECT_URIS`
3. The database is accessible from all hosts (shared database)

## Example Environment Configuration

```bash
# .env file

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_REDIRECT_URIS=http://localhost:10000/linkedin/callback,https://your-app.onrender.com/linkedin/callback,https://your-domain.com/linkedin/callback
LINKEDIN_TOKEN_ENCRYPTION_KEY=your_32_byte_base64_encoded_key_here

# Database
DATABASE_URL=sqlite:///./case_study.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@host:port/database
```

## Migration Checklist

- [ ] Run `python migrations/create_oauth_states_table.py` to create the table
- [ ] Set `LINKEDIN_REDIRECT_URIS` environment variable with all your redirect URIs
- [ ] Register all redirect URIs in LinkedIn Developer Portal
- [ ] Test OAuth flow from localhost
- [ ] Test OAuth flow from Render/production
- [ ] Set up cleanup script as scheduled task
- [ ] Verify token storage and retrieval works correctly

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure database migrations have been run
4. Verify LinkedIn app configuration matches your redirect URIs

