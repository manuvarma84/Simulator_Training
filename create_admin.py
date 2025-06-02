from main import create_app
from extensions import db
from models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    admin = User(
        email="admin2@system.com",
        password_hash=generate_password_hash("admin123"),
        role="admin",
        college_id="1"  # Admin might not belong to a specific college
    )
    db.session.merge(admin)
    db.session.commit()
    print("Admin created!")
