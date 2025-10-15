import os
import requests
import json
from datetime import datetime
from flask_mail import Message
from app import mail

class SlackInviteService:
    def __init__(self):
        self.slack_workspace = "storyboom"  # Your workspace name
        self.slack_token = os.getenv("SLACK_ADMIN_TOKEN")  # Admin token for invites
        self.channel_id = "C096U3ANE9M"  # Your actual channel ID
        self.workspace_url = f"https://{self.slack_workspace}.slack.com"
    
    def send_workspace_invite(self, user_email, user_name):
        """
        Send a Slack workspace invite to the user's email
        """
        try:
            # Method 1: Use Slack API to send invite (requires admin token)
            if self.slack_token:
                return self._send_slack_api_invite(user_email)
            
            # Method 2: Send email with invite link (fallback)
            # WARNING: This uses a public invite link - consider using admin API only
            return self._send_email_invite(user_email, user_name)
            
        except Exception as e:
            print(f" Error sending Slack invite: {str(e)}")
            return False
    
    def _send_slack_api_invite(self, user_email):
        """
        Send invite using Slack Admin API
        """
        try:
            url = "https://slack.com/api/admin.users.invite"
            headers = {
                "Authorization": f"Bearer {self.slack_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "email": user_email,
                "channel_ids": [self.channel_id],
                "restricted": False,
                "ultra_restricted": False
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f" Slack invite sent successfully to {user_email}")
                    return True
                else:
                    print(f" Slack API error: {result.get('error')}")
                    return False
            else:
                print(f" HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f" Error with Slack API invite: {str(e)}")
            return False
    
    def _send_email_invite(self, user_email, user_name):
        """
        Send email with Slack workspace invite link
        """
        try:
            # Create invite link (you'll need to generate this from Slack admin panel)
            # IMPORTANT: Generate a new invite link with domain restrictions
            invite_link = "https://join.slack.com/t/storyboom/shared_invite/zt-3a6990vw1-xypzVcrioXu7dHUEvinQtw"
            
            subject = " Join StoryBoom on Slack!"
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4A154B;"> Welcome to StoryBoom!</h2>
                
                <p>Hi {user_name},</p>
                
                <p>You've just created an amazing case study! We'd love for you to share it with the team on Slack.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #4A154B; margin-top: 0;">Join our Slack workspace:</h3>
                    <p>Connect with the team and share your success stories in the <strong>#all-storyboom</strong> channel!</p>
                    
                    <a href="{invite_link}" 
                       style="background-color: #4A154B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 10px 0;">
                        🚀 Join StoryBoom on Slack
                    </a>
                </div>
                
                <p><strong>What happens next?</strong></p>
                <ul>
                    <li>Click the button above to join our Slack workspace</li>
                    <li>Once you're in, you can share your case studies as yourself</li>
                    <li>Connect with the team and celebrate success stories together!</li>
                </ul>
                
                <p>If you have any questions, just reply to this email!</p>
                
                <p>Best regards,<br>The StoryBoom Team</p>
            </div>
            """
            
            # Send email
            msg = Message(
                subject=subject,
                recipients=[user_email],
                html=html_body
            )
            
            mail.send(msg)
            print(f" Email invite sent successfully to {user_email}")
            return True
            
        except Exception as e:
            print(f" Error sending email invite: {str(e)}")
            return False
    
    def get_workspace_info(self):
        """
        Get workspace information for invite links
        """
        return {
            "workspace_name": self.slack_workspace,
            "workspace_url": self.workspace_url,
            "channel_name": "#all-storyboom"
        } 