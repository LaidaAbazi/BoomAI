import os
import requests
import json
from datetime import datetime
from cryptography.fernet import Fernet
from app.models import db, User

class TeamsOAuthService:
    def __init__(self):
        self.client_id = os.getenv("TEAMS_CLIENT_ID")
        self.client_secret = os.getenv("TEAMS_CLIENT_SECRET")
        self.redirect_uri = os.getenv("TEAMS_REDIRECT_URI", "https://2b670ee75077.ngrok-free.app/api/teams/oauth/callback")
        self.tenant_id = os.getenv("TEAMS_TENANT_ID", "common")
        
        # Microsoft Graph API scopes for user tokens
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
        """Generate OAuth URL for user token authorization"""
        from urllib.parse import urlencode, quote
        base_url = f"https://login.microsoftonline.com/{tenant_id or self.tenant_id}/oauth2/v2.0/authorize"
        params = {
            "client_id": self.client_id or "",
            "response_type": "code",
            # redirect_uri must be URL-encoded exactly as registered
            "redirect_uri": self.redirect_uri or "",
            # Microsoft expects space-delimited scopes to be encoded as %20
            "scope": self.scope or "",
            "response_mode": "query",
        }
        if state:
            params["state"] = state
        # Properly encode query string (keep spaces as %20, not +)
        query_string = urlencode(params, quote_via=quote, safe="/:")
        return f"{base_url}?{query_string}"
    
    def exchange_code_for_token(self, code):
        """Exchange OAuth code for user access token"""
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
                
                # Extract tenant ID from user info
                tenant_id = user_info.get("tenantId") or self.tenant_id
                
                return {
                    "access_token": access_token,
                    "refresh_token": result.get("refresh_token"),
                    "scope": result.get("scope", ""),
                    "expires_in": result.get("expires_in"),
                    "tenant_id": tenant_id,
                    "user_id": user_info.get("id"),
                    "user_name": user_info.get("displayName"),
                    "tenant_name": user_info.get("companyName", "Unknown Organization")
                }
            else:
                print(f"❌ OAuth error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error exchanging code for token: {str(e)}")
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
    
    def save_user_token(self, user_id, token_data):
        """Save user token to database"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Update user's Teams connection status
            user.teams_connected = True
            user.teams_user_id = token_data["user_id"]
            user.teams_tenant_id = token_data["tenant_id"]
            user.teams_user_token = self.encrypt_token(token_data["access_token"])
            user.teams_scope = token_data["scope"]
            user.teams_authed_at = datetime.utcnow()
            
            db.session.commit()
            print(f"✅ Teams user token saved for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving user token: {str(e)}")
            db.session.rollback()
            return False
    
    def get_user_token(self, user_id):
        """Get decrypted user token"""
        try:
            user = User.query.get(user_id)
            if not user or not user.teams_user_token:
                return None
            
            return self.decrypt_token(user.teams_user_token)
            
        except Exception as e:
            print(f"❌ Error getting user token: {str(e)}")
            return None
    
    def send_message_as_user(self, user_token, team_id, channel_id, case_study, user_name=None):
        """Send a message to Teams as the user using their token"""
        try:
            # Create a Teams-formatted message
            message_content = self._create_teams_message(case_study, user_name)
            
            message = {
                "body": {
                    "contentType": "text",
                    "content": message_content
                }
            }
            
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Message sent as user successfully for case study: {case_study.title}")
                return {
                    "success": True,
                    "message_id": result.get("id"),
                    "createdDateTime": result.get("createdDateTime")
                }
            else:
                print(f"❌ Failed to send message: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            print(f"❌ Error sending message as user: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def post_message(self, user_token, team_id, channel_id, text):
        """Post a custom message to Teams using user token"""
        try:
            message = {
                "body": {
                    "contentType": "text",
                    "content": text
                }
            }
            
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("id"),
                    "createdDateTime": result.get("createdDateTime")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_teams(self, user_token):
        """Get teams the user has access to"""
        try:
            url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                teams = response.json().get("value", [])
                return [
                    {
                        "id": team["id"],
                        "name": team["displayName"],
                        "description": team.get("description", "")
                    }
                    for team in teams
                ]
            else:
                print(f"❌ Failed to get teams: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting teams: {str(e)}")
            return []
    
    def get_team_channels(self, user_token, team_id):
        """Get channels for a specific team"""
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
            headers = {
                "Authorization": f"Bearer {user_token}",
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
    
    def test_user_token(self, user_token):
        """Test if the user token is valid"""
        try:
            url = "https://graph.microsoft.com/v1.0/me"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error testing user token: {str(e)}")
            return False
    
    def _create_teams_message(self, case_study, user_name=None):
        """Create a Teams-formatted message from case study"""
        try:
            # Start with a header
            message_content = f"🎉 **New Success Story: {case_study.title}**\n\n"
            
            # Add personalized intro
            sender_name = user_name or "I"
            message_content += f"Hey team! {sender_name} here with an exciting success story to share:\n\n"
            
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
            print(f"❌ Error creating Teams message: {str(e)}")
            return f"🎉 **New Success Story: {case_study.title}**\n\nA new success story has been created and shared!"
