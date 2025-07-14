"""
User-friendly error messages for the application
"""

class UserFriendlyErrors:
    """Centralized user-friendly error messages"""
    
    # Authentication errors
    AUTH_ERRORS = {
        "validation_failed": "Please check your information and try again.",
        "user_exists": "An account with this email already exists. Try logging in instead.",
        "invalid_credentials": "Email or password is incorrect. Please try again.",
        "account_locked": "Your account is temporarily locked due to too many failed attempts. Please try again in 15 minutes.",
        "not_authenticated": "Please log in to continue.",
        "user_not_found": "User account not found. Please contact support.",
        "email_verification_failed": "Email verification failed. Please try again or contact support.",
        "not_verified": "Please check your email for verification before logging in.",
        "network_error": "Connection problem. Please check your internet and try again."
    }
    
    # Case study errors
    CASE_STUDY_ERRORS = {
        "not_found": "Case study not found. It may have been deleted or you don't have access.",
        "missing_data": "Some required information is missing. Please fill in all fields.",
        "save_failed": "Failed to save your case study. Please try again.",
        "generation_failed": "Failed to generate content. Please try again in a moment.",
        "extraction_failed": "Could not extract information. Please check your text and try again.",
        "pdf_generation_failed": "Failed to create PDF. Please try again.",
        "word_generation_failed": "Failed to create Word document. Please try again.",
        "linkedin_generation_failed": "Failed to create LinkedIn post. Please try again."
    }
    
    # Media generation errors
    MEDIA_ERRORS = {
        "video_generation_failed": "Video creation failed. Please try again later.",
        "video_status_check_failed": "Could not check video status. Please refresh the page.",
        "podcast_generation_failed": "Podcast creation failed. Please try again later.",
        "podcast_status_check_failed": "Could not check podcast status. Please refresh the page.",
        "audio_load_failed": "Could not load audio. Please try again or use the direct link.",
        "rate_limit_exceeded": "Too many requests. Please wait a moment and try again.",
        "api_connection_failed": "Service temporarily unavailable. Please try again later.",
        "voice_config_error": "Voice settings are invalid. Please try without custom voice settings.",
        "music_config_error": "Music settings are invalid. Please try without background music."
    }
    
    # Interview errors
    INTERVIEW_ERRORS = {
        "session_not_found": "Interview session not found. Please start a new interview.",
        "transcript_missing": "Interview transcript is missing. Please try the interview again.",
        "link_generation_failed": "Failed to create interview link. Please try again.",
        "invalid_token": "Interview link is invalid or expired. Please request a new link.",
        "provider_not_found": "Provider interview not found. Please complete the provider interview first."
    }
    
    # General errors
    GENERAL_ERRORS = {
        "server_error": "Something went wrong on our end. Please try again later.",
        "database_error": "Database connection problem. Please try again.",
        "file_not_found": "File not found. It may have been moved or deleted.",
        "permission_denied": "You don't have permission to perform this action.",
        "timeout": "Request timed out. Please try again.",
        "invalid_request": "Invalid request. Please check your input and try again.",
        "maintenance": "System is under maintenance. Please try again later.",
        "unknown_error": "An unexpected error occurred. Please try again or contact support."
    }
    
    @staticmethod
    def get_auth_error(error_type, original_error=None):
        """Get user-friendly authentication error message"""
        message = UserFriendlyErrors.AUTH_ERRORS.get(error_type, UserFriendlyErrors.GENERAL_ERRORS["unknown_error"])
        return {
            "error": message,
            "technical_details": str(original_error) if original_error else None
        }
    
    @staticmethod
    def get_case_study_error(error_type, original_error=None):
        """Get user-friendly case study error message"""
        message = UserFriendlyErrors.CASE_STUDY_ERRORS.get(error_type, UserFriendlyErrors.GENERAL_ERRORS["unknown_error"])
        return {
            "error": message,
            "technical_details": str(original_error) if original_error else None
        }
    
    @staticmethod
    def get_media_error(error_type, original_error=None):
        """Get user-friendly media error message"""
        message = UserFriendlyErrors.MEDIA_ERRORS.get(error_type, UserFriendlyErrors.GENERAL_ERRORS["unknown_error"])
        return {
            "error": message,
            "technical_details": str(original_error) if original_error else None
        }
    
    @staticmethod
    def get_interview_error(error_type, original_error=None):
        """Get user-friendly interview error message"""
        message = UserFriendlyErrors.INTERVIEW_ERRORS.get(error_type, UserFriendlyErrors.GENERAL_ERRORS["unknown_error"])
        return {
            "error": message,
            "technical_details": str(original_error) if original_error else None
        }
    
    @staticmethod
    def get_general_error(error_type, original_error=None):
        """Get user-friendly general error message"""
        message = UserFriendlyErrors.GENERAL_ERRORS.get(error_type, UserFriendlyErrors.GENERAL_ERRORS["unknown_error"])
        return {
            "error": message,
            "technical_details": str(original_error) if original_error else None
        }
    
    @staticmethod
    def sanitize_technical_error(error_message):
        """Remove technical details from error messages for users"""
        technical_indicators = [
            "sqlalchemy", "database", "connection", "timeout", "integrity", 
            "constraint", "foreign key", "unique", "duplicate", "index",
            "api", "http", "status", "code", "exception", "traceback",
            "werkzeug", "flask", "jinja", "template", "render"
        ]
        
        error_lower = error_message.lower()
        for indicator in technical_indicators:
            if indicator in error_lower:
                return UserFriendlyErrors.GENERAL_ERRORS["server_error"]
        
        return error_message 