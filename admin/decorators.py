# student/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(role):
    def decorator(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            # Ensure the user is logged in and has the correct role
            if not current_user.is_authenticated or current_user.role != role:
                abort(403)  # Forbidden access
            return func(*args, **kwargs)
        return decorated_view
    return decorator