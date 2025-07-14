import re
import html

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False
    return True

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    
    # HTML escape the text
    sanitized = html.escape(text.strip())
    return sanitized

def validate_case_study_data(data):
    """Validate case study data"""
    errors = []
    
    if not data.get('title', '').strip():
        errors.append("Title is required")
    
    if not data.get('final_summary', '').strip():
        errors.append("Final summary is required")
    
    return errors 