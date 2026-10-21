"""
Authentication routes — login, register, logout.
This is provided for you. You can modify it if needed.

Notice what this does NOT do (these are things teams build):
  - check whether the user still works here (employment_status)
  - limit failed login attempts
  - record logins anywhere
  - expire sessions
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/home")
@login_required
def home():
    """Placeholder page after login. Point this at your own tool's main page."""
    return render_template("home.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Logged in as {user.display_name or user.username}.", "success")
            return redirect(url_for("auth.home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for("auth.register"))

        user = User(username=username, display_name=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
