"""
Satellite command simulator.

You don't need to know anything about satellites to use this.
Call execute_command() and it updates the satellite in the database
the way a real satellite would respond.

    from app.simulator import COMMANDS, execute_command

    result = execute_command(satellite, "orbit_adjust", "-15")
    # result -> "AL-07 altitude changed 550.0 km -> 535.0 km"

IMPORTANT: this function does NO security checks. It doesn't check
who is sending the command, doesn't ask for approval, and doesn't
write to the command log. Adding those is YOUR job.
"""

from app.models import db

# Every command an operator can send.
# "risk" is how bad it is if this command is sent by mistake or by an attacker.
COMMANDS = {
    "ping": {
        "label": "Ping",
        "risk": "low",
        "parameter": None,
        "what_it_does": "Checks the satellite is responding. Changes nothing.",
    },
    "antenna_point": {
        "label": "Point antenna",
        "risk": "medium",
        "parameter": "bearing in degrees, 0-360 (e.g. 120)",
        "what_it_does": "Aims the satellite's antenna. Wrong bearing = customers in that region lose internet.",
    },
    "power_mode": {
        "label": "Set power mode",
        "risk": "medium",
        "parameter": "normal or low_power",
        "what_it_does": "Low power saves battery but cuts bandwidth for every customer on that satellite.",
    },
    "orbit_adjust": {
        "label": "Adjust orbit",
        "risk": "high",
        "parameter": "change in km, -30 to 30 (e.g. -15)",
        "what_it_does": "Fires thrusters to move the satellite up or down. Burns fuel that can never be refilled. Too low = burns up in the atmosphere.",
    },
    "firmware_update": {
        "label": "Update firmware",
        "risk": "high",
        "parameter": "version (e.g. 3.2.2)",
        "what_it_does": "Installs new software on the satellite. A bad build can brick it permanently.",
    },
    "safe_mode": {
        "label": "Enter safe mode",
        "risk": "medium",
        "parameter": None,
        "what_it_does": "Shuts down everything except the essentials. All customers on this satellite go offline.",
    },
    "resume": {
        "label": "Resume normal operation",
        "risk": "low",
        "parameter": None,
        "what_it_does": "Brings a satellite out of safe mode.",
    },
    "deorbit": {
        "label": "Deorbit",
        "risk": "critical",
        "parameter": None,
        "what_it_does": "Permanently lowers the satellite until it burns up. CANNOT be undone. A satellite costs ~$500k.",
    },
}

MIN_SAFE_ALTITUDE_KM = 400.0


def execute_command(satellite, command_type, parameter=None):
    """
    Apply a command to a satellite and save the change.
    Returns a human-readable result string.
    Raises ValueError if the command or parameter is invalid.
    """
    if command_type not in COMMANDS:
        raise ValueError(f"Unknown command: {command_type}")

    if satellite.status == "deorbiting":
        raise ValueError(f"{satellite.name} is deorbiting and no longer accepts commands")

    p = (parameter or "").strip()
    name = satellite.name

    if command_type == "ping":
        result = f"{name} responded: status={satellite.status}, altitude={satellite.orbit_altitude_km} km"

    elif command_type == "antenna_point":
        bearing = _number(p, 0, 360, "Bearing")
        old = satellite.antenna_bearing_deg
        satellite.antenna_bearing_deg = bearing
        result = f"{name} antenna moved {old} deg -> {bearing} deg"

    elif command_type == "power_mode":
        if p not in ("normal", "low_power"):
            raise ValueError("Power mode must be 'normal' or 'low_power'")
        satellite.power_mode = p
        result = f"{name} power mode set to {p}"

    elif command_type == "orbit_adjust":
        delta = _number(p, -30, 30, "Orbit change")
        fuel_cost = abs(delta) * 0.5
        if satellite.fuel_remaining_pct < fuel_cost:
            raise ValueError(f"{name} doesn't have enough fuel for this burn")
        old = satellite.orbit_altitude_km
        satellite.orbit_altitude_km = round(old + delta, 1)
        satellite.fuel_remaining_pct = round(satellite.fuel_remaining_pct - fuel_cost, 1)
        result = f"{name} altitude changed {old} km -> {satellite.orbit_altitude_km} km"
        if satellite.orbit_altitude_km < MIN_SAFE_ALTITUDE_KM:
            result += " -- WARNING: below safe altitude"

    elif command_type == "firmware_update":
        if not p:
            raise ValueError("Firmware version is required")
        old = satellite.firmware_version
        satellite.firmware_version = p
        result = f"{name} firmware {old} -> {p}"

    elif command_type == "safe_mode":
        satellite.status = "safe_mode"
        result = f"{name} entered safe mode. {satellite.subscribers_served} customers offline."

    elif command_type == "resume":
        satellite.status = "active"
        result = f"{name} resumed normal operation"

    elif command_type == "deorbit":
        satellite.status = "deorbiting"
        satellite.subscribers_served = 0
        result = f"{name} deorbit started. This cannot be reversed."

    db.session.commit()
    return result


def _number(value, low, high, label):
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number")
    if not low <= n <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return n
