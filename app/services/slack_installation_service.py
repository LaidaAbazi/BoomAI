import os
import requests
import json
from datetime import datetime
from cryptography.fernet import Fernet
from app.models import db, SlackInstallation, User

class SlackInstallationService:
    def __init__(self):
        self.client_id = os.getenv("SLACK_CLIENT_ID")
        self.client_secret = os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SLACK_REDIRECT_URI", "https://2b670ee75077.ngrok-free.app/api/slack/oauth/callback")
        
        # Bot token scopes for workspace installation
        self.bot_scope = "chat:write,channels:read,groups:read,channels:join"
        
        # User token scopes for posting as user
        self.user_scope = "chat:write,channels:read,groups:read"
        
        # Encryption key for tokens
        self.encryption_key = os.getenv("SLACK_TOKEN_ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a new key if none exists
            self.encryption_key = Fernet.generate_key()
            print(f" Generated new encryption key. Set SLACK_TOKEN_ENCRYPTION_KEY={self.encryption_key.decode()}")
        
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_token(self, token):
        """Encrypt a Slack token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt a stored Slack token"""
        try:
            return self.cipher.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            print(f" Error decrypting token: {str(e)}")
            return None
    
    def get_oauth_url(self, state=None, team_id=None):
        """Generate OAuth URL for workspace installation"""
        base_url = "https://slack.com/oauth/v2/authorize"
        params = {
            "client_id": self.client_id,
            "scope": self.bot_scope,
            "redirect_uri": self.redirect_uri
        }
        
        if state:
            params["state"] = state
        if team_id:
            params["team"] = team_id
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    def exchange_code_for_installation(self, code):
        """Exchange OAuth code for installation data"""
        try:
            url = "https://slack.com/api/oauth.v2.access"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    # Extract installation data - this is bot token installation
                    team = result.get("team", {})
                    enterprise = result.get("enterprise", {})
                    
                    return {
                        "team_id": team.get("id"),
                        "team_name": team.get("name"),
                        "bot_token": result.get("access_token"),  # This is the bot token
                        "scope": result.get("scope", ""),
                        "is_enterprise_install": result.get("is_enterprise_install", False),
                        "enterprise_id": enterprise.get("id") if enterprise else None,
                        "enterprise_name": enterprise.get("name") if enterprise else None
                    }
                else:
                    print(f" OAuth error: {result.get('error')}")
                    return None
            else:
                print(f" HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f" Error exchanging code for installation: {str(e)}")
            return None
    
    def create_installation(self, user_id, installation_data):
        """Create a new Slack installation record"""
        try:
            # Check if installation already exists
            existing = SlackInstallation.query.filter_by(
                user_id=user_id,
                slack_team_id=installation_data["team_id"]
            ).first()
            
            if existing:
                # Update existing installation
                existing.slack_team_name = installation_data["team_name"]
                existing.bot_token = self.encrypt_token(installation_data["bot_token"])
                existing.scope = installation_data["scope"]
                existing.is_enterprise_install = installation_data["is_enterprise_install"]
                existing.enterprise_id = installation_data["enterprise_id"]
                existing.enterprise_name = installation_data["enterprise_name"]
                existing.installed_at = datetime.utcnow()
            else:
                # Create new installation
                installation = SlackInstallation(
                    user_id=user_id,
                    slack_team_id=installation_data["team_id"],
                    slack_team_name=installation_data["team_name"],
                    bot_token=self.encrypt_token(installation_data["bot_token"]),
                    scope=installation_data["scope"],
                    is_enterprise_install=installation_data["is_enterprise_install"],
                    enterprise_id=installation_data["enterprise_id"],
                    enterprise_name=installation_data["enterprise_name"]
                )
                db.session.add(installation)
            
            db.session.commit()
            return True
            
        except Exception as e:
            print(f" Error creating installation: {str(e)}")
            db.session.rollback()
            return False
    
    def get_user_installations(self, user_id):
        """Get all Slack installations for a user"""
        try:
            installations = SlackInstallation.query.filter_by(user_id=user_id).all()
            return [
                {
                    "id": inst.id,
                    "team_id": inst.slack_team_id,
                    "team_name": inst.slack_team_name,
                    "is_enterprise": inst.is_enterprise_install,
                    "enterprise_name": inst.enterprise_name,
                    "scope": inst.scope,
                    "installed_at": inst.installed_at.isoformat() if inst.installed_at else None
                }
                for inst in installations
            ]
        except Exception as e:
            print(f" Error getting user installations: {str(e)}")
            return []
    
    def get_installation_token(self, user_id, team_id):
        """Get the bot token for a specific workspace installation"""
        try:
            installation = SlackInstallation.query.filter_by(
                user_id=user_id,
                slack_team_id=team_id
            ).first()
            
            if installation:
                return self.decrypt_token(installation.bot_token)
            return None
            
        except Exception as e:
            print(f" Error getting installation token: {str(e)}")
            return None
    
    def get_workspace_conversations(self, bot_token, team_id):
        """Get conversations for a specific workspace using bot token"""
        try:
            url = "https://slack.com/api/conversations.list"
            headers = {
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "types": "public_channel,private_channel",
                "limit": 1000,
                "exclude_archived": True
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    conversations = []
                    
                    # Process public channels
                    for conv in result.get("channels", []):
                        conversations.append({
                            "id": conv["id"],
                            "name": conv["name"],
                            "type": "public_channel",
                            "is_private": False,
                            "is_member": conv.get("is_member", False),
                            "is_archived": conv.get("is_archived", False)
                        })
                    
                    # Process private channels (only if bot is member)
                    for conv in result.get("groups", []):
                        if conv.get("is_member"):
                            conversations.append({
                                "id": conv["id"],
                                "name": conv["name"],
                                "type": "private_channel",
                                "is_private": True,
                                "is_member": True,
                                "is_archived": conv.get("is_archived", False)
                            })
                    
                    return conversations
                else:
                    print(f" Slack API error: {result.get('error')}")
                    return []
            else:
                print(f" HTTP error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f" Error getting workspace conversations: {str(e)}")
            return []
    
    def join_public_channel(self, bot_token, channel_id):
        """Join a public channel before posting"""
        try:
            url = "https://slack.com/api/conversations.join"
            headers = {
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json"
            }
            
            data = {"channel": channel_id}
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("ok", False)
            return False
            
        except Exception as e:
            print(f" Error joining channel: {str(e)}")
            return False
    
    def post_message(self, bot_token, channel_id, text, blocks=None):
        """Post a message to a Slack channel using bot token"""
        try:
            message = {
                "channel": channel_id,
                "text": text
            }
            
            if blocks:
                message["blocks"] = blocks
            
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return {"success": True, "ts": result.get("ts")}
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def post_message_as_user(self, user_token, channel_id, text, blocks=None):
        """Post a message to Slack as the user (not as bot)"""
        try:
            message = {
                "channel": channel_id,
                "text": text
            }
            
            if blocks:
                message["blocks"] = blocks
            
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return {"success": True, "ts": result.get("ts")}
                else:
                    return {"success": False, "error": result.get("error")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_installation(self, bot_token):
        """Test if the installation is working by calling auth.test"""
        try:
            url = "https://slack.com/api/auth.test"
            headers = {
                "Authorization": f"Bearer {bot_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("ok", False)
            return False
            
        except Exception as e:
            print(f" Error testing installation: {str(e)}")
            return False
    
    def delete_installation(self, user_id, team_id):
        """Delete a Slack installation"""
        try:
            installation = SlackInstallation.query.filter_by(
                user_id=user_id,
                slack_team_id=team_id
            ).first()
            
            if installation:
                db.session.delete(installation)
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            print(f" Error deleting installation: {str(e)}")
            db.session.rollback()
            return False 

    def can_post_to_workspace(self, user_id, team_id):
        """Check if user can post to a specific workspace"""
        try:
            installation = SlackInstallation.query.filter_by(
                user_id=user_id,
                slack_team_id=team_id
            ).first()
            
            if not installation:
                return {
                    "can_post": False,
                    "reason": "not_installed",
                    "message": "StoryBoom is not installed in this workspace",
                    "action_required": "install",
                    "authorize_url": f"/api/slack/oauth/authorize?team_id={team_id}"
                }
            
            # Test if the installation is still valid
            bot_token = self.decrypt_token(installation.bot_token)
            if not bot_token:
                return {
                    "can_post": False,
                    "reason": "invalid_token",
                    "message": "Installation token is invalid",
                    "action_required": "reinstall",
                    "authorize_url": f"/api/slack/oauth/authorize?team_id={team_id}"
                }
            
            # Test the installation
            test_result = self.test_installation(bot_token)
            if not test_result:
                return {
                    "can_post": False,
                    "reason": "installation_failed",
                    "message": "Installation test failed",
                    "action_required": "reinstall",
                    "authorize_url": f"/api/slack/oauth/authorize?team_id={team_id}"
                }
            
            return {
                "can_post": True,
                "workspace_name": installation.slack_team_name,
                "is_enterprise": installation.is_enterprise_install,
                "scope": installation.scope
            }
            
        except Exception as e:
            print(f" Error checking workspace access: {str(e)}")
            return {
                "can_post": False,
                "reason": "error",
                "message": "Error checking workspace access",
                "action_required": "contact_support"
            } 

    def generate_slack_message_from_email_draft(self, case_study, user_name=None):
        """
        Generate a Slack message using the email draft content
        This creates a message that sounds like it's coming from the user
        """
        try:
            if not case_study.final_summary:
                return f" I'm happy to share a success story! Check it out "
            
            # Clean the summary text
            clean_summary = self._clean_summary_text(case_study.final_summary)
            
            # Create a personal message for Slack
            message = f" *{case_study.title or 'Success Story'}*\n\n"
            
            # Add a brief summary (first 200 characters)
            if clean_summary:
                summary_preview = clean_summary[:200]
                if len(clean_summary) > 200:
                    summary_preview += "..."
                message += summary_preview + "\n\n"
            
            # Add personal touch
            sender_name = user_name or "I"
            message += f"*{sender_name}* wanted to share this success story with the team! 📈\n\n"
            
            # Add call to action
            message += " *Key highlights:*\n"
            
            # Extract key points from the summary
            lines = clean_summary.split('\n')
            key_points = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 20 and len(line) < 100:
                    if any(keyword in line.lower() for keyword in ['increase', 'decrease', 'improved', 'achieved', 'result', 'success']):
                        key_points.append(line)
                        if len(key_points) >= 3:
                            break
            
            if key_points:
                for point in key_points:
                    message += f"• {point}\n"
            else:
                message += "• Check out the full case study for details\n"
            
            message += f"\n *Full case study available* - Let me know if you'd like to learn more!"
            
            return message
            
        except Exception as e:
            print(f" Error generating Slack message: {str(e)}")
            return f" I'm happy to share a success story! Check it out 📄"
    
    def _clean_summary_text(self, text):
        """Clean summary text for Slack formatting"""
        if not text:
            return ""
        
        # Remove common formatting markers
        text = text.replace("HERO STATEMENT:", "").replace("BANNER:", "")
        text = text.replace("BACKGROUND:", "").replace("CHALLENGE:", "")
        text = text.replace("SOLUTION:", "").replace("RESULTS:", "")
        text = text.replace("CONCLUSION:", "")
        
        # Clean up extra whitespace
        text = " ".join(text.split())
        
        return text.strip() 