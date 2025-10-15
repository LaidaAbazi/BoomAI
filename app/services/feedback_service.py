import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models import Feedback, db
from app.services.ai_service import AIService

class FeedbackService:
    def __init__(self):
        self.ai_service = AIService()
    
    def analyze_single_feedback(self, feedback_content: str, rating: int = None, feedback_type: str = "general") -> str:
        """Analyze a single feedback and generate a summary"""
        try:
            if not self.ai_service.openai_api_key:
                return "AI analysis not available. Manual review required."
            
            # Validate input
            if not feedback_content or not feedback_content.strip():
                return "No feedback content provided for analysis."
            
            # Create context for the AI
            context_parts = []
            if feedback_type and feedback_type != "general":
                context_parts.append(f"Type: {feedback_type}")
            if rating is not None:
                context_parts.append(f"Rating: {rating}/5")
            
            context = "\n".join(context_parts) if context_parts else "General feedback"
            context += f"\nFeedback: {feedback_content.strip()}"
            
            # Simplified, more natural prompt
            prompt = f"""You are analyzing user feedback for a business application. Here's the feedback:

{context}

Please provide a brief, helpful summary that captures:
- What the user is saying (main points)
- How they feel about it (sentiment)
- Whether it's something actionable
- What area of the product this relates to

Write this as a natural paragraph, not a structured list. Be specific and reference the actual content the user provided. If the feedback is unclear or minimal, say so directly."""

            headers = {
                "Authorization": f"Bearer {self.ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.ai_service.openai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"OpenAI API error in single feedback analysis: {response.status_code} - {response.text}")
                return "Failed to analyze feedback. Please review manually."
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                return "Failed to analyze feedback. Please review manually."
                
        except Exception as e:
            print(f"Error analyzing single feedback: {str(e)}")
            return "Error analyzing feedback. Please review manually."
    
    def generate_comprehensive_feedback_summary(self, all_feedbacks: List[Feedback]) -> str:
        """Generate a comprehensive summary of all feedback collected"""
        try:
            if not all_feedbacks:
                return "No feedback available for analysis."
            
            if not self.ai_service.openai_api_key:
                return "AI analysis not available. Manual review required."
            
            # Prepare feedback data for analysis - focus on content, not structure
            feedback_texts = []
            for i, feedback in enumerate(all_feedbacks, 1):
                feedback_text = f"Feedback #{i}:\n"
                if feedback.rating:
                    feedback_text += f"Rating: {feedback.rating}/5\n"
                if feedback.feedback_type and feedback.feedback_type != "general":
                    feedback_text += f"Type: {feedback.feedback_type}\n"
                feedback_text += f"Content: {feedback.content}\n"
                feedback_text += f"Date: {feedback.created_at.strftime('%Y-%m-%d')}\n"
                feedback_texts.append(feedback_text)
            
            # Combine all feedback into a single text block
            all_feedback_text = "\n---\n".join(feedback_texts)
            
            # Simplified, more conversational prompt
            prompt = f"""You are analyzing user feedback for a business application. Here are {len(all_feedbacks)} pieces of feedback from users:

{all_feedback_text}

Please analyze this feedback and provide a comprehensive summary that covers:

1. What users are saying overall - what are the main themes and patterns?
2. What are users happy about or what's working well?
3. What problems or issues are users reporting?
4. What suggestions or requests are users making?
5. What should be prioritized based on the feedback?

Write this as a clear, actionable summary that helps the development team understand what users need. Be specific and reference actual feedback when possible. If there are conflicting opinions or mixed signals, mention that."""

            headers = {
                "Authorization": f"Bearer {self.ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.ai_service.openai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1500
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"OpenAI API error in comprehensive analysis: {response.status_code} - {response.text}")
                return "Failed to generate comprehensive feedback summary. Please review feedback manually."
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                return "Failed to generate comprehensive feedback summary. Please review feedback manually."
                
        except Exception as e:
            print(f"Error generating comprehensive feedback summary: {str(e)}")
            return "Error generating comprehensive feedback summary. Please review feedback manually."
    
    def get_feedback_statistics(self, all_feedbacks: List[Feedback]) -> Dict[str, Any]:
        """Get statistical overview of feedback"""
        if not all_feedbacks:
            return {
                'total_feedback': 0,
                'average_rating': 0,
                'rating_distribution': {},
                'feedback_type_distribution': {},
                'recent_feedback_count': 0
            }
        
        # Calculate statistics
        total_feedback = len(all_feedbacks)
        ratings = [f.rating for f in all_feedbacks if f.rating is not None]
        average_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Rating distribution
        rating_distribution = {}
        for rating in range(1, 6):
            rating_distribution[rating] = len([f for f in all_feedbacks if f.rating == rating])
        
        # Feedback type distribution
        feedback_type_distribution = {}
        for feedback in all_feedbacks:
            feedback_type = feedback.feedback_type or 'general'
            feedback_type_distribution[feedback_type] = feedback_type_distribution.get(feedback_type, 0) + 1
        
        # Recent feedback (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_feedback_count = len([f for f in all_feedbacks if f.created_at >= week_ago])
        
        return {
            'total_feedback': total_feedback,
            'average_rating': round(average_rating, 2),
            'rating_distribution': rating_distribution,
            'feedback_type_distribution': feedback_type_distribution,
            'recent_feedback_count': recent_feedback_count
        }
    
    def update_feedback_summary(self, feedback_id: int) -> bool:
        """Update the summary for a specific feedback entry"""
        try:
            feedback = Feedback.query.get(feedback_id)
            if not feedback:
                return False
            
            summary = self.analyze_single_feedback(
                feedback.content, 
                feedback.rating, 
                feedback.feedback_type
            )
            
            feedback.feedback_summary = summary
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"Error updating feedback summary: {str(e)}")
            db.session.rollback()
            return False 
