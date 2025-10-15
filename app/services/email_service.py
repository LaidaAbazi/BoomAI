import os
import requests
import json
from datetime import datetime
from flask_mail import Message
from app import mail
from app.services.ai_service import AIService

class EmailService:
    def __init__(self):
        self.ai_service = AIService()
    
    def generate_email_draft(self, case_study, user_name=None, recipient_email=None):
        """
        Generate an email draft for sharing a success story
        
        Args:
            case_study: The success story object
            user_name: Optional user name to include in the email
            recipient_email: Optional recipient email address
            
        Returns:
            dict: Contains email subject, body, and recipient information
        """
        try:
            # Generate email content using AI
            email_content = self._generate_email_content(case_study, user_name)
            
            # Generate email subject
            email_subject = self._generate_email_subject(case_study)
            print(f"🔍 Generated email subject: '{email_subject}'")
            
            # Create email draft structure
            email_draft = {
                "subject": email_subject,
                "body": email_content,
                "recipient": recipient_email or "",
                "pdf_url": f"/api/public/pdf/{case_study.id}",
                "case_study_title": case_study.title,
                "generated_at": datetime.now().isoformat()
            }
            
            print(f"🔍 Email draft subject: '{email_draft['subject']}'")
            
            return email_draft
            
        except Exception as e:
            print(f"❌ Error generating email draft: {str(e)}")
            return None

    def _generate_email_with_gpt4(self, prompt):
        """Generate email content using GPT-4 for better language detection"""
        try:
            headers = {
                "Authorization": f"Bearer {self.ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4",
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"GPT-4 API error in email generation: {response.status_code} - {response.text}")
                # Fallback to regular generate_text method
                return self.ai_service.generate_text(prompt, max_tokens=300)
                
        except Exception as e:
            print(f"Error generating email with GPT-4: {str(e)}")
            # Fallback to regular generate_text method
            return self.ai_service.generate_text(prompt, max_tokens=300)

    def _generate_subject_with_gpt4(self, prompt):
        """Generate email subject using GPT-4 for better language detection"""
        try:
            headers = {
                "Authorization": f"Bearer {self.ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4",
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 50
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"GPT-4 API error in subject generation: {response.status_code} - {response.text}")
                # Fallback to regular generate_text method
                return self.ai_service.generate_text(prompt, max_tokens=50)
                
        except Exception as e:
            print(f"Error generating subject with GPT-4: {str(e)}")
            # Fallback to regular generate_text method
            return self.ai_service.generate_text(prompt, max_tokens=50)
    
    def _generate_email_subject(self, case_study):
        """
        Generate an engaging email subject line using AI
        """
        try:
            if not case_study.final_summary:
                return "Success Story: Case Study Available"
            
            # Clean the summary text
            clean_summary = self._clean_summary_text(case_study.final_summary)
            
            # Extract key metrics for better subject generation
            metrics = self._extract_key_metrics(case_study)
            
            # Build metrics context for the prompt
            metrics_context = ""
            if metrics:
                if 'percentages' in metrics:
                    metrics_context += f"Key Performance: {', '.join(metrics['percentages'])}% improvements\n"
                if 'time_improvements' in metrics:
                    metrics_context += f"Efficiency: {', '.join(metrics['time_improvements'])}x faster\n"
                if 'cost_savings' in metrics:
                    metrics_context += f"Savings: ${', '.join(metrics['cost_savings'])}\n"
            
            prompt = f"""
            You are an expert email marketing specialist creating a compelling subject line for sharing a business success story.
            
            CRITICAL LANGUAGE REQUIREMENT: 
            - Analyze the language of the case study content below
            - If the content is in German, write the subject in German
            - If the content is in Spanish, write the subject in Spanish  
            - If the content is in French, write the subject in French
            - If the content is in English, write the subject in English
            - Match the exact language of the case study content
            
            CONTEXT:
            - This is a professional success story being shared with colleagues, clients, or stakeholders
            - The recipient should be intrigued to open and read the full case study
            - The email includes a PDF attachment with complete details
            
            SUCCESS STORY DETAILS:
            Title: {case_study.title}
            Key Content: {clean_summary[:500]}
            
            KEY METRICS TO HIGHLIGHT:
            {metrics_context if metrics_context else "Focus on qualitative achievements and outcomes mentioned in the content. Do NOT use placeholder numbers like 'XX%' or 'XXx'. Only mention specific, real metrics if they are clearly stated in the content."}
            
            REQUIREMENTS:
            - Maximum 60 characters (including spaces)
            - Professional yet engaging tone in the detected language
            - Highlight the most impressive outcome or benefit
            - Use action-oriented language when possible
            - Avoid generic phrases unless they add value
            - Include specific numbers/percentages ONLY if they are clearly available in the content
            - NEVER use placeholder text like "XX%", "XXx", or "XX" - only use real, specific numbers
            
            LANGUAGE-SPECIFIC EXAMPLES:
            German: "Erfolgsgeschichte: [Company] Transformation", "40% Effizienzsteigerung: [Company] Durchbruch"
            Spanish: "Historia de Éxito: [Company] Transformación", "40% Mejora de Eficiencia: [Company] Logro"
            French: "Histoire de Succès: [Company] Transformation", "40% Amélioration: [Company] Percée"
            English: "Success Story: [Company] Transformation", "40% Efficiency Boost: [Company] Breakthrough"
            
            Generate ONE compelling subject line in the detected language that will make recipients want to open this email. Return only the subject line, no quotes or additional text.
            """
            
            # Use GPT-4 for better language detection and generation
            subject = self._generate_subject_with_gpt4(prompt)
            print(f"🤖 AI generated subject: '{subject}'")
            
            if subject and len(subject.strip()) > 0:
                # Clean the subject by removing quotes if present
                cleaned_subject = subject.strip().strip('"').strip("'")
                print(f"✅ Final AI subject: '{cleaned_subject}'")
                return cleaned_subject
            else:
                fallback_subject = f"Success Story: {case_study.title}"
                print(f"⚠️ Using fallback subject: '{fallback_subject}'")
                return fallback_subject
                
        except Exception as e:
            print(f"Error generating email subject: {str(e)}")
            return f"Success Story: {case_study.title}"
    
    def _generate_email_content(self, case_study, user_name=None):
        """
        Generate the email body content using AI
        """
        try:
            if not case_study.final_summary:
                return self._generate_fallback_email_content(case_study, user_name)
            
            # Clean the summary text
            clean_summary = self._clean_summary_text(case_study.final_summary)
            
            # Extract key metrics for better personalization
            metrics = self._extract_key_metrics(case_study)
            
            # Create a personalized email prompt
            sender_name = user_name or "our team"
            
            # Build metrics context for the prompt
            metrics_context = ""
            has_specific_metrics = False
            if metrics:
                if 'percentages' in metrics:
                    metrics_context += f"Key Performance Improvements: {', '.join(metrics['percentages'])}% improvements\n"
                    has_specific_metrics = True
                if 'time_improvements' in metrics:
                    metrics_context += f"Time Efficiency Gains: {', '.join(metrics['time_improvements'])}x faster\n"
                    has_specific_metrics = True
                if 'cost_savings' in metrics:
                    metrics_context += f"Cost Savings: ${', '.join(metrics['cost_savings'])}\n"
                    has_specific_metrics = True
            
            prompt = f"""
            Write a professional email to share a success story with your team.
            
            CRITICAL LANGUAGE REQUIREMENT: 
            - Analyze the language of the case study content below
            - If the content is in German, write the email in German
            - If the content is in Spanish, write the email in Spanish  
            - If the content is in French, write the email in French
            - If the content is in English, write the email in English
            - Match the exact language of the case study content
            
            SUCCESS STORY:
            {case_study.title}
            {clean_summary[:800]}
            
            KEY ACHIEVEMENTS TO MENTION:
            {metrics_context if has_specific_metrics else "Focus on the most impressive outcomes from the summary above"}
            
            REQUIREMENTS (MANDATORY - output must include all of the following in the detected language):
            
            STRUCTURE (follow this exact format):
            1) GREETING LINE (mandatory first line):
               - German: "Liebe Kollegen," or "Hallo Team,"
               - Spanish: "Estimados colegas," or "Hola equipo,"
               - French: "Chers collègues," or "Bonjour l'équipe,"
               - English: "Dear colleagues," or "Hi team,"
            
            2) EMAIL BODY (2-3 paragraphs about the success story)
            
            3) PDF ATTACHMENT MENTION (mandatory):
               - German: "Ich habe die vollständige Fallstudie als PDF angehängt."
               - Spanish: "He adjuntado el caso de estudio completo en PDF."
               - French: "J'ai joint l'étude de cas complète en PDF."
               - English: "I've attached the complete case study as a PDF."
            
            4) CLOSING (mandatory):
               - German: "Mit freundlichen Grüßen,"
               - Spanish: "Saludos cordiales,"
               - French: "Cordialement,"
               - English: "Best regards,"
            
            5) SENDER NAME (mandatory last line): {user_name or 'Our Team'}
            
            EXAMPLE FORMAT (German):
            Liebe Kollegen,
            
            [Email body content here]
            
            Ich habe die vollständige Fallstudie als PDF angehängt.
            
            Mit freundlichen Grüßen,
            [Sender Name]
            
            CRITICAL: You MUST include all 5 elements above. Do not skip any of them.
            """
            
            # Use GPT-4 for better language detection and generation
            email_body = self._generate_email_with_gpt4(prompt)
            print(f"🤖 Raw AI generated content: {email_body[:300]}...")
            
            if email_body and len(email_body.strip()) > 0:
                # Clean the email body to remove only subject lines (not signatures)
                email_body = self._clean_subject_lines_only(email_body)
                print(f"🧹 After cleaning: {email_body[:300]}...")
                
                # The AI should have already generated the appropriate greeting and PDF mention
                # Just ensure proper sentence ending
                if not email_body.strip().endswith('.'):
                    email_body += "."
                
                print(f"📧 Final email body: {email_body[:200]}...")
                return email_body.strip()
            else:
                return self._generate_fallback_email_content(case_study, user_name)
                
        except Exception as e:
            print(f"Error generating email content: {str(e)}")
            return self._generate_fallback_email_content(case_study, user_name)
    
    def _generate_fallback_email_content(self, case_study, user_name=None):
        """
        Generate a fallback email content if AI generation fails
        """
        sender_name = user_name or "our team"
        
        return f"""Dear Team,

I'm excited to share a success story with you! {sender_name} recently completed a success story that demonstrates some impressive results.

{case_study.title}

This success story showcases how we helped our client achieve significant improvements in their business processes and outcomes. The project involved collaboration between our team and the client to implement innovative solutions that delivered measurable results.

I've attached the complete success story as a PDF for your review.

Best regards,
{sender_name}"""
    
    def _clean_summary_text(self, summary):
        """
        Clean the summary text by removing formatting markers
        """
        if not summary:
            return ""
        
        # Remove common formatting markers
        markers_to_remove = [
            "HERO STATEMENT:", "BANNER:", "CHALLENGE:", "SOLUTION:", 
            "RESULTS:", "CONCLUSION:", "BACKGROUND:", "APPROACH:"
        ]
        
        cleaned = summary
        for marker in markers_to_remove:
            cleaned = cleaned.replace(marker, "")
        
        # Remove extra whitespace and normalize
        cleaned = " ".join(cleaned.split())
        
        return cleaned
    
    def _extract_key_metrics(self, case_study):
        """
        Extract key metrics and outcomes from the case study for better email content
        """
        if not case_study.final_summary:
            return {}
        
        summary = case_study.final_summary.lower()
        metrics = {}
        
        # Look for percentage improvements
        import re
        percentage_patterns = [
            r'(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*percent',
            r'increase.*?(\d+(?:\.\d+)?)\s*%',
            r'reduce.*?(\d+(?:\.\d+)?)\s*%',
            r'improve.*?(\d+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in percentage_patterns:
            matches = re.findall(pattern, summary)
            if matches:
                metrics['percentages'] = matches[:3]  # Take first 3 percentages
        
        # Look for time improvements
        time_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:faster|quicker)',
            r'(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:improvement)',
            r'reduce.*?(\d+(?:\.\d+)?)\s*(?:hours?|days?|weeks?|months?)'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, summary)
            if matches:
                metrics['time_improvements'] = matches[:2]
        
        # Look for cost savings
        cost_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:k|thousand|million|billion)?',
            r'save.*?\$(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'reduce.*?cost.*?\$(\d+(?:,\d{3})*(?:\.\d+)?)'
        ]
        
        for pattern in cost_patterns:
            matches = re.findall(pattern, summary)
            if matches:
                metrics['cost_savings'] = matches[:2]
        
        return metrics
    
    def get_mailto_url(self, email_draft):
        """
        Generate a mailto URL for the email draft
        
        Args:
            email_draft: The email draft dictionary
            
        Returns:
            str: mailto URL that can be used to open the user's email client
        """
        try:
            subject = email_draft.get("subject", "")
            body = email_draft.get("body", "")
            recipient = email_draft.get("recipient", "")
            
            # Encode the subject and body for URL
            import urllib.parse
            encoded_subject = urllib.parse.quote(subject)
            encoded_body = urllib.parse.quote(body)
            
            # Build mailto URL
            mailto_url = f"mailto:{recipient}?subject={encoded_subject}&body={encoded_body}"
            
            return mailto_url
            
        except Exception as e:
            print(f"Error generating mailto URL: {str(e)}")
            return ""
    
    def send_email_automatically(self, email_draft, sender_email, sender_name=None, case_study=None):
        """
        Send email automatically using the app's email configuration
        
        Args:
            email_draft: The email draft dictionary
            sender_email: The email address of the sender (logged-in user)
            sender_name: Optional name of the sender
            case_study: Optional case study object for PDF attachment
            
        Returns:
            dict: Contains success status and message
        """
        try:
            if not email_draft.get("recipient"):
                return {
                    "success": False,
                    "message": "No recipient email address provided"
                }
            
            subject = email_draft.get("subject", "")
            body = email_draft.get("body", "")
            recipient = email_draft.get("recipient", "")
            
            # Check if this is edited content from frontend or generated content
            if email_draft.get('use_edited_content'):
                # Use edited content exactly as-is (no cleaning)
                print(f"📧 Using EDITED content as-is: {body[:200]}...")
            else:
                # Clean generated content to remove subject lines
                body = self._clean_subject_lines_only(body)
                print(f"📧 Cleaned generated content: {body[:200]}...")
            
            # Create email message
            msg = Message(
                subject=subject,
                recipients=[recipient],
                sender=(sender_name or sender_email, sender_email)
            )
            
            # Generate and attach PDF if case study is provided
            pdf_attached = False
            if case_study:
                try:
                    # Check if PDF data already exists
                    if case_study.final_summary_pdf_data:
                        pdf_data = case_study.final_summary_pdf_data
                        print(f"✅ Using existing PDF data for case study {case_study.id}")
                    else:
                        # Generate PDF if it doesn't exist using the robust method
                        print(f"📄 Generating PDF for case study {case_study.id}")
                        try:
                            from fpdf import FPDF
                            from io import BytesIO
                            
                            if not case_study.final_summary:
                                print(f"⚠️ No final summary available for case study {case_study.id}")
                                pdf_data = None
                            else:
                                pdf = FPDF()
                                pdf.add_page()
                                pdf.set_margins(20, 20, 20)  # Left, Top, Right margins
                                pdf.set_auto_page_break(auto=True, margin=20)
                                
                                try:
                                    pdf.set_font("Arial", 'B', 16)
                                    pdf.set_text_color(0, 0, 0)
                                    title = case_study.title or "Case Study"
                                    clean_title = title.encode('latin-1', 'replace').decode('latin-1')
                                    pdf.multi_cell(0, 10, title, align='C')
                                    pdf.ln(10)

                                    # Add final summary content with section headings
                                    pdf.set_text_color(0, 0, 0)
                                    summary_lines = case_study.final_summary.split('\n')
                                    for line in summary_lines:
                                        clean_line = line.encode('latin-1', 'replace').decode('latin-1').strip()

                                        # If line is a heading (uppercase & not too long) → bold
                                        if clean_line.isupper() and len(clean_line) < 60:
                                            pdf.set_font("Arial", 'B', 13)
                                            pdf.cell(0, 8, clean_line, ln=True)
                                            pdf.ln(2)
                                        # Otherwise → normal paragraph text
                                        elif clean_line:
                                            pdf.set_font("Arial", '', 11)
                                            pdf.multi_cell(0, 6, clean_line)
                                            pdf.ln(2)
                                        else:
                                            pdf.ln(3)  # Extra space for empty lines
                                except Exception as pdf_error:
                                    print(f"❌ PDF generation error: {str(pdf_error)}")
                                    pdf = FPDF()
                                    pdf.add_page()
                                    pdf.set_font("Arial", size=12)
                                    pdf.multi_cell(0, 10, "Case Study PDF")
                                    pdf.ln(10)
                                    summary_text = case_study.final_summary[:1000] + "..." if len(
                                        case_study.final_summary) > 1000 else case_study.final_summary
                                    pdf.multi_cell(0, 10, summary_text)

                                # Save PDF to database
                                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                                case_study.final_summary_pdf_data = pdf_bytes
                                from app import db
                                db.session.commit()
                                
                                pdf_data = pdf_bytes
                                print(f"✅ PDF generated successfully for case study {case_study.id}")
                                
                        except Exception as e:
                            print(f"❌ Error generating PDF: {str(e)}")
                            pdf_data = None
                    
                    # Attach PDF if we have data
                    if pdf_data:
                        from io import BytesIO
                        pdf_filename = f"case_study_{case_study.id}_{case_study.title or 'Success_Story'}.pdf"
                        # Clean filename for filesystem compatibility
                        import re
                        pdf_filename = re.sub(r'[^\w\-_\.]', '_', pdf_filename)
                        
                        print(f"📎 Attaching PDF: {pdf_filename} (Size: {len(pdf_data)} bytes)")
                        msg.attach(
                            filename=pdf_filename,
                            content_type="application/pdf",
                            data=pdf_data
                        )
                        pdf_attached = True
                        print(f"✅ PDF attached: {pdf_filename}")
                    else:
                        print(f"⚠️ No PDF data available for case study {case_study.id}")
                        print(f"🔍 Debug: case_study.final_summary_pdf_data is {type(case_study.final_summary_pdf_data)}")
                        if case_study.final_summary_pdf_data:
                            print(f"🔍 Debug: PDF data length: {len(case_study.final_summary_pdf_data)}")
                        else:
                            print(f"🔍 Debug: PDF data is None or empty")
                        
                except Exception as pdf_error:
                    print(f"⚠️ Could not attach PDF: {str(pdf_error)}")
            
            # If content comes from frontend, it already includes PDF attachment and signature
            # If content is newly generated, PDF attachment and signature are added in generate_email_content
            
            # Set email body
            msg.body = body
            
            # Send the email
            mail.send(msg)
            
            print(f"✅ Email sent successfully from {sender_email} to {recipient}")
            
            return {
                "success": True,
                "message": f"Email sent successfully to {recipient}",
                "sender": sender_email,
                "recipient": recipient,
                "subject": subject
            }
            
        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            }
    
    def _clean_subject_lines_only(self, body):
        """
        Clean the email body to remove only subject lines and closing phrases, not our added signatures
        """
        if not body:
            return ""
        
        # Remove lines that start with "Subject:"
        lines = body.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip lines that start with "Subject:" (case insensitive)
            if line.lower().startswith('subject:'):
                continue
            
            # DO NOT remove closing phrases, PDF mentions, or signatures - these are required elements
            # Only remove subject lines and duplicate content
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _clean_email_body(self, body):
        """
        Clean the email body to remove any unwanted content like "Subject:" lines and duplicate signatures
        """
        if not body:
            return ""
        
        # Remove lines that start with "Subject:"
        lines = body.split('\n')
        cleaned_lines = []
        found_signature = False
        
        for line in lines:
            line = line.strip()
            
            # Skip lines that start with "Subject:" (case insensitive)
            if line.lower().startswith('subject:'):
                continue
            
            # Remove duplicate signatures and closings
            if line.lower() in ['best regards,', 'warm regards,', 'sincerely,', 'regards,']:
                if found_signature:
                    continue  # Skip duplicate signature lines
                found_signature = True
            
            # Skip lines that are just the user's name (likely duplicate signature)
            if found_signature and (line == '' or line.isdigit() or len(line.split()) <= 3):
                continue
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines) 