from flask import Blueprint, redirect, request, jsonify, session
from flask_mail import Message
from sqlalchemy import create_engine
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError
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
from flask import url_for

bp = Blueprint('auth', __name__, url_prefix='/api')


@bp.route('/signup', methods=['POST'])
def api_signup():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate input using schema
        schema = UserCreateSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as e:
            error_response = UserFriendlyErrors.get_auth_error("validation_failed", e)
            return jsonify(error_response), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=validated_data['email'].lower()).first()
        if existing_user:
            error_response = UserFriendlyErrors.get_auth_error("user_exists")
            return jsonify(error_response), 409
        
        # Create new user using mapper
        new_user = UserMapper.dto_to_model(validated_data)
        
        db.session.add(new_user)
        db.session.commit()
        token = serializer.dumps(new_user.email, salt='email-confirm')
        verification_link = url_for('auth.verify', token=token, _external=True)
        send_email(new_user.email, verification_link)
        
        # Return response using mapper
        user_dto = UserMapper.model_to_dto(new_user)
        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user": user_dto
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        error_response = UserFriendlyErrors.get_auth_error("user_exists")
        return jsonify(error_response), 409
    except Exception as e:
        db.session.rollback()
        error_response = UserFriendlyErrors.get_general_error("server_error", e)
        return jsonify(error_response), 500

@bp.route('/login', methods=['POST'])
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
def api_logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({"message": "Logout successful"})

@bp.route('/user')
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