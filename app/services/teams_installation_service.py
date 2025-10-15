import os
import requests
import json
from datetime import datetime
from cryptography.fernet import Fernet
from app.models import db, TeamsInstallation, User
from app.services.teams_oauth_service import TeamsOAuthService

class TeamsInstallationService:
    def __init__(self):
        self.client_id = os.getenv("TEAMS_CLIENT_ID")
        self.client_secret = os.getenv("TEAMS_CLIENT_SECRET")
        self.redirect_uri = os.getenv("TEAMS_REDIRECT_URI", "https://2b670ee75077.ngrok-free.app/api/teams/oauth/callback")
        self.tenant_id = os.getenv("TEAMS_TENANT_ID", "common")
        
        # Microsoft Graph API scopes
        self.scope = "https://graph.microsoft.com/ChannelMessage.Send https://graph.microsoft.com/Team.ReadBasic.All https://graph.microsoft.com/User.Read https://graph.microsoft.com/Chat.Read"
        
        # Encryption key for tokens
        self.encryption_key = os.getenv("TEAMS_TOKEN_ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a new key if none exists
            self.encryption_key = Fernet.generate_key()
            print(f"🔑 Generated new encryption key. Set TEAMS_TOKEN_ENCRYPTION_KEY={self.encryption_key.decode()}")
            print("⚠️  WARNING: Using temporary encryption key. Set TEAMS_TOKEN_ENCRYPTION_KEY environment variable for production!")
        else:
            # Convert string to bytes if needed
            if isinstance(self.encryption_key, str):
                self.encryption_key = self.encryption_key.encode()
        
        self.cipher = Fernet(self.encryption_key)
        
        # Initialize OAuth service for user tokens
        self.oauth_service = TeamsOAuthService()
    
    def encrypt_token(self, token):
        """Encrypt a Teams token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt a stored Teams token"""
        try:
            return self.cipher.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            print(f"❌ Error decrypting token: {str(e)}")
            return None
    
    def get_oauth_url(self, state=None, tenant_id=None):
        """Generate OAuth URL for tenant installation"""
        from urllib.parse import urlencode, quote
        base_url = f"https://login.microsoftonline.com/{tenant_id or self.tenant_id}/oauth2/v2.0/authorize"
        params = {
            "client_id": self.client_id or "",
            "response_type": "code",
            "redirect_uri": self.redirect_uri or "",
            "scope": self.scope or "",
            "response_mode": "query",
        }
        if state:
            params["state"] = state
        query_string = urlencode(params, quote_via=quote, safe="/:")
        return f"{base_url}?{query_string}"
    
    def exchange_code_for_installation(self, code):
        """Exchange OAuth code for installation data"""
        try:
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "scope": self.scope
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Get user info to determine tenant
                access_token = result["access_token"]
                user_info = self._get_user_info(access_token)
                
                if not user_info:
                    return None
                
                # Try to get organization info (for work/school accounts)
                org_tenant_id = None
                org_tenant_name = None
                try:
                    org_url = "https://graph.microsoft.com/v1.0/organization?$select=id,displayName"
                    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
                    org_res = requests.get(org_url, headers=headers)
                    if org_res.status_code == 200:
                        value = org_res.json().get("value", [])
                        if value:
                            org_tenant_id = value[0].get("id")
                            org_tenant_name = value[0].get("displayName")
                except Exception as _:
                    pass

                # Extract tenant ID/name with fallbacks
                # For personal accounts, use the user's tenantId from /me endpoint
                # For organizational accounts, prefer the organization endpoint
                tenant_id = org_tenant_id or user_info.get("tenantId") or self.tenant_id
                
                # For tenant name, use organization name for work accounts, or a generic name for personal accounts
                if org_tenant_name:
                    tenant_name = org_tenant_name  # Work/school account with organization
                elif user_info.get("companyName"):
                    tenant_name = user_info.get("companyName")  # Work/school account without organization endpoint
                else:
                    # Personal account - use a generic name
                    tenant_name = "Personal Microsoft Account"
                
                return {
                    "access_token": access_token,
                    "refresh_token": result.get("refresh_token"),
                    "scope": result.get("scope", ""),
                    "expires_in": result.get("expires_in"),
                    "tenant_id": tenant_id,
                    "user_id": user_info.get("id"),
                    "user_name": user_info.get("displayName"),
                    "tenant_name": tenant_name
                }
            else:
                print(f"❌ OAuth error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error exchanging code for installation: {str(e)}")
            return None
    
    def _get_user_info(self, access_token):
        """Get user information from Microsoft Graph"""
        try:
            url = "https://graph.microsoft.com/v1.0/me"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get user info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting user info: {str(e)}")
            return None
    
    def create_installation(self, user_id, installation_data):
        """Create or update a Teams installation"""
        try:
            # Check if installation already exists
            existing = TeamsInstallation.query.filter_by(
                user_id=user_id,
                teams_tenant_id=installation_data["tenant_id"]
            ).first()
            
            if existing:
                # Update existing installation
                existing.access_token = self.encrypt_token(installation_data["access_token"])
                if installation_data.get("refresh_token"):
                    existing.refresh_token = self.encrypt_token(installation_data["refresh_token"])
                existing.scope = installation_data["scope"]
                existing.teams_tenant_name = installation_data["tenant_name"]
                existing.installed_at = datetime.utcnow()
            else:
                # Create new installation
                installation = TeamsInstallation(
                    user_id=user_id,
                    teams_tenant_id=installation_data["tenant_id"],
                    teams_tenant_name=installation_data["tenant_name"],
                    access_token=self.encrypt_token(installation_data["access_token"]),
                    refresh_token=self.encrypt_token(installation_data["refresh_token"]) if installation_data.get("refresh_token") else None,
                    scope=installation_data["scope"]
                )
                db.session.add(installation)
            
            # Update user's Teams connection status
            user = User.query.get(user_id)
            if user:
                user.teams_connected = True
                user.teams_user_id = installation_data["user_id"]
                user.teams_tenant_id = installation_data["tenant_id"]
                user.teams_authed_at = datetime.utcnow()
            
            db.session.commit()
            print(f"✅ Teams installation created/updated for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating Teams installation: {str(e)}")
            db.session.rollback()
            return False
    
    def get_installation_token(self, user_id, tenant_id):
        """Get the access token for a specific installation"""
        try:
            installation = TeamsInstallation.query.filter_by(
                user_id=user_id,
                teams_tenant_id=tenant_id
            ).first()
            
            if installation:
                return self.decrypt_token(installation.access_token)
            return None
            
        except Exception as e:
            print(f"❌ Error getting installation token: {str(e)}")
            return None
    
    def get_user_installations(self, user_id):
        """Get all Teams installations for a user"""
        try:
            installations = TeamsInstallation.query.filter_by(user_id=user_id).all()
            return [
                {
                    "id": inst.id,
                    "tenant_id": inst.teams_tenant_id,
                    "tenant_name": inst.teams_tenant_name,
                    "installed_at": inst.installed_at.isoformat() if inst.installed_at else None
                }
                for inst in installations
            ]
        except Exception as e:
            print(f"❌ Error getting user installations: {str(e)}")
            return []
    
    def test_installation(self, access_token):
        """Test if the installation is working"""
        try:
            url = "https://graph.microsoft.com/v1.0/me"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error testing installation: {str(e)}")
            return False
    
    def get_tenant_teams(self, access_token, tenant_id):
        """Get teams for a specific tenant"""
        try:
            url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            teams = []
            if response.status_code == 200:
                teams_data = response.json().get("value", [])
                teams = [
                    {
                        "id": team["id"],
                        "name": team["displayName"],
                        "description": team.get("description", ""),
                        "tenant_id": tenant_id,
                        "is_personal_chat": False
                    }
                    for team in teams_data
                ]
                print(f"ℹ️ Found {len(teams)} Teams for tenant {tenant_id}")
            else:
                print(f"ℹ️ Teams API returned {response.status_code} for tenant {tenant_id}")
            
            # Always try to get chats as well (works for both personal and org accounts)
            chats = self._get_personal_chats(access_token, tenant_id)
            print(f"ℹ️ Found {len(chats)} chats for tenant {tenant_id}")
            
            # Combine teams and chats
            all_teams = teams + chats
            print(f"ℹ️ Total: {len(all_teams)} teams/chats for tenant {tenant_id}")
            
            return all_teams
                
        except Exception as e:
            print(f"❌ Error getting teams: {str(e)}")
            return []
    
    def _get_personal_chats(self, access_token, tenant_id):
        """Get personal chats for both personal and organizational accounts"""
        try:
            # Try to get chats (personal and group chats)
            url = "https://graph.microsoft.com/v1.0/me/chats"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            print(f"🔍 Calling Microsoft Graph API: {url}")
            response = requests.get(url, headers=headers)
            print(f"🔍 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                chats = data.get("value", [])
                print(f"ℹ️ Found {len(chats)} chats from /me/chats")
                print(f"🔍 Raw response: {response.text[:500]}...")  # Debug first 500 chars
                
                # Check for pagination
                next_link = data.get("@odata.nextLink")
                if next_link:
                    print(f"ℹ️ More chats available via pagination: {next_link}")
                
                # Convert chats to team-like format
                chat_teams = []
                for i, chat in enumerate(chats):
                    print(f"🔍 Chat {i+1}: {chat}")
                    chat_type = chat.get("chatType", "unknown")
                    
                    # Skip certain chat types that aren't useful for sharing
                    if chat_type in ["meeting", "unknown"]:
                        print(f"⏭️ Skipping chat type: {chat_type}")
                        continue
                    
                    # Generate a better name based on chat type and members
                    chat_name = chat.get("topic")
                    if not chat_name:
                        if chat_type == "oneOnOne":
                            # Try to get the other person's name
                            members = chat.get("members", [])
                            if len(members) >= 2:
                                other_member = next((m for m in members if m.get("userId") != "me"), None)
                                if other_member:
                                    chat_name = f"Chat with {other_member.get('displayName', 'Unknown')}"
                                else:
                                    chat_name = "Personal Chat"
                            else:
                                chat_name = "Personal Chat"
                        elif chat_type == "group":
                            member_count = len(chat.get("members", []))
                            chat_name = f"Group Chat ({member_count} members)"
                        else:
                            chat_name = f"Chat {chat['id'][:8]}"
                    
                    # Create description based on chat type
                    if chat_type == "oneOnOne":
                        description = "Personal conversation"
                    elif chat_type == "group":
                        member_count = len(chat.get("members", []))
                        description = f"Group chat with {member_count} members"
                    else:
                        description = f"Chat ({chat_type})"
                    
                    chat_teams.append({
                        "id": chat["id"],
                        "name": chat_name,
                        "description": description,
                        "tenant_id": tenant_id,
                        "is_personal_chat": True,
                        "chat_type": chat_type
                    })
                
                print(f"ℹ️ Converted {len(chat_teams)} chats to teams")
                return chat_teams
            else:
                print(f"❌ Chats API returned {response.status_code} - {response.text}")
                if response.status_code == 403:
                    print("🔒 Permission denied - you may need to add 'Chat.Read' permission to your Azure App Registration")
                return []
                
        except Exception as e:
            print(f"❌ Error getting personal chats: {str(e)}")
            return []
    
    def get_team_channels(self, access_token, team_id, is_personal_chat=False):
        """Get channels for a specific team"""
        try:
            # For personal chats, we don't have channels - return the chat itself as a "channel"
            if is_personal_chat:
                return [{
                    "id": team_id,  # Use the chat ID as channel ID
                    "name": "Main Chat",
                    "description": "Personal or group chat",
                    "is_private": False
                }]
            
            # For regular teams, get channels
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                channels = response.json().get("value", [])
                return [
                    {
                        "id": channel["id"],
                        "name": channel["displayName"],
                        "description": channel.get("description", ""),
                        "is_private": channel.get("membershipType") == "private"
                    }
                    for channel in channels
                ]
            else:
                print(f"❌ Failed to get channels: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting channels: {str(e)}")
            return [] 

    def generate_teams_message_from_email_draft(self, case_study, user_name):
        """
        Generate a Teams-formatted message from case study email draft content
        """
        try:
            # Start with a header
            message_content = f"🎉 **New Success Story: {case_study.title}**\n\n"
            
            # Add personalized intro
            message_content += f"Hey team! {user_name} here with an exciting success story to share:\n\n"
            
            # Add case study content if available
            if case_study.final_summary:
                # Clean up the summary for Teams
                summary = case_study.final_summary.strip()
                message_content += f"**Summary:**\n{summary}\n\n"
            
            # Add key details if available
            if case_study.challenge:
                message_content += f"**Challenge:**\n{case_study.challenge[:300]}{'...' if len(case_study.challenge) > 300 else ''}\n\n"
            
            if case_study.solution:
                message_content += f"**Solution:**\n{case_study.solution[:300]}{'...' if len(case_study.solution) > 300 else ''}\n\n"
            
            if case_study.results:
                message_content += f"**Results:**\n{case_study.results[:300]}{'...' if len(case_study.results) > 300 else ''}\n\n"
            
            # Add call to action
            message_content += "💡 *This success story was generated using StoryBoom AI - your intelligent case study creation tool!*\n\n"
            message_content += "Want to create your own success stories? Check out StoryBoom! 🚀"
            
            return message_content
            
        except Exception as e:
            print(f"❌ Error generating Teams message: {str(e)}")
            return f"🎉 **New Success Story: {case_study.title}**\n\nA new success story has been created and shared!"
    
    def post_message_to_teams(self, access_token, team_id, channel_id, message_content):
        """
        Post a message to a Teams channel
        """
        try:
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
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "createdDateTime": result.get("createdDateTime"),
                    "message_id": result.get("id")
                }
            else:
                print(f"❌ Failed to post message: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            print(f"❌ Error posting message to Teams: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_installation(self, user_id, tenant_id):
        """
        Delete a Teams installation
        """
        try:
            installation = TeamsInstallation.query.filter_by(
                user_id=user_id,
                teams_tenant_id=tenant_id
            ).first()
            
            if installation:
                db.session.delete(installation)
                
                # Update user's Teams connection status if this was their only installation
                remaining_installations = TeamsInstallation.query.filter_by(user_id=user_id).count()
                if remaining_installations == 0:
                    user = User.query.get(user_id)
                    if user:
                        user.teams_connected = False
                        user.teams_user_id = None
                        user.teams_tenant_id = None
                        user.teams_authed_at = None
                
                db.session.commit()
                print(f"✅ Teams installation deleted for user {user_id}, tenant {tenant_id}")
                return True
            else:
                print(f"❌ No installation found for user {user_id}, tenant {tenant_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting Teams installation: {str(e)}")
            db.session.rollback()
            return False 
    
    def get_user_token(self, user_id):
        """Get user's Teams token for posting as user"""
        try:
            return self.oauth_service.get_user_token(user_id)
        except Exception as e:
            print(f"❌ Error getting user token: {str(e)}")
            return None
    
    def save_user_token(self, user_id, token_data):
        """Save user token for posting as user"""
        try:
            return self.oauth_service.save_user_token(user_id, token_data)
        except Exception as e:
            print(f"❌ Error saving user token: {str(e)}")
            return False
    
    def post_message_as_user(self, user_id, team_id, channel_id, case_study, user_name=None):
        """Post a message to Teams as the user (not as bot)"""
        try:
            user_token = self.get_user_token(user_id)
            if not user_token:
                return {
                    "success": False,
                    "error": "No user token found. Please authorize Teams connection first.",
                    "action_required": "authorize"
                }
            
            # Test the token
            if not self.oauth_service.test_user_token(user_token):
                return {
                    "success": False,
                    "error": "User token is invalid or expired. Please re-authorize.",
                    "action_required": "reauthorize"
                }
            
            # Post the message as user
            result = self.oauth_service.send_message_as_user(
                user_token, team_id, channel_id, case_study, user_name
            )
            
            return result
            
        except Exception as e:
            print(f"❌ Error posting message as user: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def post_custom_message_as_user(self, user_id, team_id, channel_id, message_text):
        """Post a custom message to Teams as the user"""
        try:
            user_token = self.get_user_token(user_id)
            if not user_token:
                return {
                    "success": False,
                    "error": "No user token found. Please authorize Teams connection first.",
                    "action_required": "authorize"
                }
            
            # Test the token
            if not self.oauth_service.test_user_token(user_token):
                return {
                    "success": False,
                    "error": "User token is invalid or expired. Please re-authorize.",
                    "action_required": "reauthorize"
                }
            
            # Post the message as user
            result = self.oauth_service.post_message(user_token, team_id, channel_id, message_text)
            
            return result
            
        except Exception as e:
            print(f"❌ Error posting custom message as user: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_teams(self, user_id):
        """Get teams the user has access to"""
        try:
            user_token = self.get_user_token(user_id)
            if not user_token:
                return []
            
            return self.oauth_service.get_user_teams(user_token)
            
        except Exception as e:
            print(f"❌ Error getting user teams: {str(e)}")
            return []
    
    def get_user_team_channels(self, user_id, team_id):
        """Get channels for a team using user token"""
        try:
            user_token = self.get_user_token(user_id)
            if not user_token:
                return []
            
            return self.oauth_service.get_team_channels(user_token, team_id)
            
        except Exception as e:
            print(f"❌ Error getting user team channels: {str(e)}")
            return []
    
    def can_post_as_user(self, user_id):
        """Check if user can post to Teams as themselves"""
        try:
            user = User.query.get(user_id)
            if not user or not user.teams_connected:
                return {
                    "can_post": False,
                    "reason": "not_connected",
                    "message": "Teams not connected",
                    "action_required": "connect"
                }
            
            user_token = self.get_user_token(user_id)
            if not user_token:
                return {
                    "can_post": False,
                    "reason": "no_token",
                    "message": "No user token found",
                    "action_required": "authorize"
                }
            
            # Test the token
            if not self.oauth_service.test_user_token(user_token):
                return {
                    "can_post": False,
                    "reason": "invalid_token",
                    "message": "User token is invalid or expired",
                    "action_required": "reauthorize"
                }
            
            return {
                "can_post": True,
                "tenant_id": user.teams_tenant_id,
                "user_id": user.teams_user_id
            }
            
        except Exception as e:
            print(f"❌ Error checking user posting capability: {str(e)}")
            return {
                "can_post": False,
                "reason": "error",
                "message": "Error checking posting capability",
                "action_required": "contact_support"
            } 