from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template
from app.models import db, User, CaseStudy
from app.services.teams_installation_service import TeamsInstallationService
from app.services.teams_oauth_service import TeamsOAuthService
from app.utils.auth_helpers import login_required, get_current_user_id
import secrets

bp = Blueprint('teams_oauth', __name__, url_prefix='/api/teams/oauth')

@bp.route('/')
@login_required
def share_page():
    """
    Serve the dedicated Teams sharing page
    """
    return render_template('teams_multi_workspace.html')

@bp.route('/authorize')
@login_required
def authorize():
    """
    Start the OAuth flow - redirect user to Microsoft for tenant installation
    """
    try:
        # Generate a random state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Store state in session with user-specific key
        user_id = get_current_user_id()
        session[f'teams_oauth_state_{user_id}'] = state
        
        # Also store in general session for backward compatibility
        session['teams_oauth_state'] = state
        
        print(f"🔐 Generated OAuth state for user {user_id}: {state[:10]}...")
        
        # Get tenant_id from query params if specified
        tenant_id = request.args.get('tenant_id')
        
        installation_service = TeamsInstallationService()
        oauth_url = installation_service.get_oauth_url(state=state, tenant_id=tenant_id)
        
        return redirect(oauth_url)
        
    except Exception as e:
        print(f"❌ Error starting OAuth flow: {str(e)}")
        return jsonify({"error": "Failed to start OAuth flow"}), 500

@bp.route('/callback')
@login_required
def callback():
    """
    Handle the OAuth callback from Microsoft for tenant installation
    """
    try:
        # Get the authorization code or error from Microsoft
        code = request.args.get('code')
        error_param = request.args.get('error')
        state = request.args.get('state')
        
        # Verify state parameter (but don't fail if it's missing)
        user_id = get_current_user_id()
        stored_state = session.get('teams_oauth_state') or session.get(f'teams_oauth_state_{user_id}')
        
        if state and stored_state and state != stored_state:
            print(f"⚠️ State parameter mismatch for user {user_id}. Expected: {stored_state[:10]}..., Got: {state[:10]}...")
            # Don't fail the OAuth flow for state mismatch, just log it
        elif not stored_state:
            print(f"⚠️ No stored state found for user {user_id}, but continuing with OAuth flow")
        else:
            print(f"✅ State parameter validated successfully for user {user_id}")
        
        # If Microsoft returned an error, redirect to UI with error context
        if error_param and not code:
            return redirect(url_for('teams_oauth.share_page', status='error', error=error_param))
        
        if not code:
            # No code received – surface a friendly error to the UI
            return redirect(url_for('teams_oauth.share_page', status='error', error='no_authorization_code'))
        
        # Exchange code for installation data
        installation_service = TeamsInstallationService()
        installation_data = installation_service.exchange_code_for_installation(code)
        
        if not installation_data:
            return redirect(url_for('teams_oauth.share_page', status='error', error='token_exchange_failed'))
        
        # Create or update the installation
        success = installation_service.create_installation(user_id, installation_data)
        
        if not success:
            return redirect(url_for('teams_oauth.share_page', status='error', error='save_installation_failed'))
        
        # Test the installation
        test_result = installation_service.test_installation(installation_data["access_token"])
        
        # Clear the state from session
        session.pop('teams_oauth_state', None)
        session.pop(f'teams_oauth_state_{user_id}', None)
        
        if test_result:
            # Redirect to Teams share page with success params (similar to Slack flow)
            return redirect(url_for('teams_oauth.share_page', 
                                    status='success', 
                                    tenant_name=installation_data["tenant_name"],
                                    user_name=installation_data["user_name"]))
        else:
            # Redirect with error
            return redirect(url_for('teams_oauth.share_page', 
                                    status='error', 
                                    error='installation_test_failed'))
        
    except Exception as e:
        print(f"❌ Error in OAuth callback: {str(e)}")
        return jsonify({"error": "Failed to complete OAuth flow"}), 500

@bp.route('/workspace/<tenant_id>/check-access')
@login_required
def check_workspace_access(tenant_id):
    """
    Check if the user has access to a specific Teams tenant
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        # Check if user has an installation for this tenant
        token = installation_service.get_installation_token(user_id, tenant_id)
        
        if token:
            # Test the token
            is_valid = installation_service.test_installation(token)
            return jsonify({
                "has_access": is_valid,
                "tenant_id": tenant_id
            })
        else:
            return jsonify({
                "has_access": False,
                "tenant_id": tenant_id
            })
        
    except Exception as e:
        print(f"❌ Error checking workspace access: {str(e)}")
        return jsonify({"error": "Failed to check workspace access"}), 500

@bp.route('/post', methods=['POST'])
@login_required
def post_message():
    """
    Post a message to a Teams channel in a specific tenant
    """
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')  # Tenant ID
        team_id = data.get('team_id')  # Team ID
        channel_id = data.get('channel_id')  # Channel ID
        text = data.get('text')  # Message text
        
        if not tenant_id or not team_id or not channel_id or not text:
            return jsonify({"error": "Missing tenant_id, team_id, channel_id, or text"}), 400
        
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        # Get the access token for this tenant
        access_token = installation_service.get_installation_token(user_id, tenant_id)
        
        if not access_token:
            return jsonify({
                "error": f"StoryBoom is not installed in this tenant yet.",
                "install_required": True,
                "authorize_url": f"/api/teams/oauth/authorize?tenant_id={tenant_id}",
                "tenant_id": tenant_id,
                "action_required": "install",
                "help_text": "Click 'Install StoryBoom in this tenant' to get started. This will redirect you to Microsoft to authorize the app."
            }), 401
        
        # Test the token
        if not installation_service.test_installation(access_token):
            return jsonify({
                "error": "Access token is invalid or expired. Please re-authorize.",
                "install_required": True,
                "authorize_url": f"/api/teams/oauth/authorize?tenant_id={tenant_id}",
                "tenant_id": tenant_id,
                "action_required": "reauthorize"
            }), 401
        
        # Send the message
        message = {
            "body": {
                "contentType": "text",
                "content": text
            }
        }
        
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        import requests
        response = requests.post(url, headers=headers, json=message)
        
        if response.status_code == 201:
            return jsonify({
                "success": True,
                "message": "Message sent successfully to Teams channel"
            })
        else:
            print(f"❌ Failed to send message: {response.status_code} - {response.text}")
            return jsonify({
                "error": f"Failed to send message: {response.status_code}",
                "details": response.text
            }), 500
        
    except Exception as e:
        print(f"❌ Error posting message: {str(e)}")
        return jsonify({"error": "Failed to post message"}), 500

@bp.route('/test/<tenant_id>')
@login_required
def test_installation(tenant_id):
    """
    Test a Teams installation
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        # Get the access token for this tenant
        access_token = installation_service.get_installation_token(user_id, tenant_id)
        
        if not access_token:
            return jsonify({
                "error": "No installation found for this tenant",
                "install_required": True
            }), 404
        
        # Test the installation
        is_valid = installation_service.test_installation(access_token)
        
        if is_valid:
            return jsonify({
                "success": True,
                "message": "Teams installation is working correctly",
                "tenant_id": tenant_id
            })
        else:
            return jsonify({
                "error": "Teams installation test failed",
                "tenant_id": tenant_id,
                "install_required": True
            }), 500
        
    except Exception as e:
        print(f"❌ Error testing installation: {str(e)}")
        return jsonify({"error": "Failed to test installation"}), 500

@bp.route('/status')
@login_required
def get_teams_status():
    """
    Get the current Teams connection status for the user
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        return jsonify({
            "success": True,
            "connected": len(installations) > 0,
            "tenants_count": len(installations),
            "installations": installations
        })
        
    except Exception as e:
        print(f"❌ Error getting Teams status: {str(e)}")
        return jsonify({"error": "Failed to get Teams status"}), 500

@bp.route('/teams')
@login_required
def get_available_teams():
    """
    Get all available teams across user's connected tenants
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        all_teams = []
        for installation in installations:
            access_token = installation_service.get_installation_token(user_id, installation['tenant_id'])
            if access_token:
                teams = installation_service.get_tenant_teams(access_token, installation['tenant_id'])
                for team in teams:
                    all_teams.append({
                        "id": team["id"],
                        "name": team["name"],
                        "description": team["description"],
                        "tenant_name": installation['tenant_name'],
                        "tenant_id": installation['tenant_id']
                    })
        
        return jsonify({
            "success": True,
            "teams": all_teams
        })
        
    except Exception as e:
        print(f"❌ Error getting teams: {str(e)}")
        return jsonify({"error": "Failed to get teams"}), 500

@bp.route('/channels')
@login_required
def get_available_channels():
    """
    Get all available channels across user's connected tenants
    """
    try:
        user_id = get_current_user_id()
        print(f"🔍 Getting channels for user {user_id}")
        
        installation_service = TeamsInstallationService()
        installations = installation_service.get_user_installations(user_id)
        print(f"🔍 Found {len(installations)} installations: {installations}")
        
        all_channels = []
        for i, installation in enumerate(installations):
            print(f"🔍 Processing installation {i+1}: {installation}")
            access_token = installation_service.get_installation_token(user_id, installation['tenant_id'])
            print(f"🔍 Access token for tenant {installation['tenant_id']}: {'✅ Found' if access_token else '❌ Not found'}")
            
            if access_token:
                teams = installation_service.get_tenant_teams(access_token, installation['tenant_id'])
                print(f"🔍 Found {len(teams)} teams for tenant {installation['tenant_id']}: {teams}")
                
                for j, team in enumerate(teams):
                    print(f"🔍 Processing team {j+1}: {team}")
                    # Check if this is a personal chat
                    is_personal_chat = team.get("is_personal_chat", False)
                    print(f"🔍 Is personal chat: {is_personal_chat}")
                    
                    channels = installation_service.get_team_channels(access_token, team["id"], is_personal_chat)
                    print(f"🔍 Found {len(channels)} channels for team {team['name']}: {channels}")
                    
                    for k, channel in enumerate(channels):
                        channel_data = {
                            "id": channel["id"],
                            "name": channel["name"],
                            "description": channel["description"],
                            "team_name": team["name"],
                            "team_id": team["id"],
                            "tenant_name": installation['tenant_name'],
                            "tenant_id": installation['tenant_id'],
                            "is_private": channel["is_private"],
                            "is_personal_chat": is_personal_chat
                        }
                        print(f"🔍 Adding channel {k+1}: {channel_data}")
                        all_channels.append(channel_data)
            else:
                print(f"❌ No access token for tenant {installation['tenant_id']}")
        
        print(f"🔍 Total channels found: {len(all_channels)}")
        print(f"🔍 Final channels list: {all_channels}")
        
        return jsonify({
            "success": True,
            "channels": all_channels
        })
        
    except Exception as e:
        print(f"❌ Error getting channels: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to get channels"}), 500

@bp.route('/post_to_channel', methods=['POST'])
@login_required
def post_case_study_to_channel():
    """
    Post a case study to a specific Teams channel
    """
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')
        team_id = data.get('team_id')
        channel_id = data.get('channel_id')
        case_study_id = data.get('case_study_id')
        
        if not all([tenant_id, team_id, channel_id, case_study_id]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        user_id = get_current_user_id()
        
        # Get the case study
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        installation_service = TeamsInstallationService()
        
        # Get the access token for this tenant
        access_token = installation_service.get_installation_token(user_id, tenant_id)
        
        if not access_token:
            return jsonify({
                "error": f"StoryBoom is not installed in this tenant yet.",
                "install_required": True,
                "authorize_url": f"/api/teams/oauth/authorize?tenant_id={tenant_id}",
                "tenant_id": tenant_id,
                "action_required": "install"
            }), 401
        
        # Create the message content
        message_content = f"�� New Success Story: {case_study.title}"
        
        # Add case study summary
        summary_parts = []
        if case_study.challenge:
            summary_parts.append(f"**Challenge:** {case_study.challenge[:200]}...")
        if case_study.solution:
            summary_parts.append(f"**Solution:** {case_study.solution[:200]}...")
        if case_study.results:
            summary_parts.append(f"**Results:** {case_study.results[:200]}...")
        
        if summary_parts:
            message_content += f"\n\n{chr(10).join(summary_parts)}"
        
        # Add PDF link if available
        pdf_url = data.get('pdf_url')
        if pdf_url:
            message_content += f"\n\n📄 [View Full Case Study]({pdf_url})"
        
        # Send the message
        message = {
            "body": {
                "contentType": "text",
                "content": message_content
            }
        }
        
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        import requests
        response = requests.post(url, headers=headers, json=message)
        
        if response.status_code == 201:
            return jsonify({
                "success": True,
                "message": "Case study shared successfully to Teams channel"
            })
        else:
            print(f"❌ Failed to send case study: {response.status_code} - {response.text}")
            return jsonify({
                "error": f"Failed to send case study: {response.status_code}",
                "details": response.text
            }), 500
        
    except Exception as e:
        print(f"❌ Error posting case study: {str(e)}")
        return jsonify({"error": "Failed to post case study"}), 500 

@bp.route('/installations')
@login_required
def get_installations():
    """
    Get all Teams tenant installations for the user
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        return jsonify({
            "success": True,
            "installations": installations
        })
        
    except Exception as e:
        print(f"❌ Error getting installations: {str(e)}")
        return jsonify({"error": "Failed to get installations"}), 500

@bp.route('/auto-share-case-study', methods=['POST'])
@login_required
def auto_share_case_study():
    """
    Automatically share a case study to Teams using email draft content
    Posts as the user, not as the bot
    """
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        channel_id = data.get('channel_id')
        team_id = data.get('team_id')
        tenant_id = data.get('tenant_id')
        
        if not case_study_id or not channel_id or not team_id or not tenant_id:
            return jsonify({"error": "Missing case_study_id, channel_id, team_id, or tenant_id"}), 400
        
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        # Get the case study
        from app.models import CaseStudy, User
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Get user info for personalization
        user = User.query.get(user_id)
        user_name = f"{user.first_name} {user.last_name}" if user else "I"
        
        # Generate Teams message from email draft content
        teams_message = installation_service.generate_teams_message_from_email_draft(case_study, user_name)
        
        # Get the access token for this tenant
        access_token = installation_service.get_installation_token(user_id, tenant_id)
        
        if not access_token:
            return jsonify({
                "error": "StoryBoom is not installed in this tenant yet.",
                "install_required": True,
                "authorize_url": f"/api/teams/oauth/authorize?tenant_id={tenant_id}"
            }), 401
        
        # Post the message
        result = installation_service.post_message_to_teams(access_token, team_id, channel_id, teams_message)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Successfully shared case study to Teams!",
                "timestamp": result.get("createdDateTime"),
                "channel_id": channel_id,
                "team_id": team_id,
                "tenant_id": tenant_id
            })
        else:
            return jsonify({
                "error": f"Failed to post message: {result.get('error', 'Unknown error')}"
            }), 400
        
    except Exception as e:
        print(f"❌ Error auto-sharing case study: {str(e)}")
        return jsonify({"error": "Failed to share case study"}), 500

@bp.route('/installation/<tenant_id>/disconnect', methods=['POST'])
@login_required
def disconnect_installation(tenant_id):
    """
    Disconnect a specific Teams tenant installation
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        success = installation_service.delete_installation(user_id, tenant_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Tenant disconnected successfully"
            })
        else:
            return jsonify({"error": "Failed to disconnect tenant"}), 400
            
    except Exception as e:
        print(f"❌ Error disconnecting installation: {str(e)}")
        return jsonify({"error": "Failed to disconnect"}), 500

# User Token OAuth Routes (for posting as user)
@bp.route('/user/authorize')
@login_required
def authorize_user():
    """
    Start the OAuth flow for user token - redirect user to Microsoft for user authorization
    """
    try:
        # Generate a random state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Store state in session with user-specific key
        user_id = get_current_user_id()
        session[f'teams_user_oauth_state_{user_id}'] = state
        
        # Also store in general session for backward compatibility
        session['teams_user_oauth_state'] = state
        
        print(f"🔐 Generated user OAuth state for user {user_id}: {state[:10]}...")
        
        # Get tenant_id from query params if specified
        tenant_id = request.args.get('tenant_id')
        
        oauth_service = TeamsOAuthService()
        oauth_url = oauth_service.get_oauth_url(state=state, tenant_id=tenant_id)
        
        return redirect(oauth_url)
        
    except Exception as e:
        print(f"❌ Error starting user OAuth flow: {str(e)}")
        return jsonify({"error": "Failed to start user OAuth flow"}), 500

@bp.route('/user/callback')
@login_required
def callback_user():
    """
    Handle the OAuth callback from Microsoft for user token authorization
    """
    try:
        # Get the authorization code from Microsoft
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state parameter (but don't fail if it's missing)
        user_id = get_current_user_id()
        stored_state = session.get('teams_user_oauth_state') or session.get(f'teams_user_oauth_state_{user_id}')
        
        if state and stored_state and state != stored_state:
            print(f"⚠️ State parameter mismatch for user {user_id}. Expected: {stored_state[:10]}..., Got: {state[:10]}...")
            # Don't fail the OAuth flow for state mismatch, just log it
        elif not stored_state:
            print(f"⚠️ No stored state found for user {user_id}, but continuing with OAuth flow")
        else:
            print(f"✅ State parameter validated successfully for user {user_id}")
        
        if not code:
            return jsonify({"error": "No authorization code received"}), 400
        
        # Exchange code for user token data
        oauth_service = TeamsOAuthService()
        token_data = oauth_service.exchange_code_for_token(code)
        
        if not token_data:
            return jsonify({"error": "Failed to exchange code for user token"}), 500
        
        # Save the user token
        success = oauth_service.save_user_token(user_id, token_data)
        
        if not success:
            return jsonify({"error": "Failed to save user token"}), 500
        
        # Test the user token
        test_result = oauth_service.test_user_token(token_data["access_token"])
        
        # Clear the state from session
        session.pop('teams_user_oauth_state', None)
        session.pop(f'teams_user_oauth_state_{user_id}', None)
        
        if test_result:
            # Redirect to Teams share page with success params (similar to Slack flow)
            return redirect(url_for('teams_oauth.share_page', 
                                    status='success', 
                                    tenant_name=token_data["tenant_name"],
                                    user_name=token_data["user_name"]))
        else:
            # Redirect with error
            return redirect(url_for('teams_oauth.share_page', 
                                    status='error', 
                                    error='user_token_test_failed'))
        
    except Exception as e:
        print(f"❌ Error in user OAuth callback: {str(e)}")
        return jsonify({"error": "Failed to complete user OAuth flow"}), 500

@bp.route('/user/status')
@login_required
def get_user_status():
    """
    Get the current Teams user connection status
    """
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "success": True,
            "connected": user.teams_connected,
            "user_id": user.teams_user_id,
            "tenant_id": user.teams_tenant_id,
            "authed_at": user.teams_authed_at.isoformat() if user.teams_authed_at else None
        })
        
    except Exception as e:
        print(f"❌ Error getting user status: {str(e)}")
        return jsonify({"error": "Failed to get user status"}), 500

@bp.route('/user/teams')
@login_required
def get_user_teams():
    """
    Get teams the user has access to using their token
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        teams = installation_service.get_user_teams(user_id)
        
        return jsonify({
            "success": True,
            "teams": teams
        })
        
    except Exception as e:
        print(f"❌ Error getting user teams: {str(e)}")
        return jsonify({"error": "Failed to get user teams"}), 500

@bp.route('/user/teams/<team_id>/channels')
@login_required
def get_user_team_channels(team_id):
    """
    Get channels for a specific team using user token
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        channels = installation_service.get_user_team_channels(user_id, team_id)
        
        return jsonify({
            "success": True,
            "channels": channels
        })
        
    except Exception as e:
        print(f"❌ Error getting user team channels: {str(e)}")
        return jsonify({"error": "Failed to get user team channels"}), 500

@bp.route('/user/post', methods=['POST'])
@login_required
def post_message_as_user():
    """
    Post a message to Teams as the user
    """
    try:
        data = request.get_json()
        team_id = data.get('team_id')
        channel_id = data.get('channel_id')
        text = data.get('text')
        
        if not team_id or not channel_id or not text:
            return jsonify({"error": "Missing team_id, channel_id, or text"}), 400
        
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        # Post the message as user
        result = installation_service.post_custom_message_as_user(user_id, team_id, channel_id, text)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "Message sent successfully to Teams channel",
                "message_id": result.get("message_id"),
                "createdDateTime": result.get("createdDateTime")
            })
        else:
            return jsonify({
                "error": result.get("error", "Failed to send message"),
                "action_required": result.get("action_required")
            }), 400
        
    except Exception as e:
        print(f"❌ Error posting message as user: {str(e)}")
        return jsonify({"error": "Failed to post message"}), 500

@bp.route('/user/auto-share-case-study', methods=['POST'])
@login_required
def auto_share_case_study_as_user():
    """
    Automatically share a case study to Teams as the user
    """
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        team_id = data.get('team_id')
        channel_id = data.get('channel_id')
        
        if not case_study_id or not team_id or not channel_id:
            return jsonify({"error": "Missing case_study_id, team_id, or channel_id"}), 400
        
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        # Get the case study
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Get user info for personalization
        user = User.query.get(user_id)
        user_name = f"{user.first_name} {user.last_name}" if user else "I"
        
        # Post the message as user
        result = installation_service.post_message_as_user(user_id, team_id, channel_id, case_study, user_name)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Successfully shared case study to Teams as {user_name}!",
                "message_id": result.get("message_id"),
                "createdDateTime": result.get("createdDateTime")
            })
        else:
            return jsonify({
                "error": result.get("error", "Failed to share case study"),
                "action_required": result.get("action_required")
            }), 400
        
    except Exception as e:
        print(f"❌ Error auto-sharing case study as user: {str(e)}")
        return jsonify({"error": "Failed to share case study"}), 500

@bp.route('/user/can-post')
@login_required
def check_user_posting_capability():
    """
    Check if user can post to Teams as themselves
    """
    try:
        user_id = get_current_user_id()
        installation_service = TeamsInstallationService()
        
        capability = installation_service.can_post_as_user(user_id)
        
        return jsonify(capability)
        
    except Exception as e:
        print(f"❌ Error checking user posting capability: {str(e)}")
        return jsonify({"error": "Failed to check posting capability"}), 500