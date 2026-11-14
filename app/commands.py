from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import limiter
from app.models import db, Satellite, CommandLog
from app.simulator import COMMANDS, execute_command

commands_bp = Blueprint("commands", __name__)

# Which risk levels each role is allowed to send.
ALLOWED_RISKS = {
    "admin": {"low", "medium", "high", "critical"},
    "operator": {"low", "medium", "high"},
    "viewer": set(),
}

# Risk levels that require typing the satellite name to confirm.
CONFIRM_RISKS = {"high", "critical"}


def log_command(sat, command_type, parameter, status, description):
    """Record every command attempt: executed, failed, or blocked."""
    entry = CommandLog(
        satellite_id=sat.id,
        user_id=current_user.id,
        command_type=command_type,
        parameter=parameter or None,
        status=status,
        description=description,
        ip_address=request.remote_addr,
    )
    db.session.add(entry)
    db.session.commit()


@commands_bp.route("/commands", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute", methods=["POST"])
def send_command():
    allowed = ALLOWED_RISKS.get(current_user.role, set())

    if request.method == "POST":
        sat_id = request.form.get("satellite_id", type=int)
        command_type = request.form.get("command_type", "")
        parameter = request.form.get("parameter", "").strip()
        confirm_name = request.form.get("confirm_name", "").strip()

        sat = db.session.get(Satellite, sat_id) if sat_id else None
        if sat is None or command_type not in COMMANDS:
            flash("Pick a valid satellite and command.", "danger")
            return redirect(url_for("commands.send_command"))

        risk = COMMANDS[command_type]["risk"]

        # Check 1: is this role allowed to send this risk level?
        if risk not in allowed:
            log_command(sat, command_type, parameter, "blocked",
                        f"Role '{current_user.role}' cannot send {risk}-risk commands")
            flash(f"Blocked: your role can't send {risk}-risk commands. This attempt was logged.", "danger")
            return redirect(url_for("commands.send_command"))

        # Check 2: risky commands need the satellite name typed exactly.
        if risk in CONFIRM_RISKS and confirm_name != sat.name:
            log_command(sat, command_type, parameter, "blocked",
                        "Confirmation name did not match")
            flash(f"This is a {risk}-risk command. Type '{sat.name}' exactly to confirm.", "danger")
            return redirect(url_for("commands.send_command"))

        # All checks passed: send it.
        try:
            result = execute_command(sat, command_type, parameter)
        except ValueError as e:
            db.session.rollback()
            log_command(sat, command_type, parameter, "failed", str(e))
            flash(str(e), "danger")
            return redirect(url_for("commands.send_command"))

        log_command(sat, command_type, parameter, "executed", result)
        flash(result, "success")
        return redirect(url_for("commands.send_command"))

    satellites = Satellite.query.order_by(Satellite.name).all()
    return render_template("send_command.html", satellites=satellites,
                           commands=COMMANDS, allowed=allowed,
                           confirm_risks=CONFIRM_RISKS)


@commands_bp.route("/command-log")
@login_required
def command_log():
    if current_user.role not in ("admin", "operator"):
        abort(403)
    logs = CommandLog.query.order_by(CommandLog.timestamp.desc()).limit(200).all()
    return render_template("command_log.html", logs=logs)