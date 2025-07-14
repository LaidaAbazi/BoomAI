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