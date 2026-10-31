"""
App factory. This wires up Flask, the database, and login management.
You shouldn't need to change this file.
"""

import os
from flask import Flask
from flask_login import LoginManager
from app.models import db, bcrypt, User


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///astrolink.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Restrict when browsers send session cookies from other websites.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Prevent JavaScript from directly reading session cookies.
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))

        # Reject existing sessions belonging to former employees.
        if user and user.employment_status != "employed":
            return None

        return user

    # Auth routes (login, register, logout) — provided for you
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)

    # Your routes go here — register new blueprints below
    # Example:
    #   from app.your_feature import your_bp
    #   app.register_blueprint(your_bp)
    from app.stations import stations_bp

    app.register_blueprint(stations_bp)

    with app.app_context():
        db.create_all()

    return app
