"""Assign roles to the test accounts. Run after seed.py."""
from app import create_app
from app.models import db, User

ROLES = {
    "admin": "admin",
    "jchen": "operator",
    "mkowalski": "operator",
    "intern22": "viewer",
    "tgarcia": "viewer",
}

app = create_app()
with app.app_context():
    for username, role in ROLES.items():
        user = User.query.filter_by(username=username).first()
        if user:
            user.role = role
            print(f"{username} -> {role}")
    db.session.commit()