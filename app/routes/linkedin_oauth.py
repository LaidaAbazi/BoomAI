from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template, current_app
from app.models import db, User
from app.services.linkedin_oauth_service import LinkedInOAuthService
from app.utils.auth_helpers import get_current_user, login_required, get_current_user_id
from flasgger import swag_from
import secrets
import os

bp = Blueprint('linkedin_oauth', __name__, url_prefix='/linkedin')

@bp.route('/share/init', methods=['POST'])
@swag_from({
    'tags': ['LinkedIn'],
    'summary': 'Initialize LinkedIn sharing flow',
    'description': 'Initialize the LinkedIn OAuth sharing flow. Stores content and state in database and generates OAuth URL for authentication.',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['content'],
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'The LinkedIn post content to share'
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
        400: {'description': 'Content is required'},
        500: {'description': 'Failed to initialize LinkedIn share'}
    }
})
def share_init():
    """
    Initialize LinkedIn sharing flow
    Stores content and state in database (not session) for multi-host support
    """
    try:
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "Content is required"}), 400
        
        user_id = get_current_user_id()
        
        # Determine redirect URI based on request host
        oauth_service = LinkedInOAuthService()
        request_host = request.host
        request_scheme = request.scheme
        redirect_uri = oauth_service.get_redirect_uri_for_host(request_host, request_scheme)
        
        print(f"🌐 Using redirect URI: {redirect_uri} for host: {request_host}")
        
        # Create and store OAuth state in database (with content)
        state = oauth_service.create_oauth_state(
            user_id=user_id,
            redirect_uri=redirect_uri,
            content=content,
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
@swag_from({
    'tags': ['LinkedIn'],
    'summary': 'LinkedIn OAuth callback',
    'description': 'Handle OAuth callback from LinkedIn. Exchanges authorization code for access token, retrieves user info, and redirects to confirmation form.',
    'parameters': [
        {
            'name': 'code',
            'in': 'query',
            'required': False,
            'schema': {'type': 'string'},
            'description': 'Authorization code from LinkedIn OAuth'
        },
        {
            'name': 'state',
            'in': 'query',
            'required': False,
            'schema': {'type': 'string'},
            'description': 'State parameter for CSRF protection'
        },
        {
            'name': 'error',
            'in': 'query',
            'required': False,
            'schema': {'type': 'string'},
            'description': 'Error code if OAuth authorization failed'
        }
    ],
    'responses': {
        302: {
            'description': 'Redirects to share form on success, or status page on error',
            'headers': {
                'Location': {
                    'schema': {'type': 'string'},
                    'description': 'Redirect URL'
                }
            }
        }
    }
})
def callback():
    print("🔐 LinkedIn OAuth callback received")
    """
    Handle OAuth callback from LinkedIn
    Validates state from database, exchanges code for token, gets user info, redirects to form
    """
    try:
        # Get authorization code and state from callback
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            print(f"❌ LinkedIn OAuth error: {error}")
            return redirect(url_for('linkedin_oauth.share_status', error=error))
        
        if not code:
            return redirect(url_for('linkedin_oauth.share_status', error='no_code'))
        
        if not state:
            return redirect(url_for('linkedin_oauth.share_status', error='no_state'))
        
        user_id = get_current_user_id()
        print(f"🔐 User ID: {user_id}")
        print(f"🔐 State received: {state[:10]}...")

        # Validate state parameter from database
        oauth_service = LinkedInOAuthService()
        oauth_state = oauth_service.validate_oauth_state(state, user_id=user_id)
        
        if not oauth_state:
            print(f"⚠️ Invalid or expired state for user {user_id}")
            return redirect(url_for('linkedin_oauth.share_status', error='invalid_state'))
        
        # Get content from stored state
        content = oauth_state.content
        if not content:
            return redirect(url_for('linkedin_oauth.share_status', error='no_content'))
        
        # Get the redirect_uri that was used for this OAuth request
        redirect_uri = oauth_state.redirect_uri
        
        # Exchange code for access token (must use the same redirect_uri)
        token_data = oauth_service.exchange_code_for_token(code, redirect_uri=redirect_uri)
        
        if not token_data:
            return redirect(url_for('linkedin_oauth.share_status', error='token_exchange_failed'))
        
        access_token = token_data.get('access_token')
        
        # Get user info (to get the sub/Member ID)
        user_info = oauth_service.get_user_info(access_token)

        if not user_info or not user_info.get('sub'):
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
            print(f"⚠️ Failed to save LinkedIn token for user {user_id}, continuing with session storage")
            print(f"   This usually means the database columns don't exist yet.")
            print(f"   Please run: python migrations/add_linkedin_fields.py")
        else:
            print(f"✅ Successfully saved LinkedIn token to database for user {user_id}")
        
        # Mark state as used to prevent replay attacks
        oauth_service.mark_state_as_used(state)
        
        # Store token, user info, and content temporarily in session for form confirmation
        session['linkedin_access_token'] = access_token
        session['linkedin_author_id'] = user_info.get('sub')
        session['linkedin_share_content'] = content
        
        # Redirect to form page where user can confirm and post
        return redirect(url_for('linkedin_oauth.share_form'))
            
    except Exception as e:
        print(f"❌ Error in LinkedIn OAuth callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('linkedin_oauth.share_status', error='callback_failed'))

@bp.route('/share/form')
def share_form():
    """
    Display form with prefilled LinkedIn post content for user confirmation
    """
    try:
        content = session.get('linkedin_share_content')
        access_token = session.get('linkedin_access_token')
        author_id = session.get('linkedin_author_id')
        
        if not content:
            return redirect(url_for('linkedin_oauth.share_status', error='no_content'))
        
        if not access_token or not author_id:
            return redirect(url_for('linkedin_oauth.share_status', error='no_token'))
        
        return render_template('linkedin_share_form.html', content=content)
        
    except Exception as e:
        print(f"❌ Error rendering form page: {str(e)}")
        return redirect(url_for('linkedin_oauth.share_status', error='form_error'))

@bp.route('/share/post', methods=['POST'])
@swag_from({
    'tags': ['LinkedIn'],
    'summary': 'Create LinkedIn post',
    'description': 'Create a LinkedIn UGC (User Generated Content) post after user confirmation. Requires valid OAuth session. Returns JSON for API calls, redirects for form submissions.',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'LinkedIn post content (optional, uses session content if not provided)'
                        }
                    }
                }
            },
            'application/x-www-form-urlencoded': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'LinkedIn post content (optional, uses session content if not provided)'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Post created successfully (JSON response for API calls)',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'post_id': {'type': 'string', 'description': 'LinkedIn post ID'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Bad request (JSON response for API calls)',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        },
        500: {
            'description': 'Internal server error (JSON response for API calls)',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        },
        302: {
            'description': 'Redirects to status page (for form submissions)',
            'headers': {
                'Location': {
                    'schema': {'type': 'string'},
                    'description': 'Redirect URL to status page'
                }
            }
        }
    }
})
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

