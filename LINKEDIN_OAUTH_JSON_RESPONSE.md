# LinkedIn OAuth - JSON Response Option

## Overview

By default, the LinkedIn OAuth callback redirects users to a status page. You can now request a JSON response instead, allowing your frontend to handle the response programmatically.

## How It Works

### Option 1: Request JSON Response (Recommended)

When initializing the OAuth flow, set `return_format: "json"` in your request. The callback will return JSON instead of redirecting.

**Frontend Request:**
```javascript
const response = await fetch('/linkedin/share/init', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        content: "Your LinkedIn post content",
        return_format: "json"  // Request JSON response
    })
});

const data = await response.json();
if (data.success) {
    // Redirect to LinkedIn
    window.location.href = data.oauth_url;
}
```

**After User Authorizes on LinkedIn:**

The callback will return JSON instead of redirecting:

**Success Response (200 OK):**
```json
{
    "success": true,
    "post_id": "urn:li:ugcPost:1234567890",
    "message": "Post created successfully",
    "linkedin_member_id": "abc123",
    "linkedin_name": "John Doe"
}
```

**Error Response (400/500):**
```json
{
    "success": false,
    "error": "Error message here",
    "status_code": 500  // Only on 500 errors
}
```

### Option 2: Default Redirect (Current Behavior)

If you don't specify `return_format` or set it to `"redirect"`, the callback will redirect to the status page as before.

```javascript
// Default behavior - redirects to status page
const response = await fetch('/linkedin/share/init', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        content: "Your LinkedIn post content"
        // return_format defaults to "redirect"
    })
});
```

## Complete Frontend Implementation (JSON Response)

```javascript
class LinkedInShare {
    /**
     * Share content to LinkedIn with JSON response
     */
    async share(content) {
        try {
            // Initialize OAuth with JSON response format
            const response = await fetch('/linkedin/share/init', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content.trim(),
                    return_format: 'json'  // Request JSON response
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success || !data.oauth_url) {
                throw new Error('Invalid response from server');
            }

            // Open LinkedIn authorization in popup or redirect
            // For popup approach:
            this.openLinkedInAuth(data.oauth_url);
            
            // OR for redirect approach:
            // window.location.href = data.oauth_url;

        } catch (error) {
            console.error('LinkedIn share error:', error);
            this.showError(`Failed to share to LinkedIn: ${error.message}`);
        }
    }

    /**
     * Open LinkedIn auth in popup and listen for callback
     */
    openLinkedInAuth(oauthUrl) {
        // Open popup window
        const popup = window.open(
            oauthUrl,
            'LinkedIn Authorization',
            'width=600,height=700,scrollbars=yes'
        );

        // Listen for callback (polling approach)
        const checkInterval = setInterval(() => {
            try {
                // Check if popup was closed
                if (popup.closed) {
                    clearInterval(checkInterval);
                    return;
                }

                // Try to access popup's location (will fail if cross-origin)
                // This is a limitation - we need a different approach
            } catch (e) {
                // Cross-origin error - popup is on LinkedIn
            }
        }, 500);

        // Alternative: Use postMessage if callback page supports it
    }

    /**
     * Handle callback response (if using redirect approach)
     * This would be called when the callback redirects back to your app
     */
    handleCallback() {
        // Check if we're on the callback page with JSON response
        const urlParams = new URLSearchParams(window.location.search);
        // Note: This won't work with redirect approach since callback returns JSON directly
        // You'd need to use a popup or iframe approach
    }
}
```

## Important Notes

### Using Popup Window Approach

If you want to use JSON responses with a popup window, you'll need to:

1. **Open LinkedIn auth in a popup**
2. **Handle the callback in the popup** - The callback will return JSON
3. **Use postMessage** to send the result back to the parent window

**Example Popup Handler:**
```javascript
// In your callback page (if using popup)
window.addEventListener('message', (event) => {
    if (event.origin !== window.location.origin) return;
    
    // Handle the callback result
    if (event.data.type === 'linkedin_callback') {
        const result = event.data.result;
        if (result.success) {
            this.showSuccess('Post shared successfully!');
        } else {
            this.showError(result.error);
        }
    }
});
```

### Using Redirect Approach

If you use the redirect approach (default), the callback will return JSON, but the browser will try to display it. You may want to:

1. **Create a callback handler page** that receives the JSON and displays it
2. **Use a different redirect URI** for JSON responses
3. **Handle the JSON response** in your frontend router

## Error Handling

All errors return JSON when `return_format: "json"` is set:

**OAuth Errors:**
```json
{
    "success": false,
    "error": "LinkedIn OAuth error: access_denied"
}
```

**Validation Errors:**
```json
{
    "success": false,
    "error": "Invalid or expired OAuth state"
}
```

**Posting Errors:**
```json
{
    "success": false,
    "error": "Failed to create post: ...",
    "status_code": 500
}
```

## Recommendation

- **Use `return_format: "json"`** if you want to handle the response programmatically
- **Use default redirect** if you want the simple status page approach
- **For SPAs**, consider using a popup window with postMessage for better UX

## Technical Details

The `return_format` parameter is added to the redirect URI as a query parameter. LinkedIn should preserve it in the callback. If LinkedIn doesn't preserve it, the system falls back to redirect behavior.

The redirect URI used for token exchange is cleaned (return_format removed) to match LinkedIn's exact requirements.

