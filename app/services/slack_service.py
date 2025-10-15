import os
import requests
import json
from datetime import datetime
from app.services.ai_service import AIService

class SlackService:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.channel = "#all-storyboom"
        self.slack_workspace = "storyboom"  # Replace with your actual workspace name
        self.channel_id = "C096U3ANE9M"  # Replace with your actual channel ID
        self.ai_service = AIService()
    
    def get_channel_link(self):
        """
        Get the direct link to the Slack channel
        """
        return f"https://{self.slack_workspace}.slack.com/archives/{self.channel_id}"
    
    def send_case_study_notification(self, case_study, pdf_url=None, user_name=None, user_email=None):
        """
        Send a notification to Slack when a new case study is created
        
        Args:
            case_study: The case study object
            pdf_url: Optional URL to the PDF file
            user_name: Optional user name to display
            user_email: Optional user email for mentions
        """
        try:
            # Create a brief summary of the case study
            summary = self._create_case_study_summary(case_study)
            
            # Create user mention if email is provided
            user_mention = ""
            if user_email:
                user_mention = f"\n\n Created by: <mailto:{user_email}|{user_name or 'User'}>"
            
            # Create the Slack message
            message = {
                "channel": self.channel,
                "text": f" New Success Story Created!",
                "username": "StoryBoom AI",
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
                            "text": f"*{case_study.title}*\n\n{summary}{user_mention}"
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
                        "text": f" <{pdf_url}|See more>"
                    }
                })
            
            # Add a divider
            message["blocks"].append({
                "type": "divider"
            })
            
            # Send the message
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(message)
            )
            
            if response.status_code == 200:
                print(f" Slack notification sent successfully for case study: {case_study.title}")
                return True
            else:
                print(f" Failed to send Slack notification. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f" Error sending Slack notification: {str(e)}")
            return False
    
    def _create_case_study_summary(self, case_study):
        """
        Create a brief summary of the case study for Slack using OpenAI
        """
        if not case_study.final_summary:
            return "A new case study has been created but the final summary is not yet available."
        
        try:
            # Use OpenAI to generate a short, engaging summary
            prompt = f"""
            Create a brief, exciting summary of this case study for a Slack notification. 
            Make it engaging and highlight the key achievement. Keep it under 120 characters.
            
            Case Study: {case_study.final_summary[:800]}
            
            Write a compelling one-sentence summary that makes people want to read more.
            """
            
            # Use the AI service to generate the summary
            ai_summary = self.ai_service.generate_text(prompt, max_tokens=80)
            
            if ai_summary and len(ai_summary.strip()) > 0:
                return ai_summary.strip()
            else:
                # Fallback to simple truncation if AI fails
                summary = case_study.final_summary[:120]
                if len(case_study.final_summary) > 120:
                    summary += "..."
                return summary
                
        except Exception as e:
            print(f"Error generating AI summary for Slack: {str(e)}")
            # Fallback to simple truncation
            summary = case_study.final_summary[:120]
            if len(case_study.final_summary) > 120:
                summary += "..."
            return summary
    
    def send_test_message(self):
        """
        Send a test message to verify the webhook is working
        """
        try:
            message = {
                "channel": self.channel,
                "text": " Test message from StoryBoom AI Case Study Generator",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": " *Test Message*\n\nThis is a test message to verify the Slack integration is working correctly."
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(message)
            )
            
            if response.status_code == 200:
                print(" Test Slack message sent successfully")
                return True
            else:
                print(f" Failed to send test Slack message. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending test Slack message: {str(e)}")
            return False 