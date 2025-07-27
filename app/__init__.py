from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flasgger import Swagger, swag_from
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
swagger = Swagger()

mail = Mail()
serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY", "dev_secret_key"))

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__, 
                static_folder='../static', 
                static_url_path='',
                template_folder='../templates')
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev_secret_key")
    
    # Database configuration with better error handling
    database_url = os.getenv("DATABASE_URL", "sqlite:///./case_study.db")
    
    # Handle Render's PostgreSQL URL format
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # JWT configuration
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret")
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    
    # Flasgger configuration
    app.config['SWAGGER'] = {
        'title': 'StoryBoom AI API',
        'uiversion': 3,
        'openapi': '3.0.2',
        'description': 'API for StoryBoom AI - Case Study Generation Platform',
        'termsOfService': '',
        'contact': {
            'name': 'StoryBoom AI Support',
            'email': 'storyboomai@gmail.com'
        },
        'license': {
            'name': 'MIT',
            'url': 'https://opensource.org/licenses/MIT'
        },
        'licenseUrl': 'https://opensource.org/licenses/MIT',
        'specs': [
            {
                'endpoint': 'apispec_1',
                'route': '/apispec_1.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            }
        ],
        'specs_route': '/apidocs/',
        'securityDefinitions': {
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Session-based authentication (login required)'
            }
        },
        'security': [
            {
                'ApiKeyAuth': []
            }
        ],
        'components': {
            'schemas': {
                'User': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer', 'description': 'User ID'},
                        'first_name': {'type': 'string', 'description': 'User\'s first name'},
                        'last_name': {'type': 'string', 'description': 'User\'s last name'},
                        'email': {'type': 'string', 'format': 'email', 'description': 'User\'s email address'},
                        'company_name': {'type': 'string', 'description': 'User\'s company name'},
                        'created_at': {'type': 'string', 'format': 'date-time', 'description': 'Account creation date'},
                        'last_login': {'type': 'string', 'format': 'date-time', 'description': 'Last login date'},
                        'is_verified': {'type': 'boolean', 'description': 'Email verification status'}
                    }
                },
                'CaseStudy': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'title': {'type': 'string'},
                        'final_summary': {'type': 'string'},
                        'meta_data_text': {'type': 'string'},
                        'created_at': {'type': 'string', 'format': 'date-time'},
                        'updated_at': {'type': 'string', 'format': 'date-time'},
                        'video_status': {'type': 'string'},
                        'pictory_video_status': {'type': 'string'},
                        'podcast_status': {'type': 'string'},
                        'labels': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/Label'}
                        }
                    }
                },
                'Label': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'}
                    }
                },
                'Feedback': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'content': {'type': 'string'},
                        'rating': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                        'feedback_type': {'type': 'string'},
                        'created_at': {'type': 'string', 'format': 'date-time'},
                        'feedback_summary': {'type': 'string'}
                    }
                },
                'Error': {
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string'},
                        'message': {'type': 'string'},
                        'status': {'type': 'string'}
                    }
                }
            }
        }
    }
    
    # Security configurations
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='storyboomai@gmail.com',
        MAIL_PASSWORD='rwgmqfqazoyaaxhm',  # App Password, not real Gmail password
        MAIL_DEFAULT_SENDER='storyboomai@gmail.com',
        SESSION_COOKIE_SECURE=False,  # Set to False to allow HTTP cookies for testing
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        MAX_LOGIN_ATTEMPTS=5,
        LOGIN_LOCKOUT_DURATION=timedelta(minutes=15)
    )
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    swagger.init_app(app)
    
    # Enable CORS
        # Enable CORS with credentials support
    CORS(
        app,
        supports_credentials=True,
        origins=[
            "http://scg8g8wcc80048c00wc4s48g.91.99.166.133.sslip.io",
            "http://localhost:3000",
            "http://localhost:5000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000",
            "https://boomai.onrender.com"
        ],
        methods=["GET", "POST", "OPTIONS", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        expose_headers=["Content-Type", "Authorization"]
    )
    
    # Add global CORS preflight handler
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            origin = request.headers.get('Origin', '')
            
            # Allow specific origins and any sslip.io domain
            allowed_origins = [
                "http://localhost:3000",
                "http://localhost:5000", 
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5000",
                "https://boomai.onrender.com"
            ]
            
            # Check if origin is in allowed list or is an sslip.io domain
            if origin in allowed_origins or origin.endswith('.sslip.io'):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE, PATCH'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                return response
    
    # Add global CORS response handler
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get('Origin', '')
        
        # Allow specific origins and any sslip.io domain
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000",
            "https://boomai.onrender.com"
        ]
        
        # Check if origin is in allowed list or is an sslip.io domain
        if origin in allowed_origins or origin.endswith('.sslip.io'):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE, PATCH'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        return response
    
    # Import models after db initialization
    with app.app_context():
        from app.models import User, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken, Label, Feedback
        
        # Ensure database tables exist
        try:
            logger.info("Checking database connection...")
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            
            # Create tables if they don't exist
            logger.info("Creating database tables if they don't exist...")
            db.create_all()
            logger.info("Database tables ready")
            
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            # Don't fail the app startup, but log the error
    
    # Register blueprints
    from app.routes import auth, case_studies, interviews, media, api, metadata
    app.register_blueprint(auth.bp)
    app.register_blueprint(case_studies.bp)
    app.register_blueprint(interviews.bp)
    app.register_blueprint(media.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(metadata.metadata_bp)
    
    # Register main routes
    from app.routes import main
    app.register_blueprint(main.bp)
    
    return app 
