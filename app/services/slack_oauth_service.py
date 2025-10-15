import os
import requests
import json
from datetime import datetime

class SlackOAuthService:
    def __init__(self):
        self.client_id = os.getenv("SLACK_CLIENT_ID")
        self.client_secret = os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SLACK_REDIRECT_URI", "https://2b670ee75077.ngrok-free.app/api/slack/oauth/callback")
        self.scope = "chat:write,channels:read,groups:read,im:read,mpim:read"
        self.user_scope = "chat:write,channels:read,groups:read,im:read,mpim:read"
    
    def get_oauth_url(self, state=None):
        """
        Generate OAuth URL for user to authorize the app
        """
        base_url = "https://slack.com/oauth/v2/authorize"
        params = {
            "client_id": self.client_id,
            "scope": self.scope,
            "redirect_uri": self.redirect_uri,
            "user_scope": self.user_scope
        }
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    def exchange_code_for_token(self, code):
        """
        Exchange authorization code for access token
        """
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
                    return {
                        "access_token": result["access_token"],
                        "user_id": result["authed_user"]["id"],
                        "team_id": result["team"]["id"],
                        "scope": result["authed_user"].get("scope", ""),
                        "authed_at": datetime.utcnow()
                    }
                else:
                    print(f" OAuth error: {result.get('error')}")
                    return None
            else:
                print(f" HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f" Error exchanging code for token: {str(e)}")
            return None
    
    def send_message_as_user(self, user_token, channel, case_study, pdf_url=None, user_name=None):
        """
        Send a message to Slack as the user using their token
        """
        try:
            # Create a simple, clean message
            message = {
                "channel": channel,
                "text": f" New Success Story: {case_study.title}",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": " New Success Story Created!"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{case_study.title}*\n\n{self._create_simple_summary(case_study)}"
                        }
                    }
                ]
            }
            
            # Add PDF link if available
            if pdf_url:
                message["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f" <{pdf_url}|View Full Case Study>"
                    }
                })
            
            # Send the message using user's token
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f" Message sent as user successfully for case study: {case_study.title}")
                    return True
                else:
                    error = result.get('error')
                    print(f" Slack API error: {error}")
                    
                    # Handle specific errors
                    if error == "not_in_channel":
                        print(" User is not in the channel. They need to join the channel first.")
                        return False
                    elif error == "channel_not_found":
                        print(" Channel not found. Check channel name.")
                        return False
                    else:
                        return False
            else:
                print(f" HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f" Error sending message as user: {str(e)}")
            return False
    
    def post_message(self, user_token, channel, text, blocks=None):
        """
        Post a custom message to Slack (for the API endpoint)
        """
        try:
            message = {
                "channel": channel,
                "text": text
            }
            
            # Add blocks if provided
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
    
    def _create_simple_summary(self, case_study):
        """
        Create a simple summary of the case study
        """
        if not case_study.final_summary:
            return "A new case study has been created."
        
        # Take first 200 characters and add ellipsis if longer
        summary = case_study.final_summary[:200]
        if len(case_study.final_summary) > 200:
            summary += "..."
        
        return summary

    def get_user_conversations(self, user_token):
        """
        Get list of conversations the user has access to using conversations.list
        This is the recommended API method for getting all conversation types
        """
        try:
            url = "https://slack.com/api/conversations.list"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "types": "public_channel,private_channel,im,mpim",
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
                        if conv.get("is_member"):
                            conversations.append({
                                "id": conv["id"],
                                "name": conv["name"],
                                "type": "public_channel",
                                "is_private": False,
                                "is_archived": conv.get("is_archived", False)
                            })
                    
                    # Process private channels
                    for conv in result.get("groups", []):
                        if conv.get("is_member"):
                            conversations.append({
                                "id": conv["id"],
                                "name": conv["name"],
                                "type": "private_channel",
                                "is_private": True,
                                "is_archived": conv.get("is_archived", False)
                            })
                    
                    # Process DMs
                    for conv in result.get("ims", []):
                        if conv.get("is_im") and not conv.get("is_user_deleted"):
                            conversations.append({
                                "id": conv["id"],
                                "name": f"DM with {conv.get('user', 'Unknown')}",
                                "type": "im",
                                "is_private": True,
                                "is_archived": False
                            })
                    
                    # Process multi-person DMs
                    for conv in result.get("mpims", []):
                        if conv.get("is_mpim"):
                            conversations.append({
                                "id": conv["id"],
                                "name": conv.get("name", "Group DM"),
                                "type": "mpim",
                                "is_private": True,
                                "is_archived": False
                            })
                    
                    print(f" Found {len(conversations)} conversations for user")
                    return conversations
                else:
                    error = result.get('error')
                    print(f" Slack API error getting conversations: {error}")
                    
                    if error == "missing_scope":
                        print(" Missing required scopes. Need: channels:read, groups:read, im:read, mpim:read")
                    elif error == "token_revoked":
                        print(" User token has been revoked")
                    elif error == "token_expired":
                        print(" User token has expired")
                    
                    return []
            else:
                print(f" HTTP error getting conversations: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except Exception as e:
            print(f" Error getting user conversations: {str(e)}")
            return []

    def get_channel_message_url(self, channel_id):
        """
        Generate a URL that opens Slack channel
        """
        return f"https://storyboom.slack.com/archives/{channel_id}" 