import re
from langdetect import detect, LangDetectException

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    
    cleaned = (
        text.replace("•", "-")  
            .replace("—", "-")
            .replace("–", "-")
            .replace(""", '"')
            .replace(""", '"')
            .replace("'", "'")
            .replace("'", "'")
            .replace("£", "GBP ")
    )
    
    return cleaned.strip()

def detect_language(text):
    """Detect language of text and return full language name"""
    try:
        if not text or len(text.strip()) < 10:
            return "English"  # Default to English for short texts
        
        # Get the language code
        lang_code = detect(text)
        
        # Map language codes to full names - comprehensive list for OpenAI real-time API
        language_map = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pl': 'Polish',
            'sq': 'Albanian',
            'af': 'Afrikaans',
            'am': 'Amharic',
            'az': 'Azerbaijani',
            'be': 'Belarusian',
            'bg': 'Bulgarian',
            'bn': 'Bengali',
            'bs': 'Bosnian',
            'ca': 'Catalan',
            'ceb': 'Cebuano',
            'co': 'Corsican',
            'cs': 'Czech',
            'cy': 'Welsh',
            'da': 'Danish',
            'el': 'Greek',
            'eo': 'Esperanto',
            'et': 'Estonian',
            'eu': 'Basque',
            'fa': 'Persian',
            'fi': 'Finnish',
            'fy': 'Frisian',
            'ga': 'Irish',
            'gd': 'Scottish Gaelic',
            'gl': 'Galician',
            'gu': 'Gujarati',
            'ha': 'Hausa',
            'haw': 'Hawaiian',
            'he': 'Hebrew',
            'hmn': 'Hmong',
            'hr': 'Croatian',
            'ht': 'Haitian Creole',
            'hu': 'Hungarian',
            'hy': 'Armenian',
            'id': 'Indonesian',
            'ig': 'Igbo',
            'is': 'Icelandic',
            'jw': 'Javanese',
            'ka': 'Georgian',
            'kk': 'Kazakh',
            'km': 'Khmer',
            'kn': 'Kannada',
            'ky': 'Kyrgyz',
            'la': 'Latin',
            'lb': 'Luxembourgish',
            'lo': 'Lao',
            'lt': 'Lithuanian',
            'lv': 'Latvian',
            'mg': 'Malagasy',
            'mi': 'Maori',
            'mk': 'Macedonian',
            'ml': 'Malayalam',
            'mn': 'Mongolian',
            'mr': 'Marathi',
            'ms': 'Malay',
            'mt': 'Maltese',
            'my': 'Myanmar (Burmese)',
            'ne': 'Nepali',
            'nl': 'Dutch',
            'no': 'Norwegian',
            'ny': 'Chichewa',
            'or': 'Odia (Oriya)',
            'pa': 'Punjabi',
            'ps': 'Pashto',
            'ro': 'Romanian',
            'rw': 'Kinyarwanda',
            'si': 'Sinhala',
            'sk': 'Slovak',
            'sl': 'Slovenian',
            'sm': 'Samoan',
            'sn': 'Shona',
            'so': 'Somali',
            'sr': 'Serbian',
            'st': 'Sesotho',
            'su': 'Sundanese',
            'sv': 'Swedish',
            'sw': 'Swahili',
            'ta': 'Tamil',
            'te': 'Telugu',
            'tg': 'Tajik',
            'th': 'Thai',
            'tk': 'Turkmen',
            'tl': 'Filipino',
            'tr': 'Turkish',
            'tt': 'Tatar',
            'ug': 'Uyghur',
            'uk': 'Ukrainian',
            'ur': 'Urdu',
            'uz': 'Uzbek',
            'vi': 'Vietnamese',
            'xh': 'Xhosa',
            'yi': 'Yiddish',
            'yo': 'Yoruba',
            'zu': 'Zulu'
        }
        
        return language_map.get(lang_code, 'English')  # Default to English if language not in map
    except LangDetectException:
        return "English"  # Default to English if detection fails

def extract_names_from_case_study_fallback(text):
    """Fallback method to extract names from case study text"""
    # Simple regex-based extraction as fallback
    lines = text.split('\n')
    
    # Look for common patterns
    lead_entity = "Unknown"
    partner_entity = ""
    project_title = "Unknown Project"
    
    for line in lines[:20]:  # Check first 20 lines
        line = line.strip()
        
        # Look for company names (simple heuristic)
        if any(keyword in line.lower() for keyword in ['company', 'corporation', 'inc', 'ltd', 'llc']):
            if lead_entity == "Unknown":
                lead_entity = line.split()[0]  # Take first word as company name
        
        # Look for project titles
        if any(keyword in line.lower() for keyword in ['project', 'implementation', 'solution', 'transformation']):
            project_title = line
    
    return {
        "lead_entity": lead_entity,
        "partner_entity": partner_entity,
        "project_title": project_title
    }

def extract_names_from_case_study(text):
    """Extract names from case study text using AI or fallback"""
    try:
        # Try AI-based extraction first
        from app.services.ai_service import AIService
        ai_service = AIService()
        return ai_service.extract_names_from_case_study_llm(text)
    except Exception as e:
        print(f"AI extraction failed, using fallback: {e}")
        return extract_names_from_case_study_fallback(text) 

def clean_text_for_heygen(text):
    """Clean and validate text to prevent HeyGen from cutting off mid-word"""
    if not text:
        return ""
    
    # Basic cleaning
    cleaned = clean_text(text)
    
    # Remove any remaining special characters that might cause issues
    cleaned = re.sub(r'[^\w\s.,!?\-]', '', cleaned)
    
    # Ensure text ends with proper punctuation
    if cleaned and not cleaned[-1] in '.!?':
        cleaned += '.'
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def validate_heygen_text(text):
    """Validate text for HeyGen video generation - optimized for 30-40 seconds"""
    if not text:
        return {"valid": False, "message": "Text is empty"}
    
    # Check length (HeyGen 30-40 second limit: ~400 characters max)
    if len(text) > 400:
        return {"valid": False, "message": f"Text too long: {len(text)} characters (max 400 for 30-40 second video)"}
    
    # Check for incomplete sentences
    if text.count('.') == 0 and text.count('!') == 0 and text.count('?') == 0:
        return {"valid": False, "message": "Text must contain at least one complete sentence"}
    
    # Ensure text ends with proper punctuation
    if not text.strip().endswith(('.', '!', '?')):
        return {"valid": False, "message": "Text must end with proper punctuation"}
    
    # Check for mid-word cuts (enhanced check)
    words = text.split()
    for i, word in enumerate(words):
        # Check for very long words that might cause issues
        if len(word) > 25:  # Very long words might be problematic
            return {"valid": False, "message": f"Word too long: {word}"}
        
        # Check if word appears to be cut off (no punctuation but not the last word)
        if (i < len(words) - 1 and 
            len(word) > 1 and 
            word[-1] not in '.,!?-' and 
            not word.isalpha()):
            # This might be a cut word
            return {"valid": False, "message": f"Possible cut word detected: {word}"}
    
    # Check for proper sentence structure
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence.split()) < 2:
            return {"valid": False, "message": "Each sentence must have at least 2 words"}
    
    return {"valid": True, "message": "Text is valid for 30-40 second video"}

def safe_truncate_text(text, max_length=400):
    """Safely truncate text at sentence boundaries to prevent mid-word cuts"""
    if not text or len(text) <= max_length:
        return text
    
    # Find the last complete sentence within the limit
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')
    
    # Find the last sentence ending
    last_sentence_end = max(last_period, last_exclamation, last_question)
    
    if last_sentence_end > 0:
        return text[:last_sentence_end + 1]
    else:
        # If no sentence ending found, truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return text[:last_space] + "."
        else:
            # Last resort: truncate and add ellipsis
            return text[:max_length-3] + "..." 