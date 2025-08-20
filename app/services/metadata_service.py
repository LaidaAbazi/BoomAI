import os
import json
import re
import uuid
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.services.ai_service import AIService

class MetadataService:
    def __init__(self):
        self.output_dir = "generated_pdfs"
        os.makedirs(self.output_dir, exist_ok=True)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ai_service = AIService()
        
    def extract_and_remove_metadata_sections(self, text: str, client_summary: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Extract metadata sections from the main story and return cleaned text + metadata.
        
        Args:
            text: The full case study text
            client_summary: Optional client summary for additional analysis
            
        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        # Patterns to extract meta sections
        quotes_pattern = r"(?:\*\*|__)?Quotes? Highlights(?:\*\*|__)?\s*[\r\n\-:]*([\s\S]*?)(?=(?:\*\*|__)?[A-Z][^:]*:|$)"
        
        # Extract meta sections
        quotes_match = re.search(quotes_pattern, text, re.IGNORECASE | re.DOTALL)
        
        quote_highlights = quotes_match.group(1).strip() if quotes_match else ""

        # Fallback: if quote_highlights is empty, try to extract blockquotes or bulleted quotes
        if not quote_highlights:
            # Try to extract lines like: - **Client:** "Quote here..."
            blockquote_lines = re.findall(r'- \*\*(Client|Provider)\*\*:\s*["""]([\s\S]*?)["""]', text)
            if blockquote_lines:
                quote_highlights = "\n".join(f'- **{who}:** "{q.strip()}"' for who, q in blockquote_lines)
            else:
                # Fallback: extract multi-line quotes between quotes
                multiline_quotes = re.findall(r'["""]([\s\S]*?)["""]', text)
                if multiline_quotes:
                    quote_highlights = "\n".join(f'- "{q.strip()}"' for q in multiline_quotes)
                elif client_summary:
                    # Draft a quote from the client summary
                    drafted = self.draft_quote_from_summary(client_summary, speaker="Client")
                    quote_highlights = f'- "{drafted}"'

        # Remove meta sections from the main story
        text = re.sub(quotes_pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        
        # Extract key takeaways
        client_takeaways = self.extract_client_takeaways(client_summary) if client_summary else ""

        # Ensure sentiment analysis is included in meta data
        print(f"🔍 About to analyze sentiment for client summary: {bool(client_summary)}")
        if client_summary:
            print(f"🔍 Client summary length: {len(client_summary)}")
            print(f"🔍 Client summary preview: {client_summary[:100]}...")
        
        sentiment = self.analyze_sentiment(client_summary) if client_summary else {}
        
        print(f"🔍 Sentiment analysis result: {bool(sentiment)}")
        if sentiment:
            print(f"🔍 Sentiment keys: {list(sentiment.keys())}")
            print(f"🔍 Has visualizations: {bool(sentiment.get('visualizations'))}")
            if sentiment.get('visualizations'):
                viz = sentiment['visualizations']
                print(f"🔍 Sentiment chart img: {viz.get('sentiment_chart_img', 'missing')}")
                print(f"🔍 Client satisfaction gauge: {bool(viz.get('client_satisfaction_gauge'))}")

        return text.strip(), {
            "quote_highlights": quote_highlights,
            "sentiment": sentiment,
            "client_takeaways": client_takeaways,
        }

    def extract_client_takeaways(self, client_summary: str) -> str:
        """Extract key takeaways from client interview using OpenAI."""
        try:
            prompt = f"""
            Analyze the following client interview summary and extract the 3-5 most important key takeaways.
            Focus on:
            - Main pain points or challenges they faced
            - Most valued aspects of the solution
            - Key benefits or improvements they experienced
            - Their overall satisfaction level
            - Any specific metrics or results they mentioned

            Format the response as a bullet-point list.

            Client Summary:
            {client_summary}
            """

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4",
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, 
                                  json=payload)
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error extracting client takeaways: {str(e)}")
            return "Unable to extract key takeaways."

    def generate_sentiment_chart(self, sentiment_score: float) -> bytes:
        """Generate sentiment visualization chart and return as bytes"""
        try:
            print(f"🔍 Generating sentiment chart for score: {sentiment_score}")
            
            # Create a simple horizontal bar chart for sentiment
            fig, ax = plt.subplots(figsize=(4, 1.5))
            color = 'green' if sentiment_score > 6 else 'yellow' if sentiment_score > 4 else 'red'
            ax.barh(['Sentiment'], [sentiment_score], color=color)
            ax.set_xlim(0, 10)
            ax.set_xlabel('Score (0-10)')
            ax.set_title('Sentiment Score')
            plt.tight_layout()
            
            # Save to bytes buffer instead of file
            import io
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            # Get the bytes
            chart_bytes = buffer.getvalue()
            buffer.close()
            
            print(f"🔍 Chart generated successfully, size: {len(chart_bytes)} bytes")
            return chart_bytes
        except Exception as e:
            print(f"❌ Error generating sentiment chart: {str(e)}")
            import traceback
            traceback.print_exc()
            return b""

    def extract_client_satisfaction(self, client_summary: str) -> Dict[str, str]:
        """Extract client satisfaction metrics from summary"""
        try:
            # Define categories and keywords
            categories = [
                ("Very Bad", ["terrible", "awful", "horrible", "very disappointed", "extremely dissatisfied", "never again", "worst"]),
                ("Bad", ["bad", "disappointed", "dissatisfied", "not happy", "not satisfied", "issues", "problems", "concerns"]),
                ("Neutral", ["okay", "neutral", "average", "fine", "acceptable", "neither good nor bad"]),
                ("Good", ["good", "satisfied", "happy", "pleased", "helpful", "positive", "recommend", "valuable", "improved", "great help"]),
                ("Very Good", ["excellent", "outstanding", "amazing", "fantastic", "very happy", "very satisfied", "delighted", "impressed", "exceptional", "game changer", "highly recommend", "best"])
            ]
            
            summary_lower = client_summary.lower()
            found_category = "Neutral"
            
            for cat, keywords in categories:
                for kw in keywords:
                    if kw in summary_lower:
                        found_category = cat
                        break
                if found_category != "Neutral":
                    break

            # Try to extract a satisfaction sentence
            satisfaction_sentence = ""
            for cat, keywords in categories:
                for kw in keywords:
                    match = re.search(r'([^.]*\b' + re.escape(kw) + r'\b[^.]*)\.', client_summary, re.IGNORECASE)
                    if match:
                        satisfaction_sentence = match.group(1).strip()
                        break
                if satisfaction_sentence:
                    break

            return {
                "category": found_category,
                "statement": satisfaction_sentence or "No explicit satisfaction statement found."
            }
        except Exception as e:
            print(f"Error extracting client satisfaction: {str(e)}")
            return {
                "category": "Neutral",
                "statement": "No explicit satisfaction statement found."
            }

    def generate_client_satisfaction_gauge(self, category: str) -> str:
        """Generate client satisfaction gauge chart using Plotly"""
        try:
            # Map categories to values and colors for the gauge
            category_map = {
                "Very Bad": (1, "#ef4444"),
                "Bad": (3, "#f59e42"),
                "Neutral": (5, "#fbbf24"),
                "Good": (7, "#a3e635"),
                "Very Good": (9, "#22c55e")
            }
            value, color = category_map.get(category, (5, "#fbbf24"))
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                number={'valueformat': '', 'font': {'size': 1}, 'suffix': ''},  # Hide the number
                title={'text': f"Client Satisfaction: <b>{category}</b>", 'font': {'size': 22}},
                gauge={
                    'axis': {'range': [0, 10], 'tickvals': [1, 3, 5, 7, 9], 'ticktext': ["Very Bad", "Bad", "Neutral", "Good", "Very Good"], 'tickwidth': 2, 'tickcolor': "#888"},
                    'bar': {'color': color, 'thickness': 0.3},
                    'steps': [
                        {'range': [0, 2], 'color': "#ef4444"},
                        {'range': [2, 4], 'color': "#f59e42"},
                        {'range': [4, 6], 'color': "#fbbf24"},
                        {'range': [6, 8], 'color': "#a3e635"},
                        {'range': [8, 10], 'color': "#22c55e"},
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 8},
                        'thickness': 0.9,
                        'value': value
                    }
                }
            ))
            fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))
            return fig.to_json()
        except Exception as e:
            print(f"Error generating client satisfaction gauge: {str(e)}")
            return ""

    def analyze_sentiment(self, client_summary: str) -> Dict[str, Any]:
        """Analyze sentiment of client summary"""
        try:
            print(f"🔍 Starting sentiment analysis for text length: {len(client_summary)}")
            analyzer = SentimentIntensityAnalyzer()
            scores = analyzer.polarity_scores(client_summary)
            compound = scores['compound']
            
            print(f"🔍 VADER scores: {scores}")
            print(f"🔍 Compound score: {compound}")
            
            if compound >= 0.05:
                sentiment = "positive"
            elif compound <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            print(f"🔍 Determined sentiment: {sentiment}")

            final_analysis = {
                "overall_sentiment": {
                    "sentiment": sentiment,
                    "confidence": abs(compound),
                    "score": round((compound + 1) * 5, 2)  # scale -1..1 to 0..10
                },
                "emotional_analysis": {
                    "primary_emotion": sentiment,
                    "secondary_emotions": [],
                    "emotional_intensity": max(scores['pos'], scores['neg'])
                },
                "key_points": {
                    "positive": [],
                    "negative": []
                },
                "metrics": [],
                "satisfaction": {
                    "score": 0,
                    "confidence": abs(compound),
                    "key_factors": [],
                    "statement": ""
                },
                "visualizations": {}
            }
            
            # Generate and attach the sentiment chart image
            sentiment_score = final_analysis["overall_sentiment"]["score"]
            print(f"🔍 Generating sentiment chart for score: {sentiment_score}")
            
            try:
                chart_bytes = self.generate_sentiment_chart(sentiment_score)
                print(f"🔍 Chart bytes generated: {len(chart_bytes)} bytes")
                if chart_bytes:
                    # Store chart bytes in the case study (will be saved by the caller)
                    final_analysis["visualizations"]["sentiment_chart_data"] = chart_bytes
                    # Don't set a placeholder URL - it will be set by the caller after we have the case study ID
                    # final_analysis["visualizations"]["sentiment_chart_img"] = "PENDING_CASE_STUDY_ID"
                    print(f"🔍 Added sentiment chart to visualizations")
                else:
                    print("❌ Chart bytes are empty")
            except Exception as chart_error:
                print(f"❌ Error generating sentiment chart: {str(chart_error)}")
                import traceback
                traceback.print_exc()

            # Add client satisfaction analysis
            print(f"🔍 Extracting client satisfaction...")
            satisfaction_info = self.extract_client_satisfaction(client_summary)
            final_analysis["satisfaction"]["category"] = satisfaction_info["category"]
            final_analysis["satisfaction"]["statement"] = satisfaction_info["statement"]
            print(f"🔍 Satisfaction category: {satisfaction_info['category']}")

            # Generate and attach the Plotly gauge for client satisfaction
            print(f"🔍 Generating client satisfaction gauge...")
            try:
                gauge_json = self.generate_client_satisfaction_gauge(satisfaction_info["category"])
                print(f"🔍 Gauge JSON generated: {bool(gauge_json)}")
                if gauge_json:
                    final_analysis["visualizations"]["client_satisfaction_gauge"] = gauge_json
                    print(f"🔍 Added satisfaction gauge to visualizations")
                else:
                    print("❌ Gauge JSON is empty")
            except Exception as gauge_error:
                print(f"❌ Error generating satisfaction gauge: {str(gauge_error)}")
                import traceback
                traceback.print_exc()

            print(f"🔍 Final analysis complete. Visualizations: {list(final_analysis['visualizations'].keys())}")
            return final_analysis
        except Exception as e:
            print(f"❌ Error in sentiment analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "overall_sentiment": {
                    "sentiment": "unknown",
                    "confidence": 0,
                    "score": 0
                },
                "emotional_analysis": {
                    "primary_emotion": "unknown",
                    "secondary_emotions": [],
                    "emotional_intensity": 0
                },
                "key_points": {
                    "positive": [],
                    "negative": []
                },
                "metrics": [],
                "satisfaction": {
                    "score": 0,
                    "confidence": 0,
                    "key_factors": [],
                    "statement": "No explicit satisfaction statement found."
                },
                "visualizations": {}
            }

    def draft_quote_from_summary(self, summary: str, speaker: str = "Client") -> str:
        """Simple template-based fallback if OpenAI is not available"""
        return f"As a {speaker.lower()}, I can say this project made a real difference for us. We're very happy with the results."

    def extract_quotes_from_text(self, text: str) -> list:
        """Extract quotes from text using regex patterns"""
        try:
            # Pattern to match quoted text
            quote_pattern = r'["""]([^"""]+)["""]'
            quotes = re.findall(quote_pattern, text)
            
            # Also look for bullet-pointed quotes
            bullet_quotes = re.findall(r'- \*\*(Client|Provider)\*\*:\s*["""]([^"""]+)["""]', text)
            
            all_quotes = []
            for quote in quotes:
                all_quotes.append({"text": quote.strip(), "speaker": "Unknown"})
            
            for speaker, quote in bullet_quotes:
                all_quotes.append({"text": quote.strip(), "speaker": speaker})
            
            return all_quotes
        except Exception as e:
            print(f"Error extracting quotes: {str(e)}")
            return []

    def generate_metadata_summary(self, case_study_text: str, client_summary: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for a case study.
        
        Args:
            case_study_text: The main case study text
            client_summary: Optional client summary for additional analysis
            
        Returns:
            Dictionary containing all metadata
        """
        try:
            # Extract main story and metadata sections
            main_story, metadata = self.extract_and_remove_metadata_sections(case_study_text, client_summary)
            
            # Extract quotes from the main story
            quotes = self.extract_quotes_from_text(main_story)
            metadata["extracted_quotes"] = quotes
            
            # Add analysis timestamp
            metadata["analysis_timestamp"] = datetime.now().isoformat()
            
            # Add word count and reading time estimates
            metadata["text_metrics"] = {
                "word_count": len(main_story.split()),
                "character_count": len(main_story),
                "estimated_reading_time_minutes": max(1, len(main_story.split()) // 200)  # 200 words per minute
            }
            
            return metadata
        except Exception as e:
            print(f"Error generating metadata summary: {str(e)}")
            return {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            } 