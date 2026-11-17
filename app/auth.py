"""
Authentication routes — login, register, logout.
This is provided for you. You can modify it if needed.

Notice what this does NOT do (these are things teams build):
  - check whether the user still works here (employment_status)
  - limit failed login attempts
  - record logins anywhere
  - expire sessions
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, LoginLog
from app import limiter

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

@auth_bp.before_app_request
def enforce_active_employment():
    """Immediately kick out users whose employment_status changes mid-session."""
    if current_user.is_authenticated and current_user.employment_status != "employed":
        logout_user()
        session.clear()
        flash("Your access has been revoked.", "danger")
        return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        # Check password first so active and terminated accounts take the same response time
        if user and user.check_password(password):
            # Block former employees even if they know their old password
            if user.employment_status != "employed":
                log = LoginLog(
                    username=username, ip_address=request.remote_addr, success=False
                )
                db.session.add(log)
                db.session.commit()

                flash("Invalid username or password.", "danger")
                return render_template("login.html")

            # Valid active employee — log success and start expiring session
            log = LoginLog(
                username=username, ip_address=request.remote_addr, success=True
            )
            db.session.add(log)
            db.session.commit()

            login_user(user)
            session.permanent = True  # Ensures PERMANENT_SESSION_LIFETIME applies
            flash(f"Logged in as {user.display_name or user.username}.", "success")
            return redirect(url_for("auth.home"))

        # Record failed logins for wrong passwords or unknown usernames
        log = LoginLog(username=username, ip_address=request.remote_addr, success=False)
        db.session.add(log)
        db.session.commit()

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    abort(404)
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

@auth_bp.route("/admin/login-history")
@login_required
def login_history():
    # Restrict access to administrators only.
    if not current_user.is_admin:
        abort(403)

    # Show the newest login attempts first.
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).limit(100).all()

    # Display the login records using the HTML dashboard.
    return render_template("login_history.html", logs=logs)

# Require a CSRF-protected POST request to log out.
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
