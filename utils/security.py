"""
🔒 Smart Authentication Route Protection 
Decorator-based route security for Flask
"""

from functools import wraps
from flask import session, jsonify, request, redirect, url_for
from datetime import datetime, timedelta
import secrets

# Session management
def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            if session['user_role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def audit_action(action_type, resource=None):
    """Decorator to log all actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Log the action
            user_id = session.get('user_id', 'ANONYMOUS')
            ip_address = request.remote_addr
            
            # Execute the function
            result = f(*args, **kwargs)
            
            # Log success/failure
            # Note: You'll implement actual logging in the database
            print(f"🔍 AUDIT: {user_id} performed {action_type} on {resource} from {ip_address}")
            
            return result
        return decorated_function
    return decorator

# Token generation for password reset, etc.
def generate_secure_token():
    """Generate secure random token"""
    return secrets.token_urlsafe(32)

# Session helpers
def create_user_session(user_id, role, village_code=None):
    """Create authenticated session"""
    session['user_id'] = user_id
    session['user_role'] = role
    session['village_code'] = village_code
    session['login_time'] = datetime.utcnow().isoformat()
    session.permanent = True

def clear_user_session():
    """Clear user session on logout"""
    session.clear()

def get_current_user():
    """Get current authenticated user info"""
    return {
        'user_id': session.get('user_id'),
        'role': session.get('user_role'),
        'village_code': session.get('village_code'),
        'login_time': session.get('login_time')
    }