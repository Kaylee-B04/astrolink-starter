"""
Mark an employee as having left the company.

    docker compose exec web python offboard.py tgarcia

They can no longer log in, and any session they already have ends on
their next request (see load_user in app/__init__.py).
"""
import sys
from app import create_app
from app.models import db, User

if len(sys.argv) != 2:
    sys.exit("Usage: python offboard.py <username>")

app = create_app()
with app.app_context():
    user = User.query.filter_by(username=sys.argv[1]).first()
    if not user:
        sys.exit(f"No such user: {sys.argv[1]}")
    user.employment_status = "left"
    db.session.commit()
    print(f"{user.username} marked as left.")