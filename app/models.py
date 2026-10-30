"""
Database models.

What's here:
- User: login accounts with bcrypt password hashing
- Satellite: the AstroLink fleet (12 satellites)
- GroundStation: the 4 antenna sites that talk to the satellites
- TelemetryReading: health data the satellites send down (battery, temp, signal...)
- CommandLog: history of commands sent to satellites
- Subscriber: AstroLink's paying customers (contains personal info)
- LegacyAccessLog: login history from the OLD script server (before your tool)

What's NOT here (for you to build):
- Roles or permissions
- Anything that controls who can do what
- Logging of actions taken in YOUR tool
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(120))
    job_title = db.Column(db.String(50))  # display label only, NOT a permission
    employment_status = db.Column(db.String(20), default="employed")  # "employed" or "left"
    created_at = db.Column(db.DateTime, default=utcnow)

    # Only administrators can access sensitive management features.
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Satellite(db.Model):
    __tablename__ = "satellites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default="active")  # active, safe_mode, maintenance, launching, deorbiting
    orbit_altitude_km = db.Column(db.Float, default=550.0)
    coverage_region = db.Column(db.String(50))
    fuel_remaining_pct = db.Column(db.Float, default=100.0)
    firmware_version = db.Column(db.String(20), default="3.2.1")
    antenna_bearing_deg = db.Column(db.Float, default=0.0)
    power_mode = db.Column(db.String(20), default="normal")  # normal, low_power
    subscribers_served = db.Column(db.Integer, default=0)
    launched_at = db.Column(db.DateTime)


class GroundStation(db.Model):
    __tablename__ = "ground_stations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    location = db.Column(db.String(120))
    status = db.Column(db.String(20), default="online")  # online, degraded, offline
    ip_address = db.Column(db.String(45))


class TelemetryReading(db.Model):
    """Health data a satellite sends down to a ground station."""
    __tablename__ = "telemetry"

    id = db.Column(db.Integer, primary_key=True)
    satellite_id = db.Column(db.Integer, db.ForeignKey("satellites.id"), nullable=False)
    ground_station_id = db.Column(db.Integer, db.ForeignKey("ground_stations.id"))
    timestamp = db.Column(db.DateTime, default=utcnow)
    battery_pct = db.Column(db.Float)
    temperature_c = db.Column(db.Float)
    signal_dbm = db.Column(db.Float)
    altitude_km = db.Column(db.Float)

    satellite = db.relationship("Satellite", backref="telemetry")
    ground_station = db.relationship("GroundStation", backref="telemetry")


class CommandLog(db.Model):
    """
    History of commands sent to satellites.
    Look closely at: entries with no user (shared password era),
    intern22's AL-07 command, and tgarcia's commands after leaving.
    """
    __tablename__ = "command_log"

    id = db.Column(db.Integer, primary_key=True)
    satellite_id = db.Column(db.Integer, db.ForeignKey("satellites.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow)
    command_type = db.Column(db.String(50), nullable=False)
    parameter = db.Column(db.String(100))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="executed")
    ip_address = db.Column(db.String(45))

    satellite = db.relationship("Satellite", backref="commands")
    user = db.relationship("User", backref="commands")


class Subscriber(db.Model):
    """
    AstroLink's customers. This is personal information (PII):
    names, emails, home addresses. Right now it's stored in plain text.
    """
    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    home_address = db.Column(db.String(200))
    phone = db.Column(db.String(30))
    plan = db.Column(db.String(20))  # basic, standard, business
    satellite_id = db.Column(db.Integer, db.ForeignKey("satellites.id"))

    satellite = db.relationship("Satellite", backref="subscribers")


class LegacyAccessLog(db.Model):
    """
    Login history from AstroLink's OLD command server (the scripts
    they used before your tool). Useful for spotting suspicious
    patterns. The starter does NOT write to this table.
    """
    __tablename__ = "legacy_access_log"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    username = db.Column(db.String(80))  # "ops_shared" = the shared account
    ip_address = db.Column(db.String(45))
    success = db.Column(db.Boolean, nullable=False)

class LoginLog(db.Model):
    __tablename__ = "login_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(45))
    success = db.Column(db.Boolean, nullable=False)