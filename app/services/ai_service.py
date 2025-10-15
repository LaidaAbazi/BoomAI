import os
import requests
import json
from typing import Dict, Any, Optional

class AIService:
    """AI service for OpenAI integration"""
    
    def __init__(self):
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.openai_config = {
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000,
            "temperature": 0.7
        }
    
    def generate_text(self, prompt: str, max_tokens: int = None) -> str:
        """Generate text using OpenAI API"""
        if not self.openai_api_key:
            return "AI service not available - API key not configured"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.openai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens or self.openai_config["max_tokens"],
                "temperature": self.openai_config["temperature"]
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                return f"Error generating text: {response.status_code}"
                
        except Exception as e:
            return f"Error generating text: {str(e)}"
    
    def extract_names_from_case_study(self, text: str) -> Dict[str, str]:
        """Extract company names and project title from case study text"""
        if not self.openai_api_key:
            return {
                "lead_entity": "Company Name",
                "partner_entity": "Client Name", 
                "project_title": "Project Title"
            }
        
        prompt = f"""
        Extract the following information from this case study text:
        1. Lead entity (solution provider company name)
        2. Partner entity (client company name)
        3. Project title (name of the project/case study)
        
        Return the result in JSON format with keys: lead_entity, partner_entity, project_title
        
        Text: {text[:2000]}
        """
        
        try:
            result = self.generate_text(prompt, max_tokens=200)
            
            # Try to parse JSON response
            try:
                names = json.loads(result)
                return {
                    "lead_entity": names.get("lead_entity", "Company Name"),
                    "partner_entity": names.get("partner_entity", "Client Name"),
                    "project_title": names.get("project_title", "Project Title")
                }
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                lines = result.split('\n')
                names = {
                    "lead_entity": "Company Name",
                    "partner_entity": "Client Name", 
                    "project_title": "Project Title"
                }
                
                for line in lines:
                    if "lead_entity" in line.lower() or "company" in line.lower():
                        names["lead_entity"] = line.split(':')[-1].strip().strip('"')
                    elif "partner_entity" in line.lower() or "client" in line.lower():
                        names["partner_entity"] = line.split(':')[-1].strip().strip('"')
                    elif "project_title" in line.lower() or "project" in line.lower():
                        names["project_title"] = line.split(':')[-1].strip().strip('"')
                
                return names
                
        except Exception as e:
            return {
                "lead_entity": "Company Name",
                "partner_entity": "Client Name",
                "project_title": "Project Title"
            }
    
    def extract_names_from_case_study_llm(self, text: str) -> Dict[str, str]:
        """LLM-based name extraction (alias for extract_names_from_case_study)"""
        return self.extract_names_from_case_study(text)
    
    def generate_linkedin_post(self, case_study_text):
        """Generate a LinkedIn post from a case study using AI."""
        try:
            if not self.openai_api_key:
                return "AI service not available for LinkedIn post generation."
            
            prompt = f"""
        You are an expert LinkedIn ghostwriter for a company.  
Your job is to write **ONE well-structured LinkedIn post** that matches the exact style and tone of the sample below.

**IMPORTANT: Write the LinkedIn post in the same language as the case study content below.**

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
    
    def generate_client_summary(self, transcript: str, case_study_summary: str) -> str:
        """Generate client interview summary"""
        if not self.openai_api_key:
            return "AI service not available - API key not configured"
        
        prompt = f"""
        Based on this client interview transcript and the existing case study summary,
        create a comprehensive client perspective summary that complements the case study.
        
        Transcript: {transcript[:2000]}
        Case study summary: {case_study_summary[:1000]}
        
        Focus on the client's perspective, challenges faced, and outcomes achieved.
        """
        
        try:
            return self.generate_text(prompt, max_tokens=500)
        except Exception as e:
            return f"Error generating client summary: {str(e)}"
    
    def generate_heygen_input_text(self, case_study_summary: str) -> str:
        """Generate input text for HeyGen video generation"""
        if not self.openai_api_key:
            return "AI service not available - API key not configured"
        
        prompt = f"""
        Create a script for a professional video presentation based on this case study.
        The script should be engaging, clear, and suitable for a business video.
        Keep it concise but comprehensive.
        
        Case study: {case_study_summary[:1500]}
        """
        
        try:
            return self.generate_text(prompt, max_tokens=300)
        except Exception as e:
            return f"Error generating HeyGen input: {str(e)}"
    
    def generate_pictory_scenes_text(self, case_study_summary: str) -> str:
        """Generate scenes text for Pictory video generation"""
        if not self.openai_api_key:
            return "AI service not available - API key not configured"
        
        prompt = f"""
        Create a detailed scene-by-scene breakdown for a video based on this case study.
        Each scene should have a clear description and be suitable for visual storytelling.
        
        Case study: {case_study_summary[:1500]}
        """
        
        try:
            return self.generate_text(prompt, max_tokens=400)
        except Exception as e:
            return f"Error generating Pictory scenes: {str(e)}"
    
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

Create an exactly 5-minute business podcast between only two persons about this success story no other voices. Make it conversational and engaging.

CRITICAL NAMING: Use two speakers with these exact names and genders: Jimmy (male) and Emma (female). Prefix every line of dialogue with the speaker's name followed by a colon, like "Jimmy:" or "Emma:". Start the conversation with Jimmy speaking first, then alternate naturally. Do NOT use labels like "Speaker 1" or "Speaker 2" anywhere.

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
