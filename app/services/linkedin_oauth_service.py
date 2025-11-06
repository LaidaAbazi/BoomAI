import os
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from app.models import db, User

class LinkedInOAuthService:
    def __init__(self):
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
        self.scope = "openid profile w_member_social"
        
        # LinkedIn API endpoints
        self.authorization_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.userinfo_url = "https://api.linkedin.com/v2/userinfo"
        self.ugc_post_url = "https://api.linkedin.com/v2/ugcPosts"
        
        # Encryption key for tokens
        self.encryption_key = os.getenv("LINKEDIN_TOKEN_ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a new key if none exists
            self.encryption_key = Fernet.generate_key()
            print(f"🔑 Generated new encryption key. Set LINKEDIN_TOKEN_ENCRYPTION_KEY={self.encryption_key.decode()}")
            print("⚠️  WARNING: Using temporary encryption key. Set LINKEDIN_TOKEN_ENCRYPTION_KEY environment variable for production!")
        else:
            # Convert string to bytes if needed
            if isinstance(self.encryption_key, str):
                self.encryption_key = self.encryption_key.encode()
        
        self.cipher = Fernet(self.encryption_key)
    
    def get_oauth_url(self, state=None):
        """
        Generate OAuth URL for user to authorize the app
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state
        }
        
        query_string = urlencode(params)
        return f"{self.authorization_url}?{query_string}"
    
    def exchange_code_for_token(self, code):
        """
        Exchange authorization code for access token
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(self.token_url, data=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get("access_token")
                if access_token:
                    return {
                        "access_token": access_token,
                        "refresh_token": result.get("refresh_token"),  # May be None if not requested
                        "expires_in": result.get("expires_in"),
                        "scope": result.get("scope")
                    }
                else:
                    print(f"❌ LinkedIn OAuth error: No access token in response")
                    return None
            else:
                print(f"❌ LinkedIn OAuth HTTP error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error exchanging code for token: {str(e)}")
            return None
    
    def get_user_info(self, access_token):
        """
        Get user information from LinkedIn using access token
        Returns the 'sub' (Member ID) needed for UGC posts
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(self.userinfo_url, headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                return {
                    "sub": user_info.get("sub"),  # Member ID
                    "name": user_info.get("name"),
                    "email": user_info.get("email")
                }
            else:
                print(f"❌ Failed to get user info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting user info: {str(e)}")
            return None
    
    def create_ugc_post(self, access_token, author_id, content):
        """
        Create a UGC (User Generated Content) post on LinkedIn
        author_id should be in format: urn:li:person:{sub}
        """
        try:
            # Format the author ID as LinkedIn URN
            if not author_id.startswith("urn:li:person:"):
                author_id = f"urn:li:person:{author_id}"
            
            # Prepare the UGC Post payload
            payload = {
                "author": author_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            response = requests.post(self.ugc_post_url, json=payload, headers=headers)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "message": "Post created successfully"
                }
            else:
                error_text = response.text
                print(f"❌ Failed to create UGC post: {response.status_code} - {error_text}")
                return {
                    "success": False,
                    "error": f"Failed to create post: {error_text}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            print(f"❌ Error creating UGC post: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def encrypt_token(self, token):
        """Encrypt a LinkedIn token for secure storage"""
        if not token:
            return None
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt a stored LinkedIn token"""
        if not encrypted_token:
            return None
        try:
            return self.cipher.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            print(f"❌ Error decrypting token: {str(e)}")
            return None
    
    def save_user_token(self, user_id, token_data, user_info=None):
        """
        Save LinkedIn token and user info to database
        token_data should contain: access_token, refresh_token (optional), expires_in, scope
        user_info should contain: sub (member_id), name (optional), email (optional)
        """
        import traceback
        try:
            # Validate inputs
            if not token_data or not token_data.get("access_token"):
                print(f"❌ Invalid token_data provided for user {user_id}")
                print(f"   token_data: {token_data}")
                return False
            
            if not user_info or not user_info.get("sub"):
                print(f"❌ Invalid user_info provided for user {user_id} (missing sub/member_id)")
                print(f"   user_info: {user_info}")
                return False
            
            print(f"🔍 Looking up user {user_id}...")
            user = User.query.get(user_id)
            if not user:
                print(f"❌ User {user_id} not found in database")
                return False
            
            print(f"✅ User found: {user.email}")
            
            # Encrypt access token
            print(f"🔐 Encrypting access token...")
            access_token_encrypted = self.encrypt_token(token_data.get("access_token"))
            if not access_token_encrypted:
                print(f"❌ Failed to encrypt access token for user {user_id}")
                return False
            print(f"✅ Token encrypted successfully")
            
            # Update user's LinkedIn connection status
            print(f"📝 Updating user fields...")
            user.linkedin_connected = True
            user.linkedin_member_id = user_info.get("sub")
            user.linkedin_access_token = access_token_encrypted
            
            # Handle refresh token if available
            refresh_token = token_data.get("refresh_token")
            if refresh_token:
                user.linkedin_refresh_token = self.encrypt_token(refresh_token)
                print(f"✅ Refresh token encrypted and saved")
            else:
                user.linkedin_refresh_token = None
                print(f"ℹ️  No refresh token provided")
            
            user.linkedin_scope = token_data.get("scope")
            user.linkedin_name = user_info.get("name")
            user.linkedin_email = user_info.get("email")
            
            # Calculate token expiration time
            expires_in = token_data.get("expires_in")
            if expires_in:
                try:
                    user.linkedin_token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
                    print(f"✅ Token expiration set: {user.linkedin_token_expires_at}")
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Invalid expires_in value: {expires_in}, error: {e}")
                    user.linkedin_token_expires_at = None
            else:
                user.linkedin_token_expires_at = None
                print(f"ℹ️  No expiration time provided")
            
            user.linkedin_authed_at = datetime.utcnow()
            
            # Flush to check for errors before commit
            print(f"💾 Flushing changes to database...")
            db.session.flush()
            print(f"✅ Flush successful, committing...")
            
            # Commit changes
            print(f"💾 Committing to database...")
            db.session.commit()
            print(f"✅ Commit successful!")
            
            # Verify the data was actually saved by refreshing and checking
            db.session.refresh(user)
            print(f"🔍 Verifying saved data...")
            print(f"   - linkedin_connected: {user.linkedin_connected}")
            print(f"   - linkedin_member_id: {user.linkedin_member_id}")
            print(f"   - linkedin_access_token: {'SET' if user.linkedin_access_token else 'NOT SET'}")
            print(f"   - linkedin_name: {user.linkedin_name}")
            print(f"   - linkedin_email: {user.linkedin_email}")
            print(f"   - linkedin_authed_at: {user.linkedin_authed_at}")
            
            print(f"✅ LinkedIn user token saved for user {user_id}")
            print(f"   - Member ID: {user_info.get('sub')}")
            print(f"   - Name: {user_info.get('name', 'N/A')}")
            print(f"   - Email: {user_info.get('email', 'N/A')}")
            print(f"   - Token expires: {user.linkedin_token_expires_at}")
            print(f"   - Connected: {user.linkedin_connected}")
            return True
            
        except AttributeError as e:
            # This likely means the database columns don't exist
            error_msg = str(e)
            print(f"❌ AttributeError saving LinkedIn token: {error_msg}")
            print(f"   This likely means the database columns don't exist yet.")
            print(f"   Please run a database migration to add LinkedIn fields to the users table.")
            print(f"   Full traceback:")
            traceback.print_exc()
            db.session.rollback()
            return False
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"❌ Error saving LinkedIn token ({error_type}): {error_msg}")
            print(f"   Full traceback:")
            traceback.print_exc()
            db.session.rollback()
            return False
    
    def get_user_token(self, user_id):
        """Get decrypted LinkedIn access token for user"""
        try:
            user = User.query.get(user_id)
            if not user or not user.linkedin_connected:
                return None
            
            # Check if token is expired
            if user.linkedin_token_expires_at and user.linkedin_token_expires_at < datetime.utcnow():
                print(f"⚠️ LinkedIn token expired for user {user_id}")
                # TODO: Implement token refresh if refresh_token is available
                return None
            
            return self.decrypt_token(user.linkedin_access_token)
            
        except Exception as e:
            print(f"❌ Error getting LinkedIn token: {str(e)}")
            return None
    
    def disconnect_linkedin(self, user_id):
        """Disconnect LinkedIn integration for user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            user.linkedin_connected = False
            user.linkedin_member_id = None
            user.linkedin_access_token = None
            user.linkedin_refresh_token = None
            user.linkedin_scope = None
            user.linkedin_name = None
            user.linkedin_email = None
            user.linkedin_token_expires_at = None
            user.linkedin_authed_at = None
            
            db.session.commit()
            print(f"✅ LinkedIn disconnected for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error disconnecting LinkedIn: {str(e)}")
            db.session.rollback()
            return False


