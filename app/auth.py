"""
Authentication routes: login, 2FA, register, logout.

Login rules:
  1. Only CURRENT employees (employment_status == "employed") can log in.
     Former employees (e.g. tgarcia) are rejected even with the right password.
  2. Every employee must enable 2FA. New users are forced to enroll on first
     login, and after that must enter a valid authenticator code each time.
     login_user() is only ever called from _complete_login(), after all checks.
  3. Failed attempts are rate limited and recorded in LoginLog.
"""
2fa-login

import base64
import io
import time

import pyotp
import qrcode
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, session)

from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session, current_app
main
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, bcrypt, User, LoginLog
from app import limiter

auth_bp = Blueprint("auth", __name__)

PENDING_TTL = 300      # seconds a user has to enter their 2FA code
MAX_2FA_TRIES = 5      # wrong codes allowed before they must re-enter a password

# Used so a failed lookup takes as long as a real password check. Without it,
# unknown users and former employees respond faster, which leaks who is
# (or was) an employee.
DUMMY_HASH = bcrypt.generate_password_hash("not-a-real-password").decode("utf-8")


def _is_current_employee_login(user, password):
    """True only for a real, currently employed user with the right password."""
    if user is None:
        bcrypt.check_password_hash(DUMMY_HASH, password)
        return False
    password_ok = user.check_password(password)  # always runs, even for former employees
    return password_ok and user.employment_status == "employed"


def _clear_pending():
    for key in ("pending_2fa_user_id", "pending_2fa_at", "pending_2fa_tries"):
        session.pop(key, None)


def _complete_login(user):
    """The only place login_user() runs, so it can't happen before 2FA."""
    db.session.add(LoginLog(username=user.username,
                            ip_address=request.remote_addr, success=True))
    db.session.commit()
    session.permanent = True   # applies PERMANENT_SESSION_LIFETIME (idle timeout, see __init__.py)
    login_user(user)
    flash(f"Logged in as {user.display_name or user.username}.", "success")


# Pages a logged-in employee may reach before finishing 2FA enrollment.
ENROLLMENT_ALLOWED = {"auth.setup_2fa", "auth.logout", "static"}


@auth_bp.before_app_request
def require_2fa_enrollment():
    """
    Every logged-in employee must have 2FA enabled. Until they do, any page
    other than the setup page (and logout) redirects to setup. Runs for ALL
    blueprints, so new pages added later are covered automatically.
    """
    # request.endpoint is None for URLs that don't exist (e.g. the browser's
    # automatic /favicon.ico request). Those just 404; don't flash or redirect.
    if (current_user.is_authenticated
            and request.endpoint is not None
            and not current_user.is_2fa_enabled
            and request.endpoint not in ENROLLMENT_ALLOWED):
        flash("Two-factor authentication is required. Set it up to continue.", "danger")
        return redirect(url_for("auth.setup_2fa"))


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

SESSION_TIMEOUT = timedelta(minutes=15)

@auth_bp.before_app_request
def enforce_active_employment():
    # Allow session cookies over plain HTTP when testing locally without modifying __init__.py
    if request.host.startswith(("localhost", "127.0.0.1")) and not request.is_secure:
        current_app.config["SESSION_COOKIE_SECURE"] = False
    """Kick out terminated users or sessions idle longer than 15 minutes."""
    if current_user.is_authenticated:
        # 1. Check active employment
        if current_user.employment_status != "employed":
            logout_user()
            session.clear()
            flash("Your access has been revoked.", "danger")
            return redirect(url_for("auth.login"))

        # 2. Enforce 15-minute idle session timeout
        now = datetime.now(timezone.utc)
        last_active = session.get("last_active")
        if last_active and (now - datetime.fromisoformat(last_active)) > SESSION_TIMEOUT:
            logout_user()
            session.clear()
            flash("Your session expired due to inactivity. Please log in again.", "warning")
            return redirect(url_for("auth.login"))

        session["last_active"] = now.isoformat()


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

 2fa-login
        # Step 1: current employee + correct password.
        if _is_current_employee_login(user, password):
            # Step 2: authenticator code, if this employee has 2FA enabled.
            if user.is_2fa_enabled:
                _clear_pending()
                session["pending_2fa_user_id"] = user.id
                session["pending_2fa_at"] = time.time()
                return redirect(url_for("auth.verify_2fa"))

            _complete_login(user)
            return redirect(url_for("auth.home"))

        # Record failed logins, including attempts by former employees.
        db.session.add(LoginLog(username=username,
                                ip_address=request.remote_addr, success=False))

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
            session["last_active"] = datetime.now(timezone.utc).isoformat()
            session.permanent = True  # Ensures PERMANENT_SESSION_LIFETIME applies
            flash(f"Logged in as {user.display_name or user.username}.", "success")
            return redirect(url_for("auth.home"))

        # Record failed logins for wrong passwords or unknown usernames
        log = LoginLog(username=username, ip_address=request.remote_addr, success=False)
        db.session.add(log)
        main
        db.session.commit()

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/login/verify", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def verify_2fa():
    if current_user.is_authenticated:
        return redirect(url_for("auth.home"))

    user_id = session.get("pending_2fa_user_id")
    started = session.get("pending_2fa_at", 0)
    if not user_id or time.time() - started > PENDING_TTL:
        _clear_pending()
        flash("Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    # Re-check employment: someone marked "left" between the two steps is rejected.
    if (not user or user.employment_status != "employed"
            or not user.is_2fa_enabled or not user.totp_secret):
        _clear_pending()
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            _clear_pending()
            _complete_login(user)
            return redirect(url_for("auth.home"))

        db.session.add(LoginLog(username=user.username,
                                ip_address=request.remote_addr, success=False))
        db.session.commit()

        tries = session.get("pending_2fa_tries", 0) + 1
        session["pending_2fa_tries"] = tries
        if tries >= MAX_2FA_TRIES:
            _clear_pending()
            flash("Too many incorrect codes. Please log in again.", "danger")
            return redirect(url_for("auth.login"))
        flash("Invalid code.", "danger")

    return render_template("verify_2fa.html")


@auth_bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", methods=["POST"])
def setup_2fa():
    if current_user.is_2fa_enabled:
        flash("Two-factor authentication is already enabled.", "success")
        return redirect(url_for("auth.home"))

    # The secret is stored but inactive until the user proves their app works.
    if not current_user.totp_secret:
        current_user.totp_secret = pyotp.random_base32()
        db.session.commit()
    secret = current_user.totp_secret

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            current_user.is_2fa_enabled = True
            db.session.commit()
            flash("Two-factor authentication enabled.", "success")
            return redirect(url_for("auth.home"))
        flash("Invalid code, try again.", "danger")

    uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.username, issuer_name="AstroLink")
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template("setup_2fa.html", qr_b64=qr_b64, secret=secret)


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
    _clear_pending()
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))