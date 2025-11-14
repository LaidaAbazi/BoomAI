from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template, current_app
from app.models import db, User
from app.services.linkedin_oauth_service import LinkedInOAuthService
from app.utils.auth_helpers import get_current_user, login_required, get_current_user_id
from flasgger import swag_from
import secrets
import os
from urllib.parse import urlparse

bp = Blueprint('linkedin_oauth', __name__, url_prefix='/linkedin')

# Whitelist of allowed frontend callback URLs
ALLOWED_FRONTEND_URLS = [
    'http://localhost:3000',
    'https://storyboom.ai',
    'https://boomai.onrender.com',
    'http://127.0.0.1:10000',
]

def validate_frontend_callback(url):
    """
    Validate that the frontend callback URL origin is in the whitelist.
    
    Args:
        url: The frontend callback URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return origin in ALLOWED_FRONTEND_URLS
    except Exception as e:
        print(f"❌ Error validating frontend callback URL: {str(e)}")
        return False

@bp.route('/share/init', methods=['POST'])
@swag_from({
    'tags': ['LinkedIn'],
    'summary': 'Initialize LinkedIn sharing flow',
    'description': 'Initialize the LinkedIn OAuth sharing flow. Stores content and state in database and generates OAuth URL for authentication. After OAuth completes, users are redirected to the provided frontend callback URL.',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['content', 'frontend_callback_url'],
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'The LinkedIn post content to share'
                        },
                        'frontend_callback_url': {
                            'type': 'string',
                            'description': 'Frontend URL to redirect to after OAuth completes. Must be from whitelisted origins.'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'OAuth flow initialized successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'oauth_url': {
                                'type': 'string',
                                'description': 'URL to redirect user to for LinkedIn OAuth authentication'
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Content or frontend_callback_url is required, or frontend_callback_url is not whitelisted'},
        500: {'description': 'Failed to initialize LinkedIn share'}
    }
})
def share_init():
    """
    Initialize LinkedIn sharing flow
    Stores content and state in database (not session) for multi-host support
    After OAuth completes, users are redirected to the provided frontend callback URL.
    """
    try:
        data = request.get_json()
        content = data.get('content')
        frontend_callback_url = data.get('frontend_callback_url')
        
        if not content:
            return jsonify({"error": "Content is required"}), 400
        
        if not frontend_callback_url:
            return jsonify({"error": "frontend_callback_url is required"}), 400
        
        # Validate frontend callback URL against whitelist
        if not validate_frontend_callback(frontend_callback_url):
            return jsonify({"error": "frontend_callback_url is not from an allowed origin"}), 400
        
        user_id = get_current_user_id()
        
        # Determine redirect URI based on request host
        oauth_service = LinkedInOAuthService()
        request_host = request.host
        request_scheme = request.scheme
        redirect_uri = oauth_service.get_redirect_uri_for_host(request_host, request_scheme)
        
        print(f"🌐 Using redirect URI: {redirect_uri} for host: {request_host}")
        print(f"🔗 Frontend callback URL: {frontend_callback_url}")
        
        # Create and store OAuth state in database (with content and frontend_callback_url)
        state = oauth_service.create_oauth_state(
            user_id=user_id,
            redirect_uri=redirect_uri,
            content=content,
            frontend_callback_url=frontend_callback_url,
            expiration_minutes=10
        )
        
        if not state:
            return jsonify({"error": "Failed to create OAuth state"}), 500
        
        print(f"🔐 LinkedIn OAuth state generated and stored in DB for user {user_id}: {state[:10]}...")
        
        # Generate OAuth URL with the correct redirect_uri
        oauth_url = oauth_service.get_oauth_url(state=state, redirect_uri=redirect_uri)
        
        return jsonify({
            "success": True,
            "oauth_url": oauth_url
        })
        
    except Exception as e:
        print(f"❌ Error initializing LinkedIn share: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to initialize LinkedIn share"}), 500

@bp.route('/callback', methods=['GET'])
# No Swagger decorator - this is an internal OAuth callback endpoint called by LinkedIn, not by frontend
def callback():
    print("🔐 LinkedIn OAuth callback received")
    """
    Handle OAuth callback from LinkedIn
    Validates state, exchanges code for token, saves token, and automatically posts content to LinkedIn.
    Then redirects to frontend callback URL.
    """
    try:
        # Get authorization code and state from callback
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        user_id = get_current_user_id()
        print(f"🔐 User ID: {user_id}")
        
        if error:
            print(f"❌ LinkedIn OAuth error: {error}")
            # Try to get frontend_callback_url from state if available
            frontend_callback_url = None
            if state:
                try:
                    oauth_service = LinkedInOAuthService()
                    oauth_state = oauth_service.validate_oauth_state(state, user_id=user_id)
                    if oauth_state:
                        frontend_callback_url = oauth_state.frontend_callback_url
                except:
                    pass
            if frontend_callback_url:
                from urllib.parse import urlencode
                error_params = urlencode({'error': error}, doseq=True)
                return redirect(f"{frontend_callback_url}?{error_params}")
            return redirect(url_for('linkedin_oauth.share_status', error=error))
        
        if not code:
            # Try to get frontend_callback_url from state if available
            frontend_callback_url = None
            if state:
                try:
                    oauth_service = LinkedInOAuthService()
                    oauth_state = oauth_service.validate_oauth_state(state, user_id=user_id)
                    if oauth_state:
                        frontend_callback_url = oauth_state.frontend_callback_url
                except:
                    pass
            if frontend_callback_url:
                return redirect(f"{frontend_callback_url}?error=no_code")
            return redirect(url_for('linkedin_oauth.share_status', error='no_code'))
        
        if not state:
            return redirect(url_for('linkedin_oauth.share_status', error='no_state'))
        
        print(f"🔐 State received: {state[:10]}...")
        
        # Validate state parameter from database to get frontend_callback_url
        oauth_service = LinkedInOAuthService()
        oauth_state = oauth_service.validate_oauth_state(state, user_id=user_id)
        
        # Get frontend callback URL from oauth_state (fallback to error if not available)
        frontend_callback_url = oauth_state.frontend_callback_url if oauth_state else None
        
        if not oauth_state:
            print(f"⚠️ Invalid or expired state for user {user_id}")
            if frontend_callback_url:
                return redirect(f"{frontend_callback_url}?error=invalid_state")
            return redirect(url_for('linkedin_oauth.share_status', error='invalid_state'))
        
        # Get content from stored state
        content = oauth_state.content
        if not content:
            if frontend_callback_url:
                return redirect(f"{frontend_callback_url}?error=no_content")
            return redirect(url_for('linkedin_oauth.share_status', error='no_content'))
        
        # Get frontend callback URL from stored state
        if not frontend_callback_url:
            print(f"⚠️ No frontend_callback_url in OAuth state, falling back to status page")
            frontend_callback_url = None
        
        # Get the redirect_uri that was used for this OAuth request
        redirect_uri = oauth_state.redirect_uri
        
        # Exchange code for access token
        token_data = oauth_service.exchange_code_for_token(code, redirect_uri=redirect_uri)
        
        if not token_data:
            if frontend_callback_url:
                return redirect(f"{frontend_callback_url}?error=token_exchange_failed")
            return redirect(url_for('linkedin_oauth.share_status', error='token_exchange_failed'))
        
        access_token = token_data.get('access_token')
        
        # Get user info (to get the sub/Member ID)
        user_info = oauth_service.get_user_info(access_token)

        if not user_info or not user_info.get('sub'):
            if frontend_callback_url:
                return redirect(f"{frontend_callback_url}?error=user_info_failed")
            return redirect(url_for('linkedin_oauth.share_status', error='user_info_failed'))
        
        print(f"📝 LinkedIn OAuth data received for user {user_id}:")
        print(f"   - Member ID: {user_info.get('sub')}")
        print(f"   - Name: {user_info.get('name', 'N/A')}")
        print(f"   - Email: {user_info.get('email', 'N/A')}")
        print(f"   - Token expires in: {token_data.get('expires_in', 'N/A')} seconds")
        print(f"   - Scope: {token_data.get('scope', 'N/A')}")
        
        # Save token and user info to database
        print(f"💾 Attempting to save LinkedIn token to database for user {user_id}...")
        save_success = oauth_service.save_user_token(
            user_id=user_id,
            token_data=token_data,
            user_info=user_info
        )
        
        if not save_success:
            print(f"⚠️ Failed to save LinkedIn token for user {user_id}, continuing...")
            print(f"   This usually means the database columns don't exist yet.")
            print(f"   Please run: python migrations/add_linkedin_fields.py")
        else:
            print(f"✅ Successfully saved LinkedIn token to database for user {user_id}")
        
        # Mark state as used to prevent replay attacks
        oauth_service.mark_state_as_used(state)
        
        # AUTOMATICALLY POST THE CONTENT (no preview needed)
        author_id = user_info.get('sub')
        print(f"📤 Automatically posting content to LinkedIn for user {user_id}...")
        post_result = oauth_service.create_ugc_post(access_token, author_id, content)
        
        # Redirect to frontend callback URL
        if post_result.get('success'):
            print(f"✅ LinkedIn post created successfully: {post_result.get('post_id')}")
            if frontend_callback_url:
                from urllib.parse import urlencode
                post_id = post_result.get('post_id', '')
                success_params = urlencode({'success': 'true', 'post_id': post_id}, doseq=True)
                return redirect(f"{frontend_callback_url}?{success_params}")
            return redirect(url_for('linkedin_oauth.share_status', success=True))
        else:
            error_msg = post_result.get('error', 'Unknown error')
            print(f"❌ Failed to create LinkedIn post: {error_msg}")
            if frontend_callback_url:
                from urllib.parse import urlencode
                error_params = urlencode({'error': 'post_failed', 'details': error_msg}, doseq=True)
                return redirect(f"{frontend_callback_url}?{error_params}")
            return redirect(url_for('linkedin_oauth.share_status', error='post_failed', details=error_msg))
            
    except Exception as e:
        print(f"❌ Error in LinkedIn OAuth callback: {str(e)}")
        import traceback
        traceback.print_exc()
        # Try to get frontend_callback_url from state if available
        try:
            state = request.args.get('state')
            if state:
                oauth_service = LinkedInOAuthService()
                oauth_state = oauth_service.validate_oauth_state(state, user_id=get_current_user_id())
                if oauth_state and oauth_state.frontend_callback_url:
                    from urllib.parse import urlencode
                    error_params = urlencode({'error': 'callback_failed', 'details': str(e)}, doseq=True)
                    return redirect(f"{oauth_state.frontend_callback_url}?{error_params}")
        except:
            pass
        return redirect(url_for('linkedin_oauth.share_status', error='callback_failed'))

@bp.route('/share/form')
# No Swagger decorator - this endpoint is deprecated (preview form no longer used)
# Kept for backward compatibility, but redirects to status page
def share_form():
    """
    Deprecated: Preview form endpoint (no longer used)
    Auto-posting happens in callback, so this redirects to status page
    """
    return redirect(url_for('linkedin_oauth.share_status', error='form_deprecated'))

@bp.route('/share/post', methods=['POST'])
# No Swagger decorator - this endpoint is deprecated (auto-posting happens in callback)
# Kept for backward compatibility, but posts are now created automatically in /callback
def share_post():
    """
    Create the LinkedIn post after user confirmation
    Returns JSON for API calls, redirects for form submissions
    """
    try:
        user_id = get_current_user_id()
        
        # Check if this is an API request (JSON content type or Accept header)
        is_api_request = (
            request.is_json or 
            request.content_type == 'application/json' or
            request.headers.get('Accept', '').find('application/json') != -1
        )
        
        # Get content from JSON body, form, or session
        if request.is_json:
            data = request.get_json() or {}
            content = data.get('content') or session.get('linkedin_share_content')
        else:
            content = request.form.get('content') or session.get('linkedin_share_content')
        
        access_token = session.get('linkedin_access_token')
        author_id = session.get('linkedin_author_id')
        
        if not content:
            if is_api_request:
                return jsonify({
                    "success": False,
                    "error": "Content is required"
                }), 400
            return redirect(url_for('linkedin_oauth.share_status', error='no_content'))
        
        if not access_token or not author_id:
            if is_api_request:
                return jsonify({
                    "success": False,
                    "error": "OAuth session expired or invalid. Please re-authenticate."
                }), 401
            return redirect(url_for('linkedin_oauth.share_status', error='no_token'))
        
        # Create the UGC post
        oauth_service = LinkedInOAuthService()
        post_result = oauth_service.create_ugc_post(access_token, author_id, content)
        
        # Clear all session data
        session.pop('linkedin_share_content', None)
        session.pop('linkedin_access_token', None)
        session.pop('linkedin_author_id', None)
        
        # Return JSON for API requests, redirect for form submissions
        if is_api_request:
            if post_result.get('success'):
                return jsonify({
                    "success": True,
                    "post_id": post_result.get('post_id'),
                    "message": post_result.get('message', 'Post created successfully')
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": post_result.get('error', 'Unknown error'),
                    "status_code": post_result.get('status_code')
                }), 500
        else:
            # Form submission - redirect to status page
            if post_result.get('success'):
                return redirect(url_for('linkedin_oauth.share_status', success=True))
            else:
                error_msg = post_result.get('error', 'Unknown error')
                return redirect(url_for('linkedin_oauth.share_status', error='post_failed', details=error_msg))
            
    except Exception as e:
        print(f"❌ Error creating LinkedIn post: {str(e)}")
        # Check if API request to return JSON error
        is_api_request = (
            request.is_json or 
            request.content_type == 'application/json' or
            request.headers.get('Accept', '').find('application/json') != -1
        )
        
        if is_api_request:
            return jsonify({
                "success": False,
                "error": f"Error creating LinkedIn post: {str(e)}"
            }), 500
        return redirect(url_for('linkedin_oauth.share_status', error='post_error'))

@bp.route('/share/status')
def share_status():
    """
    Display success or error status page after LinkedIn sharing attempt
    """
    try:
        success = request.args.get('success') == 'True'
        error = request.args.get('error')
        details = request.args.get('details', '')
        
        return render_template('linkedin_share_status.html', 
                             success=success, 
                             error=error, 
                             details=details)
        
    except Exception as e:
        print(f"❌ Error rendering status page: {str(e)}")
        return render_template('linkedin_share_status.html', 
                             success=False, 
                             error='unknown_error')

