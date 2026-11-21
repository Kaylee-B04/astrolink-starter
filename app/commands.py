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
    """Record every command attempt: executed, failed, blocked, pending, or rejected."""
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

        # Check 3 (Option A): require admin approval for operator orbit_adjust requests
        if command_type == "orbit_adjust" and current_user.role != "admin":
            log_command(
                sat,
                command_type,
                parameter,
                "pending",
                f"Awaiting admin approval ({parameter} km adjustment on {sat.name})",
            )
            flash(
                f"Orbit adjustment for {sat.name} queued for administrator approval.",
                "warning",
            )
            return redirect(url_for("commands.send_command"))

        # All checks passed: execute immediately.
        try:
            result = execute_command(sat, command_type, parameter)
            log_command(sat, command_type, parameter, "executed", result)
            flash(result, "success")
        except ValueError as e:
            db.session.rollback()
            log_command(sat, command_type, parameter, "failed", str(e))
            flash(str(e), "danger")
        except Exception:
            db.session.rollback()
            log_command(sat, command_type, parameter, "failed", "Internal execution error")
            flash("Command execution failed due to a system error.", "danger")

        return redirect(url_for("commands.send_command"))

    satellites = Satellite.query.order_by(Satellite.name).all()
    return render_template("send_command.html", satellites=satellites,
                           commands=COMMANDS, allowed=allowed,
                           confirm_risks=CONFIRM_RISKS)


@commands_bp.route("/command-log/<int:log_id>/approve", methods=["GET", "POST"])
@login_required
def approve_command(log_id):
    if current_user.role != "admin":
        abort(403)

    entry = db.session.get(CommandLog, log_id)
    if entry is None:
        abort(404)

    # Prevent self-approval of pending requests
    if entry.user_id == current_user.id:
        flash("You cannot approve your own pending command.", "danger")
        return redirect(url_for("commands.command_log"))

    if entry.status != "pending":
        flash("This command has already been processed.", "warning")
        return redirect(url_for("commands.command_log"))

    sat = entry.satellite

    # GET: Render the confirmation page with projected orbital telemetry
    if request.method == "GET":
        projected_altitude = None
        fuel_cost = None
        if entry.command_type == "orbit_adjust" and entry.parameter:
            try:
                delta = float(entry.parameter)
                projected_altitude = round(sat.orbit_altitude_km + delta, 1)
                fuel_cost = round(abs(delta) * 0.5, 1)
            except ValueError:
                pass

        return render_template(
            "confirm_approve.html",
            entry=entry,
            sat=sat,
            projected_altitude=projected_altitude,
            fuel_cost=fuel_cost,
        )

    # POST: Admin confirmed — execute the command
    try:
        result = execute_command(sat, entry.command_type, entry.parameter)
        entry.status = "executed"
        entry.description = f"{result} (Approved by {current_user.username})"
        db.session.commit()
        flash(f"Approved & executed: {result}", "success")
    except ValueError as e:
        db.session.rollback()
        entry.status = "failed"
        entry.description = f"Approval failed: {e} (Reviewed by {current_user.username})"
        db.session.commit()
        flash(f"Cannot execute pending command: {e}", "danger")

    return redirect(url_for("commands.command_log"))


@commands_bp.route("/command-log/<int:log_id>/reject", methods=["POST"])
@login_required
def reject_command(log_id):
    if current_user.role != "admin":
        abort(403)

    entry = db.session.get(CommandLog, log_id)
    if entry is None:
        abort(404)

    if entry.status != "pending":
        flash("This command has already been processed.", "warning")
        return redirect(url_for("commands.command_log"))

    entry.status = "rejected"
    entry.description = f"Rejected by admin {current_user.username}"
    db.session.commit()
    flash(f"Rejected command #{entry.id} for {entry.satellite.name}.", "info")
    return redirect(url_for("commands.command_log"))