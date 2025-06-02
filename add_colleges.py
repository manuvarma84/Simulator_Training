from main import create_app
from models import db, College
from datetime import datetime
from sqlalchemy.exc import IntegrityError

app = create_app()

with app.app_context():
    # Define colleges with unique codes
    colleges = [
        {"id": "1", "name": "College 1", "code": "COL_1", "subscription_expiry": datetime(2025, 12, 31)},
        {"id": "2", "name": "College 2", "code": "COL_2", "subscription_expiry": datetime(2025, 6, 30)},
        {"id": "3", "name": "College 3", "code": "COL_3", "subscription_expiry": datetime(2026, 1, 15)},
    ]

    try:
        for col in colleges:
            # Check if college exists first
            existing = College.query.filter_by(code=col["code"]).first()
            if not existing:
                college = College(
                    id=col["id"],
                    name=col["name"],
                    code=col["code"],
                    subscription_expiry=col["subscription_expiry"]
                )
                db.session.add(college)
            else:
                print(f"⚠️ College with code {col['code']} already exists. Skipping.")
        
        db.session.commit()
        print("✅ Colleges added/updated successfully.")

    except IntegrityError as e:
        db.session.rollback()
        print(f"❌ Error: {str(e)}")
        print("🔧 Solution: Delete the database file and try again")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Unexpected error: {str(e)}")