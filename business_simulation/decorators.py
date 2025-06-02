# business_simulation/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user

# Add student_required decorator
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Existing professor_required decorator
def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'professor':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function