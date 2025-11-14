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

           ### ABSOLUTE, NON-NEGOTIABLE RULES (THE MODEL MUST FOLLOW THESE EXACTLY)

1. DO NOT output any section labels.  
   Forbidden labels include: "HOOK", "STORY", "TAKEAWAY", "CLOSING", "HASHTAGS", or any variation (lowercase, uppercase, bold, with or without colons).  
   If the model outputs ANY label, the output is invalid.

2. FIRST LINE = Hook.  
   - Max 10 words.  
   - NO emojis, NO hashtags, NO links.  
   - One sentence only.

3. STORY = 4 to 6 paragraphs.  
   - Each paragraph 1 to 3 sentences maximum.  
   - Each sentence MUST appear on its own line.  
   - No paragraph may exceed 2 lines total on screen.  
   - No labels, no bullets, no numbering.  
   - No emojis in more than 3 total sentences in the entire post.

4. LANGUAGE RULE: Use the same language as the case study.

5. LENGTH RULE: Total post length MUST be between 80 and 120 words (inclusive).  
   The model must self-check and keep within this range.
   

6. FORBIDDEN WORDS & PHRASES:  
   - NEVER use “the results”, “the result?”, or “the impact”.  
   - NEVER use “the solution?” as a phrase.  
   - NEVER use “Enter [company]”.  
   - Avoid robotic phrasing like: “This wasn’t a simple task.” “They succeeded.” “A single solution…”.

7. TAKEAWAY = 1 to 2 lines only.  
   Short, poetic, memorable. No labels.

8. CLOSING = EXACTLY one question.  
   One line only. No emojis.

9. HASHTAGS = 3 to 5 hashtags on the last line.  
   Only plain hashtags. No emojis. No section labels.

10. NO markdown formatting:  
    - No bold  
    - No italics  
    - No headers (#, ##, ###)  
    - No lists  
    - No colons after labels (since labels are forbidden entirely)

11. EMOJI RULE: The post MUST use **between 1 and 3 emojis total** (inclusive).
- Emojis CANNOT appear in the hook.
- Emojis may appear only inside the story paragraphs or takeaway.


If the model violates ANY rule above, regenerate until compliant.


        Act as a **LinkedIn content strategist and viral copywriter** with a proven record of creating high-engagement posts that drive massive reach, discussion, and shares among professionals.
 **IMPORTANT: Write the LinkedIn post in the same language as the case study content below.**


Write a **scroll-stopping LinkedIn post** on the following story shown between '<<' and '>>':
 
'<<'{case_study_text}'>>'
 
Follow the structure, style, and tone instructions below carefully.
 
### **STRUCTURE: The Viral LinkedIn Framework**
 
1. **HOOK (1 line, max 10 words):**
 
   * Capture attention immediately with a thought-provoking question.
   * Keep it extremely short and punchy.
   * Example: "What if a piano could change a child's life?"
   * No hashtags, emojis, or links in the hook.
 
2. **STORY (4–6 very short paragraphs):**
 
 - Tell the story in ultra-short paragraphs (1–3 sentences each).
- Use one idea per paragraph.
- Add blank lines between paragraphs for visual breathing room and to preserve paragraph context.
- Format each sentence in the paragraph on a separate line, so sentences within a paragraph appear line-  by-line, but paragraphs are not broken up beyond that.
- Write like you speak — simple, human, conversational.
- Keep sentences short and punchy (5–12 words each).
- Be authentic and avoid jargon like "synergy," "game-changer," or "innovative solutions."
- Facts and emotions > adjectives and fluff.
- Show contrast: "Most schools see X. [Company] saw Y."
- Include NO MORE THAN 3 emojis total per ENTIRE POST.

 
3. **TAKEAWAY (1–2 very short lines):**
 
   * Summarize the key insight in a memorable, poetic way.
   * Keep it extremely concise (1–2 sentences max).
   * Example: "Sometimes, the most powerful tools for change don't run on code. They run on keys."
 
4. **CLOSING / ENGAGEMENT (1 line):**
 
   * End with a single **question** that invites comments.
   * Keep it short and natural.
   * Example: "Would you agree that every school should have access to music education like this?"
 
5. **HASHTAGS (optional, 3–5 hashtags):**
 
   * Add 3–5 relevant hashtags at the end, separated by spaces.
   * Example: "#Education #Music #Impact #Inclusion"
 
---
 
### 🧭 **STYLE GUIDELINES**
 
* **Tone:** Conversational, expert, and authentic — like a trusted peer, not a marketer.
* **Readability:** Write at a **middle-school reading level** (short, clear sentences).
* **Sentence length:** Keep most under **10–12 words**. Many should be 5–8 words.
* **Paragraph length:** Maximum 1–2 lines per paragraph. Use lots of white space.
* **Avoid:** Buzzwords, exclamation overuse, self-congratulation, or forced "corporate" tone.
* **Avoid robotic words:** NEVER use "Enter" (as in "Enter [company name]") - it sounds AI-generated and robotic. Instead, naturally introduce the company or person: "Meet [company]" or "Here's how [company]..." or just start with the story naturally.
* **Avoid "the results":** NEVER use "the results" - it sounds robotic and AI-generated. Instead, say what actually happened: "sales went up 30%", "they saved time", "it worked", "their numbers improved", "they saw huge improvements".
* **Use:** Line breaks for rhythm and white space — readability drives engagement. Add blank lines between paragraphs.
* **Voice:** Confident, empathetic, and human — share lessons, not lectures.
* **Emotion:** Include tension or contrast (e.g. "what I expected" vs. "what really happened").
* **Length:** Aim for **80–120 words total** — much shorter and more concise than typical posts. Be extremely concise.
* **Titles:** Don't use section titles or headers.
* **Formatting:** Use blank lines between paragraphs to create visual breathing room.
 
---
 
### ✅ **Final Output Checklist**
 
Before finalizing the post:
 
* [ ] Hook is extremely short (max 10 words) and curiosity-driven.
* [ ] Every paragraph is 1–2 lines maximum.
* [ ] Blank lines between paragraphs for visual breathing room.
* [ ] Story feels human, not "marketing copy."
* [ ] One clear insight or takeaway.
* [ ] Ends with one powerful question — not multiple CTAs.
* [ ] Total length is 80–120 words (much shorter than typical posts).
* [ ] 3–5 hashtags at the end (optional but recommended).
* [ ] Extremely concise — every word counts.

"""

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4",
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 210
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
        Create an exciting news flash style script based on this case study.
        Make it sound like breaking news with energy and excitement. Use phrases like "Breaking News!", "Amazing Results!", "Incredible Success!"
        Keep it concise but thrilling. The video should be approximately 30 seconds long when spoken at normal speed.
        
        Case study: {case_study_summary[:1500]}
        """
        
        try:
            return self.generate_text(prompt, max_tokens=120)
        except Exception as e:
            return f"Error generating HeyGen input: {str(e)}"
    
    def generate_heygen_newsflash_video_text(self, case_study_summary: str) -> str:
        """Generate input text for 30-second HeyGen newsflash video"""
        if not self.openai_api_key:
            return "AI service not available - API key not configured"
        
        prompt = f"""
        Create an exciting news flash style script based on this case study.
        Make it sound like breaking news with energy and excitement. Use phrases like "Breaking News!", "Amazing Results!", "Incredible Success!"
        
        **CRITICAL TIMING REQUIREMENT:**
        - The script MUST be exactly 30 seconds (30 seconds) when spoken at normal conversational pace
        - Target word count: 70-75 words (this ensures the video is approximately 30 seconds)
        - Average speaking pace is 140-150 words per minute, so 70-75 words will result in exactly 30 seconds
        - DO NOT exceed 75 words - this would make the video longer than 30 seconds
        - DO NOT go below 70 words - this would make the video shorter than 30 seconds
        - Prioritize impact while maintaining the exact 30-second duration
        
        **Requirements:**
        - Write it as if you're a news anchor delivering breaking news
        - Sound energetic and exciting - like breaking news
        - Use phrases like "Breaking News!", "Amazing Results!", "Incredible Success!"
        - Keep it concise but thrilling
        - Focus on the key highlights: what challenge was solved, how it was solved, and what happened
        - Use natural, everyday language - avoid corporate jargon
        - Make it feel like genuine breaking news, not a script written by AI
        
        **Style:**
        - Start with an attention-grabbing hook like "Breaking News!"
        - Tell the story in a way that feels urgent and exciting
        - Use varied sentence structure - mix short punchy sentences with longer flowing ones
        - Include natural emphasis and excitement
        - End with a strong conclusion that summarizes the impact
        
        Case study: {case_study_summary[:1500]}
        
        **IMPORTANT:** After writing the script, count the words. If it exceeds 75 words, rewrite it to be shorter. If it's below 70 words, expand it slightly. The final script MUST be between 70-75 words (exactly 30 seconds).
        
        Write ONLY the script text - no labels, no formatting, just the natural spoken words:
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 120,  # Adjusted to enforce 70-75 word limit
                "temperature": 0.8
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result["choices"][0]["message"]["content"].strip()
                
                # Validate word count
                words = generated_text.split()
                word_count = len(words)
                
                # If word count is outside 70-75 range, regenerate with stricter prompt
                if word_count > 75 or word_count < 70:
                    # Determine the issue
                    if word_count > 75:
                        issue = f"too long ({word_count} words - target is 70-75)"
                        instruction = "rewrite to be shorter"
                    else:
                        issue = f"too short ({word_count} words - target is 70-75)"
                        instruction = "expand it slightly"
                    
                    # Regenerate with stricter prompt emphasizing word limit
                    strict_prompt = f"""
                    Rewrite this script to be EXACTLY 70-75 words (exactly 30 seconds).
                    
                    Current script ({word_count} words):
                    {generated_text}
                    
                    Requirements:
                    - MUST be 70-75 words (currently {issue})
                    - Keep the energetic, breaking news tone
                    - Use phrases like "Breaking News!", "Amazing Results!", "Incredible Success!"
                    - Focus on key highlights: challenge, solution, impact
                    - {instruction}
                    - The script must be exactly 30 seconds when spoken
                    
                    Rewrite the script:
                    """
                    
                    strict_data = {
                        "model": "gpt-4",
                        "messages": [{"role": "user", "content": strict_prompt}],
                        "max_tokens": 120,
                        "temperature": 0.7
                    }
                    
                    retry_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=strict_data,
                        timeout=30
                    )
                    
                    if retry_response.status_code == 200:
                        retry_result = retry_response.json()
                        generated_text = retry_result["choices"][0]["message"]["content"].strip()
                        words = generated_text.split()
                        word_count = len(words)
                
                return generated_text
            else:
                return f"Error generating HeyGen newsflash video text: {response.status_code}"
                
        except Exception as e:
            return f"Error generating HeyGen newsflash video text: {str(e)}"
    
    def generate_heygen_1min_video_text(self, case_study_summary: str) -> str:
        """Generate input text for 1-minute HeyGen video - brief, human-sounding success story"""
        if not self.openai_api_key:
            return "AI service not available - API key not configured"
        
        prompt = f"""
        Transform this case study into a natural, conversational video script that tells a compelling success story.
        
        **CRITICAL TIMING REQUIREMENT:**
        - The script MUST be exactly 1 minute (60 seconds) when spoken at normal conversational pace
        - Target word count: 140-150 words (this ensures the video is approximately 60 seconds)
        - Average speaking pace is 140-150 words per minute, so 140-150 words will result in exactly 1 minute
        - DO NOT exceed 150 words - this would make the video longer than 1 minute
        - DO NOT go below 140 words - this would make the video shorter than 1 minute
        - Prioritize impact while maintaining the exact 1-minute duration
        
        **Requirements:**
        - Write it as if you're a real person genuinely excited about sharing a success story you witnessed
        - Sound completely human and conversational - like you're talking to a friend about something cool that happened
        - Do NOT use section names, headers, or labels (no "Introduction:", "Challenge:", "Solution:", etc.)
        - Do NOT just read the summary verbatim - tell the story naturally in your own words
        - Use excited but professional tone - enthusiastic but credible, like a real person would speak
        - Make it flow naturally from one thought to the next - use natural transitions like "so", "and", "but", "you know"
        - Focus on the key highlights: what challenge was solved, how it was solved, and what happened
        - Use natural, everyday language - avoid corporate jargon, AI-sounding phrases, or overly polished language
        - Use contractions when natural (I'm, we're, they've, it's) - real people use contractions
        - Make it feel like a genuine story being told by a real person, not a script written by AI
        - Be concise - use shorter sentences and cut unnecessary words to stay within the word limit
        - Use natural human expressions and phrasing - sound like someone actually talking, not reading from a script
        
        **CRITICAL - AVOID ROBOTIC LANGUAGE:**
        - NEVER use robotic-sounding phrases like "the results", "the outcome", "the solution", "the challenge"
        - NEVER use "Enter" (as in "Enter [company name]") - it sounds AI-generated and robotic. Instead, naturally introduce: "Meet [company]" or "Here's how [company]..." or just start with the story naturally.
        - NEVER use hardcoded-sounding phrases like "the best part", "honestly", "you know" when used formulaically - these sound AI-generated and repetitive
        - Avoid formulaic patterns that sound repeated or hardcoded - each script should feel unique and natural
        - Instead of "the results were amazing" → say "they saw huge improvements" or "it worked really well"
        - Instead of "the solution was implemented" → say "we did this" or "they tried this approach"
        - Instead of "the challenge was addressed" → say "they were struggling with this" or "the problem was..."
        - Instead of "the outcome exceeded expectations" → say "it went way better than they thought" or "they were blown away"
        - Instead of "the project achieved success" → say "it worked" or "they nailed it" or "it turned out great"
        - Instead of "the implementation resulted in" → say "after doing this, they..." or "once they did this..."
        - Instead of "the metrics improved" → say "their numbers went up" or "they saw better numbers"
        - Instead of "the client experienced" → say "the client saw" or "they noticed" or "they got"
        - Instead of "the process was optimized" → say "we made it better" or "they streamlined things"
        - Instead of "the strategy proved effective" → say "it worked" or "this approach really helped"
        - Avoid formal phrases like "furthermore", "moreover", "in addition", "consequently" - use "and", "so", "but", "also"
        - Avoid corporate speak like "leverage", "utilize", "facilitate", "implement" - use "use", "help", "do", "make"
        - Avoid passive voice - use active voice: "we did this" not "this was done"
        - Never say "the results" - say what actually happened: "they saved time", "sales went up", "it worked"
        - Never say "the solution" - say what it was: "this new system", "the app", "what we built"
        - Never say "the challenge" - describe the problem naturally: "they were struggling with...", "the issue was..."
        
        **Style:**
        - Start with a natural hook that draws people in - like how you'd start telling a friend about something interesting
        - Tell the story in a way that feels spontaneous and real - like you're actually remembering and sharing it
        - Use varied sentence structure - mix short punchy sentences with longer flowing ones, just like real speech
        - Include natural emphasis and excitement where appropriate - but keep it authentic, not over-the-top
        - Use natural human expressions sparingly and authentically - "so", "and", "but" are natural, but avoid overusing "honestly", "you know", "I mean" as they can sound formulaic and AI-generated when used too much
        - Avoid overly formal or corporate language - sound like a real person, not a company spokesperson
        - Use simple, direct language - real people don't use complex vocabulary when telling stories
        - Use active voice and direct language - "we helped them" not "assistance was provided"
        - Be specific and concrete - "sales went up 30%" not "positive results were achieved"
        - Use everyday words - "big" not "significant", "good" not "optimal", "fast" not "efficient"
        
        **Ending Style (CRITICAL - NEVER OMIT):**
        - You MUST ALWAYS include a complete, natural ending - the script must conclude properly
        - NEVER cut off mid-sentence or mid-thought - the ending is essential
        - End with a natural, satisfying conclusion that feels like a genuine reflection
        - Options: highlight the broader impact, express genuine excitement about what happened, or subtly invite further conversation
        - Avoid generic closings like "Thank you for watching" - instead, end with a thought that feels personal and authentic
        - The ending should feel like a natural pause in conversation, not a scripted sign-off
        - AVOID hardcoded-sounding phrases like "the best part", "honestly", "you know" when used formulaically - these sound AI-generated
        - Instead of "And honestly? The best part is..." → use more natural endings like "It's really cool to see how this changed things for them." or "They're already planning what's next, which is exciting." or "This kind of transformation is what makes the work meaningful."
        - Make each ending unique and natural - don't use formulaic patterns that sound repeated or hardcoded
        - IMPORTANT: Even if you're at 148 words, you MUST still include a complete ending sentence - adjust earlier content if needed, but never omit the ending
        
        Case study: {case_study_summary[:2000]}
        
        **CRITICAL - ENDING REQUIREMENT:**
        - The script MUST ALWAYS end with a complete, natural conclusion
        - NEVER cut off mid-sentence, mid-thought, or mid-word
        - The ending is ESSENTIAL and MUST be included - it's the most important part
        - Even if you're at 150 words, you MUST still include the complete ending
        - If needed, adjust earlier content to make room for the ending, but NEVER omit it
        - The script must be read from start to finish - the ending is never optional
        
        **IMPORTANT:** After writing the script, count the words. If it exceeds 150 words, rewrite it to be shorter while maintaining the natural, human tone. If it's below 140 words, expand it slightly. The final script MUST be between 140-150 words (exactly 1 minute) AND must include a complete ending. NEVER truncate or cut off the ending - the script must always be read until the end.
        
        Write ONLY the script text - no labels, no formatting, just the natural spoken words:
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 220,  # Adjusted to enforce 140-150 word limit (approximately 1 token = 0.75 words)
                "temperature": 0.8
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result["choices"][0]["message"]["content"].strip()
                
                # Validate word count and ending completeness
                words = generated_text.split()
                word_count = len(words)
                
                # Check if ending is complete (ends with punctuation)
                ends_with_punctuation = len(generated_text.rstrip()) > 0 and generated_text.rstrip()[-1] in ['.', '!', '?']
                
                # If word count is outside 140-150 range or ending is incomplete, regenerate with stricter prompt
                if word_count > 150 or word_count < 140 or not ends_with_punctuation:
                    # Determine the issue
                    if word_count > 150:
                        issue = f"too long ({word_count} words - target is 140-150)"
                        instruction = "rewrite to be shorter while keeping the ending"
                    elif word_count < 140:
                        issue = f"too short ({word_count} words - target is 140-150)"
                        instruction = "expand it slightly while keeping the natural tone and complete ending"
                    else:
                        issue = "incomplete ending"
                        instruction = "ensure it has a complete ending"
                    
                    # Regenerate with stricter prompt emphasizing word limit and complete ending
                    strict_prompt = f"""
                    Rewrite this script to be EXACTLY 140-150 words (exactly 1 minute) and ensure it has a complete ending.
                    
                    Current script ({word_count} words):
                    {generated_text}
                    
                    Requirements:
                    - MUST be 140-150 words (currently {issue})
                    - MUST end with a complete sentence (period, exclamation, or question mark)
                    - Keep the natural, human tone - sound like a real person telling a story, not AI
                    - NEVER use "Enter" (as in "Enter [company name]") - it sounds AI-generated and robotic. Instead, naturally introduce: "Meet [company]" or "Here's how [company]..." or just start with the story naturally.
                    - NEVER use robotic phrases like "the results", "the outcome", "the solution", "the challenge"
                    - Instead of "the results were amazing" → say "they saw huge improvements" or "it worked really well"
                    - Instead of "the solution was implemented" → say "we did this" or "they tried this approach"
                    - Instead of "the outcome exceeded expectations" → say "it went way better than they thought"
                    - Use natural, everyday language - avoid AI-sounding phrases like "amazing results", "incredible success"
                    - Use contractions naturally (I'm, we're, they've, it's) - real people use contractions
                    - NEVER use hardcoded-sounding phrases like "the best part", "honestly", "you know" when used formulaically - these sound AI-generated and repetitive
                    - Use natural human expressions sparingly and authentically - "so", "and", "but" are natural, but avoid overusing "honestly", "you know", "I mean" as they can sound formulaic
                    - Avoid corporate jargon or overly polished language - sound like a real person talking
                    - Avoid formulaic patterns that sound repeated or hardcoded - make each ending unique and natural
                    - Use active voice - "we helped them" not "assistance was provided"
                    - Be specific - "sales went up 30%" not "positive results were achieved"
                    - Include a complete ending that concludes the story properly
                    - {instruction}
                    - The script must be exactly 1 minute when spoken
                    - Make it sound like someone actually talking, not reading from a script
                    
                    Rewrite the script:
                    """
                    
                    strict_data = {
                        "model": "gpt-4",
                        "messages": [{"role": "user", "content": strict_prompt}],
                        "max_tokens": 250,
                        "temperature": 0.7
                    }
                    
                    retry_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=strict_data,
                        timeout=30
                    )
                    
                    if retry_response.status_code == 200:
                        retry_result = retry_response.json()
                        generated_text = retry_result["choices"][0]["message"]["content"].strip()
                        words = generated_text.split()
                        word_count = len(words)
                
                # Final validation - ensure it's within limits and has complete ending
                if word_count > 150:
                    # If still too long, return a note but don't truncate
                    print(f"Warning: Generated script is {word_count} words (target: 140-150). Returning as-is to preserve complete ending.")
                elif word_count < 140:
                    # If still too short, return a note
                    print(f"Warning: Generated script is {word_count} words (target: 140-150). Returning as-is to preserve complete ending.")
                
                # CRITICAL: Ensure ending is ALWAYS complete - never truncate or cut off
                # Check if ending is complete (ends with punctuation)
                final_ending_check = len(generated_text.rstrip()) > 0 and generated_text.rstrip()[-1] in ['.', '!', '?']
                
                if not final_ending_check:
                    # If ending is incomplete, add punctuation to ensure it's complete
                    # This is a safety net - the regeneration should have handled this, but we ensure it here
                    generated_text = generated_text.rstrip() + '.'
                    print(f"Note: Added punctuation to ensure complete ending.")
                
                # Final check: Verify the script has a complete ending before returning
                # We NEVER truncate - always return the full script with complete ending
                if len(generated_text.strip()) == 0:
                    return "Error: Generated script is empty. Please try again."
                
                # Return the complete script - NEVER truncated, ALWAYS with ending
                return generated_text
            else:
                return f"Error generating HeyGen 1-minute video text: {response.status_code}"
                
        except Exception as e:
            return f"Error generating HeyGen 1-minute video text: {str(e)}"
    
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
            return self.generate_text(prompt, max_tokens=450)
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
