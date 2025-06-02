from functools import wraps
from flask import abort, current_app
from flask_login import current_user

def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check professor role and college access
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
            
        if current_user.role != 'professor':
            abort(403)
            
        # Verify simulation ownership
        if 'sim_id' in kwargs:
            sim = current_app.simulation_service.get_simulation(kwargs['sim_id'])
            if sim.college_id != current_user.college_id:
                abort(403)
                
        return f(*args, **kwargs)
    return decorated_function