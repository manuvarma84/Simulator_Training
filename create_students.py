from main import create_app
from models import User, College, db
from werkzeug.security import generate_password_hash
from datetime import datetime

app = create_app()

with app.app_context():
    # OPTIONAL: Create the college first if it doesn’t already exist
    if not College.query.filter_by(code="COL_1").first():
        college = College(name="College 1", code="COL_1", subscription_expiry=datetime(2025, 12, 31))
        db.session.add(college)
        db.session.commit()
        print("College created.")

    # Get the college we just added (or already exists)
    college = College.query.filter_by(code="COL_1").first()

    # Create student users
    for i in range(1, 4):
        email = f"student{i}@college.edu"
        if not User.query.filter_by(email=email).first():
            student = User(
                email=email,
                password_hash=generate_password_hash("student123"),
                role="student",
                college_id=college.id
            )
            db.session.add(student)
            print(f"Added {email}")
    
    db.session.commit()
    print("✅ Students created successfully.")
