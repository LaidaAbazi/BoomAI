"""
Language utilities for HeyGen and WonderCraft integration
"""
from app.utils.text_processing import detect_language

# WonderCraft supported languages
WONDERCRAFT_SUPPORTED_LANGUAGES = {
    'English', 'Spanish', 'Portuguese', 'French', 'German', 'Italian', 
    'Hindi', 'Arabic', 'Greek', 'Swedish', 'Danish', 'Dutch', 'Polish', 
    'Turkish', 'Ukrainian'
}

# Map detected language names to WonderCraft-compatible language names
# This handles variations in language detection
LANGUAGE_NORMALIZATION_MAP = {
    # English variants
    'English': 'English',
    
    # Spanish variants
    'Spanish': 'Spanish',
    'Español': 'Spanish',
    
    # Portuguese variants
    'Portuguese': 'Portuguese',
    'Português': 'Portuguese',
    
    # French variants
    'French': 'French',
    'Français': 'French',
    
    # German variants
    'German': 'German',
    'Deutsch': 'German',
    
    # Italian variants
    'Italian': 'Italian',
    'Italiano': 'Italian',
    
    # Hindi variants
    'Hindi': 'Hindi',
    'हिन्दी': 'Hindi',
    
    # Arabic variants
    'Arabic': 'Arabic',
    'العربية': 'Arabic',
    
    # Greek variants
    'Greek': 'Greek',
    'Ελληνικά': 'Greek',
    
    # Swedish variants
    'Swedish': 'Swedish',
    'Svenska': 'Swedish',
    
    # Danish variants
    'Danish': 'Danish',
    'Dansk': 'Danish',
    
    # Dutch variants
    'Dutch': 'Dutch',
    'Nederlands': 'Dutch',
    
    # Polish variants
    'Polish': 'Polish',
    'Polski': 'Polish',
    
    # Turkish variants
    'Turkish': 'Turkish',
    'Türkçe': 'Turkish',
    
    # Ukrainian variants
    'Ukrainian': 'Ukrainian',
    'Українська': 'Ukrainian',
}

# HeyGen voice ID mapping
# Only include languages with provided voice IDs
HEYGEN_VOICE_IDS = {
    'English': '4754e1ec667544b0bd18cdf4bec7d6a7',  # Current default
    'Spanish': '6ce26db0cb6f4e7881b85452619f7f19',
    'Portuguese': '6d282a9f296746568da9d65586935dba',
    'German': 'de691a68bd394d6fa8e29a6a63caede6',
    'French': '728ce6e94304471fae9cf02ad85ec9a2',
    'Italian': '5d70217a058845d082021f563ccc607b',
    'Swedish': 'f28d58e430a446fca6fbf1988164116f',
}

def normalize_language(language_name):
    """
    Normalize language name to WonderCraft-compatible format
    """
    if not language_name:
        return 'English'
    
    # Normalize to title case
    normalized = language_name.strip().title()
    
    # Check if we have a mapping
    return LANGUAGE_NORMALIZATION_MAP.get(normalized, normalized)

def is_wondercraft_supported(language):
    """
    Check if a language is supported by WonderCraft
    """
    normalized = normalize_language(language)
    return normalized in WONDERCRAFT_SUPPORTED_LANGUAGES

def get_wondercraft_language(language):
    """
    Get WonderCraft-compatible language name, or return English if not supported
    """
    normalized = normalize_language(language)
    
    if normalized in WONDERCRAFT_SUPPORTED_LANGUAGES:
        return normalized
    
    # If not supported, return English as fallback
    print(f"Warning: Language '{language}' (normalized: '{normalized}') not supported by WonderCraft. Using English.")
    return 'English'

def get_heygen_voice_id(language):
    """
    Get HeyGen voice ID for a given language
    Falls back to English if language-specific voice not available
    """
    normalized = normalize_language(language)
    voice_id = HEYGEN_VOICE_IDS.get(normalized)
    
    if voice_id:
        return voice_id
    
    # Fallback to English
    print(f"Warning: No HeyGen voice ID configured for '{normalized}'. Using English voice.")
    return HEYGEN_VOICE_IDS['English']

def detect_and_normalize_language(text):
    """
    Detect language from text and return normalized language name
    """
    if not text:
        return 'English'
    
    detected = detect_language(text)
    return normalize_language(detected)

