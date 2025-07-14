from functools import wraps
from flask import session, jsonify
from app.models import User

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