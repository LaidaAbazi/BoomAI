from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

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
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///./case_study.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # JWT configuration
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret")
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    
    # Security configurations
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='storyboomai@gmail.com',
        MAIL_PASSWORD='rwgmqfqazoyaaxhm',  # App Password, not real Gmail password
        MAIL_DEFAULT_SENDER='storyboomai@gmail.com',
        SESSION_COOKIE_SECURE=True,
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
    # Enable CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Import models after db initialization
    with app.app_context():
        from app.models import User, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken, Label, Feedback
    
    # Register blueprints
    from app.routes import auth, case_studies, interviews, media, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(case_studies.bp)
    app.register_blueprint(interviews.bp)
    app.register_blueprint(media.bp)
    app.register_blueprint(api.bp)
    
    # Register main routes
    from app.routes import main
    app.register_blueprint(main.bp)
    
    return app 