import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration with PostgreSQL SSL handling
    database_url = os.environ.get('DATABASE_URL') or 'sqlite:///./case_study.db'
    if database_url.startswith('postgres://'):
        # Convert postgres:// to postgresql:// for newer psycopg2 versions
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # PostgreSQL-specific configuration for Render
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 10,
        'pool_size': 5,
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'application_name': 'BoomAI'
        }
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-change-in-production'
    JWT_TOKEN_LOCATION = ['headers']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Security configurations
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_DURATION = timedelta(minutes=15)
    
    # API Keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    HEYGEN_API_KEY = os.environ.get('HEYGEN_API_KEY')
    PICTORY_CLIENT_ID = os.environ.get('PICTORY_CLIENT_ID')
    PICTORY_CLIENT_SECRET = os.environ.get('PICTORY_CLIENT_SECRET')
    PICTORY_USER_ID = os.environ.get('PICTORY_USER_ID')
    WONDERCRAFT_API_KEY = os.environ.get('WONDERCRAFT_API_KEY')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    
    # Override PostgreSQL settings for development
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 10,
        'pool_size': 5
    }

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 
