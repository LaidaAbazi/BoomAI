import os
import requests
import json
import re
from datetime import datetime
from app.utils.text_processing import extract_names_from_case_study_fallback, clean_text

class AIService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_config = {
            "model": "gpt-4",
            "temperature": 0.5,
            "top_p": 0.9,
            "presence_penalty": 0.2,
            "frequency_penalty": 0.2
        }
    
    def extract_names_from_case_study_llm(self, text):
        """Extract solution provider name, client name, and project name using OpenAI LLM for maximum accuracy."""
        try:
            if not self.openai_api_key:
                return self.extract_names_from_case_study_fallback(text)
            
            # Take only the first part of the text to save tokens and focus on the most relevant content
            lines = text.split('\n')
            # Get the first 20 lines or first 2000 characters, whichever comes first
            intro_text = '\n'.join(lines[:20])
            if len(intro_text) > 2000:
                intro_text = intro_text[:2000]
            
            prompt = f"""You are a business case study analysis expert. Extract the three key entities from this case study text:

1. **Solution Provider Name** - The company or organization that provided the solution/service
2. **Client Name** - The company or organization that received the solution/service  
3. **Project Name** - The name of the project, product, service, or transformation (NOT a long descriptive title)

Look for these patterns in the text:
- Company names mentioned in the introduction or background
- Project names, product names, or service names (keep these short and specific)
- Client references like "client", "customer", "partner"
- Provider references like "we", "our team", "our company"
- Business context and industry mentions

IMPORTANT: For the project title, look for specific project names like "ChatBot AI", "Digital Transformation", "Customer Portal", "AI Solution", etc. Do NOT use long descriptive phrases, headlines, or sentences. The project title should be 2-4 words maximum.

Case Study Text:
{intro_text}

Return ONLY a JSON object with these exact keys:
{{
  "lead_entity": "Solution Provider Name",
  "partner_entity": "Client Name", 
  "project_title": "Project Name"
}}

If any entity cannot be found, use "Unknown" for that field. Ensure the JSON is valid and properly formatted."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.1,  # Lower temperature for more consistent extraction
                "max_tokens": 200
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in name extraction: {response.status_code} - {response.text}")
                return self.extract_names_from_case_study_fallback(text)
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in name extraction: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return self.extract_names_from_case_study_fallback(text)
            
            if "choices" in result and len(result["choices"]) > 0:
                extracted_text = result["choices"][0]["message"]["content"].strip()
                
                # Try to parse JSON response
                try:
                    # Clean up the response - remove any markdown formatting
                    extracted_text = extracted_text.replace('```json', '').replace('```', '').strip()
                    names = json.loads(extracted_text)
                    
                    # Validate and clean the extracted names
                    lead_entity = names.get("lead_entity", "Unknown").strip()
                    partner_entity = names.get("partner_entity", "").strip()
                    project_title = names.get("project_title", "Unknown Project").strip()
                    
                    # Handle empty or invalid values
                    if not lead_entity or lead_entity.lower() in ["unknown", "none", "empty"]:
                        lead_entity = "Unknown"
                    if not partner_entity or partner_entity.lower() in ["unknown", "none", "empty"]:
                        partner_entity = ""
                    if not project_title or project_title.lower() in ["unknown", "none", "empty"]:
                        project_title = "Unknown Project"
                    
                    return {
                        "lead_entity": lead_entity,
                        "partner_entity": partner_entity,
                        "project_title": project_title
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"Failed to parse extracted names JSON: {e}")
                    print(f"Extracted text: {extracted_text}")
                    # Fallback to old method
                    return self.extract_names_from_case_study_fallback(text)
            else:
                print(f"Unexpected API response structure in name extraction: {result}")
                # Fallback to old method
                return self.extract_names_from_case_study_fallback(text)
                
        except requests.RequestException as e:
            print(f"Request error in name extraction: {str(e)}")
            return self.extract_names_from_case_study_fallback(text)
        except Exception as e:
            print(f"Error extracting names with LLM: {str(e)}")
            # Fallback to old method
            return self.extract_names_from_case_study_fallback(text)
    
    def extract_names_from_case_study(self, text):
        """Extract names using LLM with fallback to regex method."""
        return self.extract_names_from_case_study_llm(text)
    
    def extract_names_from_case_study_fallback(self, text):
        """Fallback method using simple text analysis."""
        # normalize dashes
        text = text.replace("—", "-").replace("–", "-")
        lines = text.splitlines()
        
        # Look for company names and project references in the first few lines
        intro_text = '\n'.join(lines[:10])
        
        # Simple pattern matching for common business terms
        provider_keywords = ["we", "our team", "our company", "our organization"]
        client_keywords = ["client", "customer", "partner", "they", "their"]
        
        # For now, return default values since this is a fallback
        # The LLM method should handle most cases
        return {
            "lead_entity": "Unknown",
            "partner_entity": "",
            "project_title": "Unknown Project"
        }
    
    def generate_summary(self, transcript, language="en"):
        """Generate summary from transcript using OpenAI"""
        try:
            if not self.openai_api_key:
                return "AI service not available. Please provide a manual summary."
            
            prompt = f"""Generate a comprehensive summary of this interview transcript. Focus on:
- Key business challenges and solutions
- Results and outcomes
- Client satisfaction and feedback
- Technical implementation details

Transcript:
{transcript}

Provide a well-structured summary suitable for a business case study."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in summary generation: {response.status_code} - {response.text}")
                return f"Failed to generate summary. API error: {response.status_code}"
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in summary generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return "Failed to generate summary. Invalid response format."
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Unexpected API response structure in summary generation: {result}")
                return "Failed to generate summary."
                
        except requests.RequestException as e:
            print(f"Request error in summary generation: {str(e)}")
            return "Failed to generate summary. Network error."
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return "Error generating summary. Please try again."
    
    def generate_client_summary(self, transcript, provider_summary):
        """Generate client summary from transcript"""
        try:
            if not self.openai_api_key:
                return "AI service not available. Please provide a manual summary."
            
            prompt = f"""Generate a client perspective summary from this interview transcript. Focus on:
- Client's business challenges and pain points
- Their experience with the solution
- Results and benefits they achieved
- Their satisfaction and feedback
- Key quotes and testimonials

Provider Summary for Context:
{provider_summary}

Client Interview Transcript:
{transcript}

Provide a client-focused summary that complements the provider perspective."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 800
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in client summary generation: {response.status_code} - {response.text}")
                return f"Failed to generate client summary. API error: {response.status_code}"
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in client summary generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return "Failed to generate client summary. Invalid response format."
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Unexpected API response structure in client summary generation: {result}")
                return "Failed to generate client summary."
                
        except requests.RequestException as e:
            print(f"Request error in client summary generation: {str(e)}")
            return "Failed to generate client summary. Network error."
        except Exception as e:
            print(f"Error generating client summary: {str(e)}")
            return "Error generating client summary. Please try again."
    
    def generate_full_case_study(self, case_study):
        """Generate complete case study from provider and client summaries"""
        try:
            if not self.openai_api_key:
                return case_study.final_summary or "AI service not available."
            
            # Safely access the summaries with proper null checks
            provider_summary = ""
            if case_study.solution_provider_interview and case_study.solution_provider_interview.summary:
                provider_summary = case_study.solution_provider_interview.summary
            
            client_summary = ""
            if case_study.client_interview and case_study.client_interview.summary:
                client_summary = case_study.client_interview.summary
            
            prompt = f"""Create a comprehensive business case study that combines the solution provider and client perspectives. Structure it as follows:

1. Executive Summary
2. Background & Challenge
3. Solution & Implementation
4. Results & Outcomes
5. Client Testimonials & Feedback
6. Conclusion

Provider Summary:
{provider_summary}

Client Summary:
{client_summary}

Create a professional, well-structured case study that tells a compelling story of business transformation."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in full case study generation: {response.status_code} - {response.text}")
                return case_study.final_summary or f"Failed to generate case study. API error: {response.status_code}"
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in full case study generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return case_study.final_summary or "Failed to generate case study. Invalid response format."
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Unexpected API response structure in full case study generation: {result}")
                return case_study.final_summary or "Failed to generate case study."
                
        except requests.RequestException as e:
            print(f"Request error in full case study generation: {str(e)}")
            return case_study.final_summary or "Failed to generate case study. Network error."
        except Exception as e:
            print(f"Error generating full case study: {str(e)}")
            return case_study.final_summary or "Error generating case study. Please try again."
    
    def generate_linkedin_post(self, case_study_text):
        """Generate a LinkedIn post from a case study using AI."""
        try:
            if not self.openai_api_key:
                return "AI service not available for LinkedIn post generation."
            
            prompt = f"""
        You are an expert LinkedIn ghostwriter for a company.  
Your job is to write **ONE well-structured LinkedIn post** that matches the exact style and tone of the sample below.

---

**🎯 Purpose:**  
The post should feel like a personal reflection from someone in the company (e.g., founder, project lead, or senior consultant) sharing a true client success story PLUS practical insights that others can learn from — written in a warm, conversational, and very clear style.

---

**✅ Write it like this:**

- Your FIRST LINE must be **one short sentence only** — maximum **10 words**.  
- It must be directly inspired by the biggest *pain point, surprising stat, or unexpected win* in the case study text.  
- It must read like a natural curiosity trigger, not a generic corporate result or claim.
• Follow immediately with 1–2 short lines that naturally set up the story or the key theme.  
• Tell a short, clear story describing:  
  — How the company worked with a client  
  — What they learned during the project  
  — How they turned those lessons into a clear, helpful framework or simple steps others can use.  
• Break down the framework or lessons just like the example: use short lines, clear steps, maybe simple arrows or numbering.  
• Optionally illustrate the *wrong way vs right way* using short lines.  
• Wrap up with 1–2 lines encouraging readers to apply the idea right away.  
• End with 3–5 relevant hashtags (all lowercase, no spaces).  
• Finally, add one line: *Visual idea:* describe a simple graphic that matches the framework.

---

**✅ Style & tone:**  
• Fully from the company's voice — "we", "our team", "our project".  
• Warm, confident, human.  
• No stiff jargon or robotic phrasing.  
• Short paragraphs, short sentences, clear line breaks — easy to read on mobile.  
• Plain language — max Grade 6–7 reading level.  
• Total length: around **1200–1800 characters**, including hashtags.

---

**❌ Do NOT:**  
• Do not use visible section labels like "HOOK".  
• Do not make it sound generic or repetitive.  
• Do not list dry bullet points — use arrows or short lines like the example.  
• Do not add any links in the post.

---

**✅ CASE STUDY:**  

{case_study_text}

LinkedIn Post:
"""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4",
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return f"Failed to generate LinkedIn post. API error: {response.status_code}"
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return "Failed to generate LinkedIn post. Invalid response format."
            
            # Check if the response has the expected structure
            if "choices" not in result or len(result["choices"]) == 0:
                print(f"Unexpected API response structure: {result}")
                return "Failed to generate LinkedIn post. Unexpected response structure."
            
            return result["choices"][0]["message"]["content"].strip()
            
        except requests.RequestException as e:
            print(f"Request error in LinkedIn post generation: {str(e)}")
            return "Failed to generate LinkedIn post. Network error."
        except Exception as e:
            print(f"Error generating LinkedIn post: {str(e)}")
            return "Error generating LinkedIn post. Please try again."
    
    def generate_podcast_script(self, case_study_text):
        """Generate podcast script from case study"""
        try:
            if not self.openai_api_key:
                return "AI service not available for podcast script generation."
            
            prompt = f"""Create a podcast episode (max 5 minutes) that explains the work done, the business case, and the results achieved. Make the conversation dynamic and expressive, using vocal emphasis, excitement, and friendly interaction. Imagine you're speaking to a live audience that you want to inspire and excite!. The script should:
- Be conversational and engaging
- Include host and guest dialogue
- Highlight key insights and lessons learned
- Be suitable for a business/technology podcast
- Be stricly 5 minutes when read aloud

Case Study:
{case_study_text}  

Create a podcast script that tells the story in an engaging way."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.6,
                "max_tokens": 1000
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in podcast script generation: {response.status_code} - {response.text}")
                return f"Failed to generate podcast script. API error: {response.status_code}"
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in podcast script generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return "Failed to generate podcast script. Invalid response format."
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Unexpected API response structure in podcast script generation: {result}")
                return "Failed to generate podcast script."
                
        except requests.RequestException as e:
            print(f"Request error in podcast script generation: {str(e)}")
            return "Failed to generate podcast script. Network error."
        except Exception as e:
            print(f"Error generating podcast script: {str(e)}")
            return "Error generating podcast script. Please try again."
    
    def generate_heygen_input_text(self, final_summary):
        """Generate optimized input text for HeyGen video using OpenAI."""
        try:
            prompt = f"""You are a professional business scriptwriter creating a short video script for a HeyGen AI avatar. Your task is to turn the success story summary below into a concise, professional, and clearly structured spoken script — as if it's being presented by a company representative in a formal setting (e.g. on LinkedIn, in a client meeting, or at a company showcase).

Tone:
- Professional, confident, and factual.
- No exaggeration, slang, hype, or casual phrases (e.g., avoid words like "smashing," "amazing," "incredible," "AI-powered" unless explicitly mentioned).
- Write in first-person plural ("we," "our team," "our client") as if the company is speaking.

Content Rules:
- Only use information found in the success story summary. Do not assume or invent anything.
- Do not add filler like "since no metrics are given" — if something is missing, skip that point entirely. Every sentence must reflect real, supported content.
- Include the company name, client name, and project name where appropriate.
- Focus on the client's challenge, what was delivered, how it was implemented (if described), and the final outcome.
- If specific results or metrics are provided, include them clearly. If not, omit that section without comment.

Style:
- Use short, natural-sounding sentences — easy to follow when spoken by an AI avatar.
- The tone should sound like a real business person, not like a marketer or assistant.

Structure:
1. Brief introduction or hook (1–2 sentences)
2. Client background or challenge
3. What we delivered
4. How it was implemented (if relevant)
5. The outcome or impact
6. Closing reflection or key takeaway

Length:
- Keep the full script under 1300 characters.
- Do not include any titles, labels, line breaks, or extra notes — return only the final clean block of spoken text.

Success Story Summary:
{final_summary}

Return only the final video script. Nothing else."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [
                    {"role": "system", "content": "You are a professional video script writer who specializes in creating engaging, conversational scripts for AI avatar presentations. Your scripts are known for being clear, impactful, and perfectly timed for avatar delivery."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in HeyGen input text generation: {response.status_code} - {response.text}")
                return None
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in HeyGen input text generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return None
            
            if "choices" in result and len(result["choices"]) > 0:
                script = result["choices"][0]["message"]["content"].strip()
                
                # Ensure the script doesn't exceed 1300 characters
                if len(script) > 1300:
                    script = script[:1297] + "..."
                    
                return script
            else:
                print(f"Unexpected API response structure in HeyGen input text generation: {result}")
                return None
                
        except requests.RequestException as e:
            print(f"Request error in HeyGen input text generation: {str(e)}")
            return None
        except Exception as e:
            print(f"Error generating HeyGen input text: {str(e)}")
            return None

    def generate_pictory_scenes_text(self, final_summary):
        """Generate scene-based text for Pictory video using OpenAI."""
        try:
            prompt = f"""You are a video scriptwriter for StoryBoom AI. Your task is to turn the case study below into a compelling 8-scene short-form video script. Each sentence should reflect a real moment or idea from the story, written clearly enough to be visualized as a separate scene.

Your goal is to help companies showcase their project or client success story in a way that feels real, story-driven, and accurate.

Guidelines:
- Use present tense and active voice.
- Each sentence should be short (10–25 words), simple, and clear.
- Each one should reflect one key idea that can be visualized in a clip (e.g., a challenge, a solution, a result).
- Avoid vague or generic phrases like "the results were amazing." Be concrete and real.
- Use a natural, spoken tone, like someone confidently narrating their team's journey.
- Always include the company name, client name, and project name where relevant.
- Stay true to the facts and phrasing in the story. Do not exaggerate or fabricate.

Structure the 8 scenes like this:
1. A strong, curiosity-driven hook
2. The challenge or situation
3. Who we are (the solution provider)
4. What we did
5. How we delivered it
6. The main outcome
7. A highlight or metric
8. The impact on the client (or their feedback)

Output format:
Return exactly 8 sentences, separated by a period and a space. No line breaks. No bullet points. No extra text or titles.

Here is the case study:
{final_summary}

Return only the final 8-scene script, nothing else."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.openai_config["model"],
                "messages": [
                    {"role": "system", "content": "You are a professional short-form video scriptwriter who creates engaging, visual scenes for social media videos."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 800
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in Pictory scenes text generation: {response.status_code} - {response.text}")
                return None
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in Pictory scenes text generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return None
            
            if "choices" in result and len(result["choices"]) > 0:
                scenes_text = result["choices"][0]["message"]["content"].strip()
                
                # Split into individual scenes
                scenes = [scene.strip() for scene in scenes_text.split('\n') if scene.strip()]
                
                # Clean up numbering if present
                cleaned_scenes = []
                for scene in scenes:
                    # Remove numbering like "1.", "2.", etc.
                    cleaned_scene = re.sub(r'^\d+\.\s*', '', scene)
                    cleaned_scenes.append(cleaned_scene)
                
                return cleaned_scenes[:6]  # Ensure max 6 scenes
            else:
                print(f"Unexpected API response structure in Pictory scenes text generation: {result}")
                return None
                
        except requests.RequestException as e:
            print(f"Request error in Pictory scenes text generation: {str(e)}")
            return None
        except Exception as e:
            print(f"Error generating Pictory scenes text: {str(e)}")
            return None

    def generate_podcast_prompt(self, final_summary):
        """Use OpenAI to summarize the case study into a short, clean version for Wondercraft."""
        try:
            # Use OpenAI to create a concise summary of the case study
            openai_prompt = f"""Summarize this business case study in exactly 150 words or less. Make it clear, engaging, and include:
- Client name and challenge
- Solution provided  
- Key results/impact
- Main lessons learned

Write it in a natural, conversational style that would work well for a podcast. Remove any formatting, headers, or technical jargon.

Case study:
{final_summary}

Return ONLY the 150-word summary, nothing else."""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4",
                "messages": [{"role": "system", "content": openai_prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Check if the response is successful
            if response.status_code != 200:
                print(f"OpenAI API error in podcast prompt generation: {response.status_code} - {response.text}")
                return None
            
            # Try to parse the JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response in podcast prompt generation: {e}")
                print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
                return None
            
            if "choices" in result and len(result["choices"]) > 0:
                summary = result["choices"][0]["message"]["content"].strip()
                
                if summary:
                    # Create the full prompt with instructions for Wondercraft
                    full_prompt = f"""Make the conversation energetic, positive, and excited throughout - not over the top, just genuinely enthusiastic.

Create an exactly 5-minute business podcast between two persons about this success story. Make it conversational and engaging.

Business case study:
{summary}"""
                    
                    return full_prompt
                else:
                    return None
            else:
                print(f"Unexpected API response structure in podcast prompt generation: {result}")
                return None
                
        except requests.RequestException as e:
            print(f"Request error in podcast prompt generation: {str(e)}")
            return None
        except Exception as e:
            print(f"Error generating summary with OpenAI: {str(e)}")
            return None 