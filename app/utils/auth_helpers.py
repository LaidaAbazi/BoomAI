from functools import wraps
from flask import session, jsonify, request, redirect, url_for
from app.models import User, InviteToken

def get_current_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

def get_current_user():
    """Get current user object from session"""
    user_id = get_current_user_id()
    if user_id:
        return User.query.get(user_id)
    return None

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        user = User.query.get(user_id)
        if not user:
            session.clear()
            return jsonify({"error": "User not found"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def login_or_token_required(f):
    """Decorator that accepts either session login OR client interview token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First try session authentication
        user_id = get_current_user_id()
        if user_id:
            user = User.query.get(user_id)
            if user:
                return f(*args, **kwargs)
        
        # If no session, try token authentication
        # Check both request body and query parameters for token
        data = request.get_json() or {}
        token = data.get('token') or request.args.get('token')
        
        if token:
            # Validate the token - don't check if used since tokens are marked used on first access
            invite_token = InviteToken.query.filter_by(token=token).first()
            if invite_token:
                # Token is valid, allow access
                return f(*args, **kwargs)
        
        # If neither session nor valid token, deny access
        return jsonify({"error": "Authentication required"}), 401
    
    return decorated_function

def subscription_required(f):
    """Decorator to require active subscription for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        user = User.query.get(user_id)
        if not user:
            session.clear()
            return jsonify({"error": "User not found"}), 401
        
        if not user.has_active_subscription:
            return jsonify({
                "error": "Active subscription required",
                "needs_subscription": True,
                "message": "You need an active subscription to access this feature"
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function 