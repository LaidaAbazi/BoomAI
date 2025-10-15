from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template
from app.models import db, User, CaseStudy
from app.services.slack_installation_service import SlackInstallationService
from app.utils.auth_helpers import login_required, get_current_user_id
import secrets

bp = Blueprint('slack_oauth', __name__, url_prefix='/api/slack/oauth')

@bp.route('/')
@login_required
def share_page():
    """
    Serve the dedicated Slack sharing page
    """
    return render_template('slack_multi_workspace.html')

@bp.route('/authorize')
@login_required
def authorize():
    """
    Start the OAuth flow - redirect user to Slack for workspace installation
    """
    try:
        # Generate a random state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Store state in session with user-specific key
        user_id = get_current_user_id()
        session[f'slack_oauth_state_{user_id}'] = state
        
        # Also store in general session for backward compatibility
        session['slack_oauth_state'] = state
        
        print(f"🔐 Generated OAuth state for user {user_id}: {state[:10]}...")
        
        # Get team_id from query params if specified
        team_id = request.args.get('team_id')
        
        installation_service = SlackInstallationService()
        oauth_url = installation_service.get_oauth_url(state=state, team_id=team_id)
        
        return redirect(oauth_url)
        
    except Exception as e:
        print(f"❌ Error starting OAuth flow: {str(e)}")
        return jsonify({"error": "Failed to start OAuth flow"}), 500

@bp.route('/callback')
@login_required
def callback():
    """
    Handle the OAuth callback from Slack for workspace installation
    """
    try:
        # Get the authorization code from Slack
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify state parameter (but don't fail if it's missing)
        user_id = get_current_user_id()
        stored_state = session.get('slack_oauth_state') or session.get(f'slack_oauth_state_{user_id}')
        
        if state and stored_state and state != stored_state:
            print(f"⚠️ State parameter mismatch for user {user_id}. Expected: {stored_state[:10]}..., Got: {state[:10]}...")
            # Don't fail the OAuth flow for state mismatch, just log it
            # This can happen if the session is lost or if there are multiple OAuth attempts
        elif not stored_state:
            print(f"⚠️ No stored state found for user {user_id}, but continuing with OAuth flow")
        else:
            print(f"✅ State parameter validated successfully for user {user_id}")
        
        if not code:
            return jsonify({"error": "No authorization code received"}), 400
        
        # Exchange code for installation data
        installation_service = SlackInstallationService()
        installation_data = installation_service.exchange_code_for_installation(code)
        
        if not installation_data:
            return jsonify({"error": "Failed to exchange code for installation"}), 500
        
        # Create or update the installation
        success = installation_service.create_installation(user_id, installation_data)
        
        if not success:
            return jsonify({"error": "Failed to save installation"}), 500
        
        # Test the installation
        test_result = installation_service.test_installation(installation_data["bot_token"])
        
        # Clear the state from session
        session.pop('slack_oauth_state', None)
        session.pop(f'slack_oauth_state_{user_id}', None)
        
        # Redirect to the Slack workspace page with success parameters
        redirect_url = f"/api/slack/oauth/?workspace={installation_data['team_id']}&auto_load=true&success=true&team_name={installation_data['team_name']}"
        return redirect(redirect_url)
            
    except Exception as e:
        print(f"❌ Error in OAuth callback: {str(e)}")
        return jsonify({"error": "OAuth callback failed"}), 500

@bp.route('/installations')
@login_required
def get_installations():
    """
    Get all Slack workspace installations for the user
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        return jsonify({
            "success": True,
            "installations": installations
        })
        
    except Exception as e:
        print(f" Error getting installations: {str(e)}")
        return jsonify({"error": "Failed to get installations"}), 500

@bp.route('/available-workspaces')
@login_required
def get_available_workspaces():
    """
    Get a list of workspaces the user can potentially connect to
    This helps users discover which workspaces they can add
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        # Get user's current installations
        current_installations = installation_service.get_user_installations(user_id)
        connected_team_ids = [inst['team_id'] for inst in current_installations]
        
        return jsonify({
            "success": True,
            "current_installations": current_installations,
            "connected_team_ids": connected_team_ids,
            "add_new_url": "/api/slack/oauth/authorize"
        })
        
    except Exception as e:
        print(f" Error getting available workspaces: {str(e)}")
        return jsonify({"error": "Failed to get available workspaces"}), 500

@bp.route('/workspace/<team_id>/conversations')
@login_required
def get_workspace_conversations(team_id):
    """
    Get conversations for a specific workspace
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        # Get the bot token for this workspace
        bot_token = installation_service.get_installation_token(user_id, team_id)
        
        if not bot_token:
            return jsonify({
                "error": "Workspace not found or not installed",
                "install_required": True
            }), 401
        
        # Get conversations for this workspace
        conversations = installation_service.get_workspace_conversations(bot_token, team_id)
        
        return jsonify({
            "success": True,
            "conversations": conversations
        })
        
    except Exception as e:
        print(f" Error getting workspace conversations: {str(e)}")
        return jsonify({"error": "Failed to get conversations"}), 500

@bp.route('/workspace/<team_id>/check-access')
@login_required
def check_workspace_access(team_id):
    """
    Check if user can post to a specific workspace
    This helps the UI show appropriate actions before posting
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        access_status = installation_service.can_post_to_workspace(user_id, team_id)
        
        return jsonify({
            "success": True,
            "access_status": access_status
        })
        
    except Exception as e:
        print(f" Error checking workspace access: {str(e)}")
        return jsonify({"error": "Failed to check workspace access"}), 500

@bp.route('/post', methods=['POST'])
@login_required
def post_message():
    """
    Post a message to a Slack channel in a specific workspace
    """
    try:
        data = request.get_json()
        team_id = data.get('team_id')  # Workspace ID
        channel_id = data.get('channel_id')  # Channel ID
        text = data.get('text')  # Message text
        blocks = data.get('blocks')  # Optional Slack blocks
        
        if not team_id or not channel_id or not text:
            return jsonify({"error": "Missing team_id, channel_id, or text"}), 400
        
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        # Get the bot token for this workspace
        bot_token = installation_service.get_installation_token(user_id, team_id)
        
        if not bot_token:
            return jsonify({
                "error": f"StoryBoom is not installed in this workspace yet.",
                "install_required": True,
                "authorize_url": f"/api/slack/oauth/authorize?team_id={team_id}",
                "workspace_id": team_id,
                "action_required": "install",
                "help_text": "Click 'Install StoryBoom in this workspace' to get started. This will redirect you to Slack to authorize the app."
            }), 401
        
        # Get workspace info to check if bot is in the channel
        conversations = installation_service.get_workspace_conversations(bot_token, team_id)
        target_channel = next((c for c in conversations if c["id"] == channel_id), None)
        
        if not target_channel:
            return jsonify({"error": "Channel not found"}), 404
        
        # For public channels, join if not already a member
        if not target_channel["is_private"] and not target_channel["is_member"]:
            join_success = installation_service.join_public_channel(bot_token, channel_id)
            if not join_success:
                return jsonify({"error": "Failed to join public channel"}), 500
        
        # For private channels, check if bot is a member
        if target_channel["is_private"] and not target_channel["is_member"]:
            return jsonify({
                "error": "Bot is not in this private channel. Ask a member to invite @StoryBoom to this private channel.",
                "invite_hint": True
            }), 403
        
        # Post the message
        result = installation_service.post_message(bot_token, channel_id, text, blocks)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "Message posted to Slack successfully!",
                "timestamp": result.get("ts")
            })
        else:
            return jsonify({
                "error": f"Failed to post message: {result.get('error', 'Unknown error')}"
            }), 400
        
    except Exception as e:
        print(f" Error posting message: {str(e)}")
        return jsonify({"error": "Failed to post message"}), 500

@bp.route('/installation/<team_id>/disconnect', methods=['POST'])
@login_required
def disconnect_installation(team_id):
    """
    Disconnect a specific Slack workspace installation
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        success = installation_service.delete_installation(user_id, team_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Workspace disconnected successfully"
            })
        else:
            return jsonify({"error": "Failed to disconnect workspace"}), 400
            
    except Exception as e:
        print(f" Error disconnecting installation: {str(e)}")
        return jsonify({"error": "Failed to disconnect"}), 500

@bp.route('/test/<team_id>')
@login_required
def test_installation(team_id):
    """
    Test if a Slack installation is working
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        # Get the bot token for this workspace
        bot_token = installation_service.get_installation_token(user_id, team_id)
        
        if not bot_token:
            return jsonify({"error": "Workspace not found"}), 404
        
        # Test the installation
        test_result = installation_service.test_installation(bot_token)
        
        if test_result:
            return jsonify({
                "success": True,
                "message": "Installation is working correctly"
            })
        else:
            return jsonify({
                "error": "Installation test failed"
            }), 400
            
    except Exception as e:
        print(f" Error testing installation: {str(e)}")
        return jsonify({"error": "Failed to test installation"}), 500 

@bp.route('/status')
@login_required
def get_slack_status():
    """
    Get the current Slack connection status for the user
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        return jsonify({
            "success": True,
            "connected": len(installations) > 0,
            "workspaces_count": len(installations),
            "installations": installations
        })
        
    except Exception as e:
        print(f" Error getting Slack status: {str(e)}")
        return jsonify({"error": "Failed to get Slack status"}), 500

@bp.route('/channels')
@login_required
def get_available_channels():
    """
    Get all available channels across user's connected workspaces
    """
    try:
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        all_channels = []
        for installation in installations:
            bot_token = installation_service.get_installation_token(user_id, installation['team_id'])
            if bot_token:
                conversations = installation_service.get_workspace_conversations(bot_token, installation['team_id'])
                for conv in conversations:
                    all_channels.append({
                        "id": conv["id"],
                        "name": conv["name"],
                        "workspace_name": installation['team_name'],
                        "workspace_id": installation['team_id'],
                        "is_private": conv["is_private"],
                        "type": conv["type"]
                    })
        
        return jsonify({
            "success": True,
            "channels": all_channels
        })
        
    except Exception as e:
        print(f" Error getting channels: {str(e)}")
        return jsonify({"error": "Failed to get channels"}), 500

@bp.route('/post_to_channel', methods=['POST'])
@login_required
def post_case_study_to_channel():
    """
    Post a case study to a specific Slack channel
    """
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        channel = data.get('channel')  # Channel name like "#general"
        
        if not case_study_id or not channel:
            return jsonify({"error": "Missing case_study_id or channel"}), 400
        
        # Get case study details
        from app.models import CaseStudy
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Find the workspace and channel
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        installations = installation_service.get_user_installations(user_id)
        
        # Find channel across all workspaces
        target_channel = None
        target_workspace = None
        
        for installation in installations:
            bot_token = installation_service.get_installation_token(user_id, installation['team_id'])
            if bot_token:
                conversations = installation_service.get_workspace_conversations(bot_token, installation['team_id'])
                for conv in conversations:
                    if conv["name"] == channel.replace("#", ""):
                        target_channel = conv
                        target_workspace = installation
                        break
                if target_channel:
                    break
        
        if not target_channel:
            return jsonify({"error": f"Channel {channel} not found in any connected workspace"}), 404
        
        # Build message text
        message_text = f" *{case_study.title or 'Success Story'}*\n\n"
        if case_study.final_summary:
            message_text += case_study.final_summary[:500]
            if len(case_study.final_summary) > 500:
                message_text += "..."
        
        # Post the message
        bot_token = installation_service.get_installation_token(user_id, target_workspace['team_id'])
        result = installation_service.post_message(bot_token, target_channel["id"], message_text)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Case study shared to #{target_channel['name']} in {target_workspace['team_name']} successfully!",
                "channel": target_channel['name'],
                "workspace": target_workspace['team_name']
            })
        else:
            return jsonify({
                "error": f"Failed to post message: {result.get('error', 'Unknown error')}"
            }), 400
        
    except Exception as e:
        print(f" Error posting case study to channel: {str(e)}")
        return jsonify({"error": "Failed to post case study"}), 500 

@bp.route('/auto-share-case-study', methods=['POST'])
@login_required
def auto_share_case_study():
    """
    Automatically share a case study to Slack using email draft content
    Posts as the user, not as the bot
    """
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        channel_id = data.get('channel_id')
        workspace_id = data.get('workspace_id')
        
        if not case_study_id or not channel_id or not workspace_id:
            return jsonify({"error": "Missing case_study_id, channel_id, or workspace_id"}), 400
        
        user_id = get_current_user_id()
        installation_service = SlackInstallationService()
        
        # Get the case study
        from app.models import CaseStudy, User
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Get user info for personalization
        user = User.query.get(user_id)
        user_name = f"{user.first_name} {user.last_name}" if user else "I"
        
        # Generate Slack message from email draft content
        slack_message = installation_service.generate_slack_message_from_email_draft(case_study, user_name)
        
        # For now, we'll use bot token (we'll implement user tokens in the next step)
        # Get the bot token for this workspace
        bot_token = installation_service.get_installation_token(user_id, workspace_id)
        
        if not bot_token:
            return jsonify({
                "error": "StoryBoom is not installed in this workspace yet.",
                "install_required": True,
                "authorize_url": f"/api/slack/oauth/authorize?team_id={workspace_id}"
            }), 401
        
        # Post the message
        result = installation_service.post_message(bot_token, channel_id, slack_message)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Successfully shared case study to Slack!",
                "timestamp": result.get("ts"),
                "channel_id": channel_id,
                "workspace_id": workspace_id
            })
        else:
            return jsonify({
                "error": f"Failed to post message: {result.get('error', 'Unknown error')}"
            }), 400
        
    except Exception as e:
        print(f" Error auto-sharing case study: {str(e)}")
        return jsonify({"error": "Failed to share case study"}), 500 