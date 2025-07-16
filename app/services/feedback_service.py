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
            
            # Create context for the AI
            context = f"Feedback Type: {feedback_type}\n"
            if rating:
                context += f"Rating: {rating}/5\n"
            context += f"Feedback Content: {feedback_content}\n"
            
            prompt = f"""Analyze this user feedback and provide a concise summary that captures:

1. **Main Points**: Key issues, suggestions, or positive feedback mentioned
2. **Sentiment**: Overall tone (positive, negative, neutral, mixed)
3. **Actionability**: Whether the feedback is actionable and specific
4. **Priority**: High, medium, or low priority based on content and rating
5. **Category**: What aspect of the product/service this feedback relates to

Context:
{context}

Provide a clear, concise summary in 2-3 sentences that captures the essence of this feedback for quick review and action planning."""

            headers = {
                "Authorization": f"Bearer {self.ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.ai_service.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code != 200:
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
            
            # Prepare feedback data for analysis
            feedback_data = []
            for feedback in all_feedbacks:
                feedback_data.append({
                    'content': feedback.content,
                    'rating': feedback.rating,
                    'type': feedback.feedback_type,
                    'date': feedback.created_at.strftime('%Y-%m-%d'),
                    'summary': feedback.feedback_summary or "No summary available"
                })
            
            # Create comprehensive analysis prompt
            prompt = f"""Analyze all the collected feedback and provide a comprehensive summary report. 

Total feedback entries: {len(feedback_data)}

Feedback Data:
{json.dumps(feedback_data, indent=2, default=str)}

Please provide a detailed analysis covering:

**EXECUTIVE SUMMARY**
- Overall sentiment across all feedback
- Key themes and patterns identified
- Most common issues or positive points

**DETAILED ANALYSIS**
1. **Positive Feedback**: What users like and appreciate
2. **Negative Feedback**: Issues, problems, and pain points
3. **Suggestions & Improvements**: User recommendations and ideas
4. **Feature Requests**: New functionality users want
5. **Usability Issues**: Interface, workflow, or user experience problems

**PATTERNS & TRENDS**
- Recurring themes across multiple users
- Rating patterns and correlations
- Feedback type distribution
- Time-based patterns if any

**ACTIONABLE INSIGHTS**
- High-priority issues that need immediate attention
- Quick wins that can be implemented easily
- Long-term improvements to consider
- User satisfaction drivers

**RECOMMENDATIONS**
- Immediate actions (next 1-2 weeks)
- Short-term improvements (next 1-2 months)
- Long-term considerations (next 3-6 months)

Provide a comprehensive, actionable report that helps prioritize development and improvement efforts."""

            headers = {
                "Authorization": f"Bearer {self.ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.ai_service.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code != 200:
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