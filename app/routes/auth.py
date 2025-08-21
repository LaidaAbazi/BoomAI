from flask import Blueprint, redirect, request, jsonify, session
from flask_mail import Message
from sqlalchemy import create_engine
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import datetime, timedelta
from app.models import db, User
from app.mappers.user_mapper import UserMapper
from app.schemas.user_schemas import UserCreateSchema, UserLoginSchema
from marshmallow import ValidationError
from app.utils.error_messages import UserFriendlyErrors
import os
from sqlalchemy.orm.session import sessionmaker
from app import serializer, mail
from sqlalchemy.engine.create import create_engine
from flask import url_for, current_app
from flasgger import swag_from
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__, url_prefix='/api')


@bp.route('/signup', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Register a new user',
    'description': 'Create a new user account',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['first_name', 'last_name', 'email', 'password'],
                    'properties': {
                        'first_name': {'type': 'string', 'minLength': 1, 'maxLength': 100},
                        'last_name': {'type': 'string', 'minLength': 1, 'maxLength': 100},
                        'email': {'type': 'string', 'format': 'email'},
                        'password': {'type': 'string', 'minLength': 8},
                        'company_name': {'type': 'string', 'maxLength': 255}
                    }
                }
            }
        }
    },
    'responses': {
        201: {
            'description': 'User created successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'},
                            'user': {'$ref': '#/components/schemas/User'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Validation error'},
        409: {'description': 'User already exists'}
    }
})
def api_signup():
    """User registration endpoint"""
    try:
        # Check database connection first
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
        except Exception as db_error:
            logger.error(f"Database connection failed: {str(db_error)}")
            logger.error(f"Database URL: {os.getenv('DATABASE_URL', 'Not set')}")
            error_response = UserFriendlyErrors.get_general_error("database_error", db_error)
            return jsonify(error_response), 500
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received in signup request")
            error_response = UserFriendlyErrors.get_general_error("invalid_request")
            return jsonify(error_response), 400
        
        logger.info(f"Processing signup request for email: {data.get('email', 'unknown')}")
        
        # Validate input using schema
        schema = UserCreateSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as e:
            logger.warning(f"Validation error in signup: {str(e)}")
            error_response = UserFriendlyErrors.get_auth_error("validation_failed", e)
            return jsonify(error_response), 400
        
        # Check if user already exists
        try:
            existing_user = User.query.filter_by(email=validated_data['email'].lower()).first()
            if existing_user:
                logger.info(f"User already exists: {validated_data['email']}")
                error_response = UserFriendlyErrors.get_auth_error("user_exists")
                return jsonify(error_response), 409
        except Exception as query_error:
            logger.error(f"Error checking existing user: {str(query_error)}")
            logger.error(f"Query error type: {type(query_error)}")
            error_response = UserFriendlyErrors.get_general_error("database_error", query_error)
            return jsonify(error_response), 500
        
        # Create new user using mapper
        try:
            new_user = UserMapper.dto_to_model(validated_data)
            logger.info(f"User model created, attempting to save to database...")
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"User created successfully: {new_user.email}")
        except IntegrityError as integrity_error:
            db.session.rollback()
            logger.error(f"Integrity error during user creation: {str(integrity_error)}")
            error_response = UserFriendlyErrors.get_auth_error("user_exists")
            return jsonify(error_response), 409
        except OperationalError as op_error:
            db.session.rollback()
            logger.error(f"Operational error during user creation: {str(op_error)}")
            logger.error(f"Operational error type: {type(op_error)}")
            error_response = UserFriendlyErrors.get_general_error("database_error", op_error)
            return jsonify(error_response), 500
        except Exception as create_error:
            db.session.rollback()
            logger.error(f"Unexpected error during user creation: {str(create_error)}")
            logger.error(f"Create error type: {type(create_error)}")
            import traceback
            logger.error(f"Create error traceback: {traceback.format_exc()}")
            error_response = UserFriendlyErrors.get_general_error("database_error", create_error)
            return jsonify(error_response), 500
        
        # Generate verification token
        try:
            token = serializer.dumps(new_user.email, salt='email-confirm')
            # Use config BASE_URL which falls back to local development
            BASE_URL = current_app.config.get('BASE_URL', os.getenv("BASE_URL", "https://storyboom.ai"))
            verification_link = f"{BASE_URL}/api/verify/{token}"
        except Exception as token_error:
            logger.error(f"Error generating verification token: {str(token_error)}")
            # Continue without verification token
        
        # Try to send email, but don't fail if it doesn't work
        try:
            send_email(new_user.email, verification_link)
            logger.info(f"Verification email sent to: {new_user.email}")
        except Exception as email_error:
            logger.error(f"Email sending failed: {email_error}")
            # Continue with signup even if email fails
        
        # Return response using mapper
        try:
            user_dto = UserMapper.model_to_dto(new_user)
            return jsonify({
                "success": True,
                "message": "User created successfully",
                "user": user_dto
            }), 201
        except Exception as dto_error:
            logger.error(f"Error creating user DTO: {str(dto_error)}")
            # Return basic success response if DTO creation fails
            return jsonify({
                "success": True,
                "message": "User created successfully",
                "user": {
                    "id": new_user.id,
                    "email": new_user.email,
                    "first_name": new_user.first_name,
                    "last_name": new_user.last_name
                }
            }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error in signup: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        error_response = UserFriendlyErrors.get_general_error("server_error", e)
        return jsonify(error_response), 500

@bp.route('/login', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'summary': 'User login',
    'description': 'Authenticate user and create session',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['email', 'password'],
                    'properties': {
                        'email': {'type': 'string', 'format': 'email'},
                        'password': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Login successful',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'},
                            'user': {'$ref': '#/components/schemas/User'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Invalid credentials'},
        423: {'description': 'Account locked'}
    }
})
def api_login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        # Validate input using schema
        schema = UserLoginSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as e:
            error_response = UserFriendlyErrors.get_auth_error("validation_failed", e)
            return jsonify(error_response), 400
        
        email = validated_data['email'].lower()
        password = validated_data['password']
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            error_response = UserFriendlyErrors.get_auth_error("invalid_credentials")
            return jsonify(error_response), 401
        
        # Check if account is locked
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            error_response = UserFriendlyErrors.get_auth_error("account_locked")
            return jsonify(error_response), 423
        
        if not user.is_verified:
            error_response = UserFriendlyErrors.get_auth_error("not_verified")
            return jsonify(error_response), 401
        
        # Verify password
        if not check_password_hash(user.password_hash, password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
            
            db.session.commit()
            error_response = UserFriendlyErrors.get_auth_error("invalid_credentials")
            return jsonify(error_response), 401
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Store user info in session
        session['user_id'] = user.id
        session['user_email'] = user.email
        
        # Return response using mapper
        user_dto = UserMapper.model_to_dto(user)
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": user_dto
        })
        
    except Exception as e:
        error_response = UserFriendlyErrors.get_general_error("server_error", e)
        return jsonify(error_response), 500

@bp.route('/logout', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'summary': 'User logout',
    'description': 'End user session',
    'responses': {
        200: {
            'description': 'Logout successful',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def api_logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({"message": "Logout successful"})

@bp.route('/user')
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Get current user',
    'description': 'Retrieve current user information',
    'responses': {
        200: {
            'description': 'User information retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'user': {'$ref': '#/components/schemas/User'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'},
        404: {'description': 'User not found'}
    }
})
def api_user():
    """Get current user information"""
    from app.utils.auth_helpers import get_current_user_id
    
    user_id = get_current_user_id()
    if not user_id:
        error_response = UserFriendlyErrors.get_auth_error("not_authenticated")
        return jsonify(error_response), 401
    
    user = User.query.get(user_id)
    if not user:
        error_response = UserFriendlyErrors.get_auth_error("user_not_found")
        return jsonify(error_response), 404
    
    # Return response using mapper
    user_dto = UserMapper.model_to_dto(user)
    return jsonify({"user": user_dto}) 

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./case_study.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@bp.route('/verify/<token>', methods=['GET'])
def verify(token):
    local_session = SessionLocal()
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except Exception as e:
        print("DEBUG: Token error:", e)
        return 'Invalid or expired token.'

    user = local_session.query(User).filter_by(email=email).first()


    if user:
        if user.is_verified:  # type: ignore
            local_session.close()
            return 'Account already verified.'

        user.is_verified = True  # type: ignore
        local_session.commit()

        session['user_id'] = user.id

        local_session.close()
        return redirect('/dashboard', 302)

    local_session.close()
    return 'User not found.'


def send_email(to, link):
    try:
        msg = Message('Verify Your Email', recipients=[to])
        msg.body = f'Click this link to verify your email: {link}'
        mail.send(msg)
    except Exception as e:
        print(f"Email sending failed: {e}")