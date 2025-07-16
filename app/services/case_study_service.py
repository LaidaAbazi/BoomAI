import os
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import io
import base64
from datetime import datetime
from fpdf import FPDF
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from docx import Document
from docx.shared import Inches
import json
import re
import uuid
import requests
from app.models import db, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken
from app.services.ai_service import AIService
from app.services.metadata_service import MetadataService
from app.utils.text_processing import clean_text, detect_language
from io import BytesIO

class CaseStudyService:
    def __init__(self):
        self.output_dir = "generated_pdfs"
        os.makedirs(self.output_dir, exist_ok=True)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_config = {
            "model": "gpt-4",
            "temperature": 0.5,
            "top_p": 0.9,
            "presence_penalty": 0.2,
            "frequency_penalty": 0.2
        }
        self.metadata_service = MetadataService()
    
    def generate_pdf(self, case_study):
        """Generate PDF from case study and store in DB"""
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Case Study Report", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", "", 12)
            if case_study.final_summary:
                paragraphs = case_study.final_summary.split('\n\n')
                for paragraph in paragraphs:
                    if paragraph.strip():
                        lines = paragraph.split('\n')
                        for line in lines:
                            if line.strip():
                                pdf.multi_cell(0, 5, line.strip())
                        pdf.ln(5)
            pdf_buffer = BytesIO()
            pdf.output(pdf_buffer, 'S')
            case_study.final_summary_pdf_data = pdf_buffer.getvalue()
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return False
    
    def generate_word_document(self, case_study):
        """Generate Word document from case study"""
        try:
            # Create document
            doc = Document()
            
            # Title
            title = doc.add_heading('Case Study Report', 0)
            title.alignment = 1  # Center alignment
            
            # Add content
            if case_study.final_summary:
                paragraphs = case_study.final_summary.split('\n\n')
                
                for paragraph in paragraphs:
                    if paragraph.strip():
                        doc.add_paragraph(paragraph.strip())
                        doc.add_paragraph()  # Add spacing
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"case_study_{timestamp}.docx"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save document
            doc.save(filepath)
            
            return filepath
            
        except Exception as e:
            print(f"Error generating Word document: {str(e)}")
            return None
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text using the metadata service"""
        return self.metadata_service.analyze_sentiment(text)
    
    def generate_sentiment_chart(self, sentiment_score, output_dir="generated_pdfs"):
        """Generate sentiment visualization chart using the metadata service"""
        return self.metadata_service.generate_sentiment_chart(sentiment_score, output_dir)
    
    def extract_client_satisfaction(self, client_summary):
        """Extract client satisfaction metrics from summary using the metadata service"""
        return self.metadata_service.extract_client_satisfaction(client_summary)
    
    def generate_client_satisfaction_gauge(self, category):
        """Generate client satisfaction gauge chart"""
        try:
            # Map categories to values and colors
            category_mapping = {
                'very_satisfied': {'value': 100, 'color': '#28a745'},
                'satisfied': {'value': 75, 'color': '#17a2b8'},
                'neutral': {'value': 50, 'color': '#ffc107'},
                'dissatisfied': {'value': 25, 'color': '#fd7e14'},
                'very_dissatisfied': {'value': 0, 'color': '#dc3545'}
            }
            
            mapping = category_mapping.get(category, {'value': 50, 'color': '#ffc107'})
            
            # Create gauge chart
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = mapping['value'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Client Satisfaction"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': mapping['color']},
                    'steps': [
                        {'range': [0, 20], 'color': "lightgray"},
                        {'range': [20, 40], 'color': "lightgray"},
                        {'range': [40, 60], 'color': "lightgray"},
                        {'range': [60, 80], 'color': "lightgray"},
                        {'range': [80, 100], 'color': "lightgray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"satisfaction_gauge_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save chart
            fig.write_html(filepath)
            
            return filepath
            
        except Exception as e:
            print(f"Error generating satisfaction gauge: {str(e)}")
            return None
    
    def extract_client_takeaways(self, client_summary):
        """Extract key takeaways from client interview using the metadata service."""
        return self.metadata_service.extract_client_takeaways(client_summary)

    def extract_and_remove_metadata_sections(self, text, client_summary=None):
        """Extract and remove metadata sections from text using the metadata service"""
        return self.metadata_service.extract_and_remove_metadata_sections(text, client_summary)

    def create_case_study(self, user_id, title, final_summary=None):
        """Create a new case study"""
        try:
            case_study = CaseStudy(
                user_id=user_id,
                title=title,
                final_summary=final_summary
            )
            db.session.add(case_study)
            db.session.commit()
            return case_study
        except Exception as e:
            db.session.rollback()
            raise e

    def get_case_study(self, case_study_id, user_id):
        """Get a case study by ID for a specific user"""
        return CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()

    def update_case_study(self, case_study_id, user_id, **kwargs):
        """Update a case study"""
        try:
            case_study = self.get_case_study(case_study_id, user_id)
            if not case_study:
                return None
            
            for key, value in kwargs.items():
                if hasattr(case_study, key):
                    setattr(case_study, key, value)
            
            db.session.commit()
            return case_study
        except Exception as e:
            db.session.rollback()
            raise e

    def delete_case_study(self, case_study_id, user_id):
        """Delete a case study"""
        try:
            case_study = self.get_case_study(case_study_id, user_id)
            if not case_study:
                return False
            
            db.session.delete(case_study)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    def generate_full_case_study(self, provider_summary, client_summary, detected_language, has_client_story):
        """Generate the complete final case study with advanced features from reference"""
        try:
            if has_client_story:
                # Original prompt for when both provider and client stories exist
                full_prompt = f"""
                You are a top-tier business case study writer, creating professional, detailed, and visually attractive stories for web or PDF (inspired by Storydoc, Adobe, and top SaaS companies).
 
                IMPORTANT: Write the entire case study in {detected_language}. This includes all sections, quotes, and any additional content.
 
                Your task is to read the full Solution Provider and Client summaries below and merge them into a single, rich, multi-perspective case study. You must synthesize the insights, stories, and data into one engaging narrative.
 
                ---

                **Instructions:**
                - The **Solution Provider version is your base**; the Client version should *enhance, correct, or add* to it.
                - If the client provides a correction, update, or different number/fact for something from the provider, ALWAYS use the client's corrected version in the main story (unless it is unclear; then flag for review).
                - In the "Corrected & Conflicted Replies" section, list each specific fact, number, or point that the client corrected, changed, or disagreed with.
                - Accuracy is CRITICAL: Double-check every fact, number, quote, and piece of information. Do NOT make any mistakes or subtle errors in the summary. Every detail must match the input summaries exactly unless you are synthesizing clearly from both. If you are unsure about a detail, do NOT invent or guess; either omit or flag it for clarification.
                - If the Client provided information that contradicts, corrects, or expands on the Provider's version, **create a special section titled "Corrected & Conflicted Replies"**. In this section, briefly and clearly list the key areas where the Client said something different, added, corrected, or removed a point. This should be a concise summary (bullets or short sentences) so the provider can easily see what changed.
                - In the main story, **merge and synthesize all available details and insights** from both the Solution Provider and Client summaries: background, challenges, solutions, process, collaboration, data, quotes, and results. Do not repeat information—combine and paraphrase to build a seamless narrative.
                - **Quotes:**  
                    - Include exactly ONE impactful quote from the client in the "Customer/Client Reflection" section
                    - Include exactly ONE impactful quote from the provider in the "Testimonial/Provider Reflection" section
                    - These should be the most powerful, representative quotes
                    - Keep them concise and impactful
                - Write in clear, engaging business English. Use a mix of paragraphs, bold section headers, and bullet points.
                - Include real numbers, testimonials, collaboration stories, and unique project details whenever possible.
                - Start with a punchy title and bold hero statement summarizing the main impact.
                - Make each section distinct and visually scannable (use bold, bullet points, metrics, and quotes).
                - Make the results section full of specifics: show metrics, improvements, and qualitative outcomes.
                - End with a call to action for future collaboration, demo, or contact.
                - DO NOT use asterisks or Markdown stars (**) in your output. Section headers should be in ALL CAPS or plain text only.
                STRUCTURE:
 
                1. LOGO & TITLE BLOCK: Display only the project title with the names of the provider and client.
                2. HERO STATEMENT / BANNER: A one-sentence summary capturing the most impactful achievement.
                3. INTRODUCTION
                4. RESEARCH AND DEVELOPMENT
                5. CLIENT CONTEXT AND CHALLENGES
                6. THE SOLUTION
                7. IMPLEMENTATION & COLLABORATION
                8. RESULTS & IMPACT
                9. CUSTOMER/CLIENT REFLECTION (one client quote only)
                10. TESTIMONIAL/PROVIDER REFLECTION (one provider quote only)
                11. CALL TO ACTION
                12. QUOTES HIGHLIGHTS (2–3 extra short quotes)
 
                CONTENT RULES:
 
                - The provider's version is the base; the client's version enhances, corrects, or adds to it.
                - Use the client's corrected version if numbers or facts differ.
                - In the "Corrected & Conflicted Replies" section (at the end), list bullets of what the client changed, corrected, or added.
                - Accuracy is critical: do not guess or invent any facts. Only use what's in the summaries.
                - Keep each section clear and scannable using ALL CAPS headers (do not bold or use markdown).
                - Main story includes exactly one quote from each side.
                - Final "Quotes Highlights" section includes 2–3 additional impactful quotes NOT used earlier.
                Format each as:
                    - Client: "..."
                    - Provider: "..."

                Use realistic business tone and vocabulary. Do not use markdown (** **, *, -). Just clean, web/PDF-friendly output.
 
                Now, here is the input:
 
                Provider Summary:
                {provider_summary}
 
                Client Summary:
                {client_summary}
                        """
            else:
                # New prompt for when only provider story exists
                full_prompt = f"""
                You are a top-tier business case study writer, creating professional, detailed, and visually attractive stories for web or PDF (inspired by Storydoc, Adobe, and top SaaS companies).
 
                IMPORTANT: Write the entire case study in {detected_language}. This includes all sections, quotes, and any additional content.
 
                Only use the Solution Provider's summary below to write a complete case study. The client did not provide input. Do not label any section with "Provider Summary" or "Title". Do not include markdown (like ** or *). Just write the case study using ALL CAPS section headers and clear business English.
 
                STRUCTURE:
 
                1. LOGO & TITLE BLOCK: Display only the project title with the names of the provider and client.
                2. HERO STATEMENT / BANNER: A one-sentence summary capturing the most impactful achievement.
                3. INTRODUCTION
                4. RESEARCH AND DEVELOPMENT
                5. CLIENT CONTEXT AND CHALLENGES
                6. THE SOLUTION
                7. IMPLEMENTATION & COLLABORATION
                8. RESULTS & IMPACT
                9. CUSTOMER/CLIENT REFLECTION (create a realistic client quote based on the provider's input)
                10. TESTIMONIAL/PROVIDER REFLECTION (one quote from the provider)
                11. CALL TO ACTION
                12. QUOTES HIGHLIGHTS (2–3 extra short provider quotes NOT used earlier)
 
                CONTENT RULES:
 
                - Maintain credibility: do not fabricate specific client claims, only rephrase insights from the provider.
                - Keep each section clear and scannable using ALL CAPS headers (no bolding or markdown).
                - Include one quote in each reflection section.
                - At the end, add a "QUOTES HIGHLIGHTS" section with 2–3 additional provider quotes.
 
                Use a realistic tone and avoid generic phrases. Just output the full case study without section labels, markdown, or references to instructions.
 
                Now, here is the input:
 
                Provider Summary:
                {provider_summary}
                        

                **IMPORTANT QUOTE STRUCTURE:**
                1. **Main Story Quotes** (Only these should appear in the main story):
                    - Include exactly ONE impactful quote from the provider in the "Testimonial/Provider Reflection" section
                    - Create a realistic client quote for the "Customer/Client Reflection" section based on the provider's description
                    - These should be the most powerful, representative quotes
                    - Keep them concise and impactful

                2. **Additional Quotes** (These will appear ONLY in the meta data):
                    - After the main story, provide a section titled "Quotes Highlights"
                    - Include 2-3 additional meaningful quotes that were NOT used in the main story
                    - These should be different from the main quotes above
                    - Format each as:
                      - **Provider:** "Their exact words or close paraphrase"
                    - Focus on quotes that:
                      - Highlight specific results or metrics
                      - Show unique insights about the collaboration
                      - Express satisfaction or key learnings
                      - Reveal interesting challenges overcome

                Example of Additional Quotes (for meta data only):
                - **Provider:** "The client's feedback helped us refine the solution in unexpected ways."
                """

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [
                    {"role": "system", "content": full_prompt},
                ],
                "temperature": 0.5,
                "top_p": 0.9
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            result = response.json()
            case_study_text = result["choices"][0]["message"]["content"]
            cleaned = clean_text(case_study_text)

            main_story, meta_data = self.extract_and_remove_metadata_sections(cleaned, client_summary)
            print("Meta data being saved:", meta_data)
            return main_story, meta_data

        except Exception as e:
            print(f"Error generating full case study: {str(e)}")
            raise e

    def draft_quote_from_summary(self, summary, speaker="Client"):
        """Simple template-based fallback if OpenAI is not available"""
        return self.metadata_service.draft_quote_from_summary(summary, speaker)

    def analyze_client_sentiment(self, client_summary):
        """Analyze sentiment of client summary using the metadata service"""
        return self.metadata_service.analyze_sentiment(client_summary) 