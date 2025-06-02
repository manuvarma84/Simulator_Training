# main.py
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import datetime
import os
from extensions import db, login_manager, migrate  # Import from extensions.py

# Initialize extensions
#db = SQLAlchemy()
#login_manager = LoginManager()
#migrate = Migrate()  # Keep this after db initialization

# Import models HERE to ensure Alembic detects them

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['UPLOAD_FOLDER'] = 'simulation_packages'
    app.config['ALLOWED_EXTENSIONS'] = {'zip'}    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simulations.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Add context processor AFTER creating the app
    @app.context_processor
    def inject_datetime():
        return {'now': datetime.utcnow}

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate AFTER db

    # Create upload folder if not exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Add this line
    
    # Import models INSIDE the app context (critical for Alembic)
    with app.app_context():
        from models import User, College, Simulation, StudentSimulation  # <-- Move here

    # Configure login manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from professor.routes import prof_bp
    from student.routes import student_bp
    from auth.routes import auth_bp
    from admin.routes import admin_bp
    from business_simulation import bp as business_bp    
    
    # Register blueprints with proper prefixes
    app.register_blueprint(prof_bp)       # Already has url_prefix='/professor'
    app.register_blueprint(student_bp)    # Already has url_prefix='/student'
    app.register_blueprint(auth_bp)       # No prefix (handles /login, /register)
    app.register_blueprint(admin_bp)      # Should have its own prefix if needed
    app.register_blueprint(business_bp)  # Ensure this exists
    
    # Main route
    @app.route('/')
    def home():
        return render_template('index.html')

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)