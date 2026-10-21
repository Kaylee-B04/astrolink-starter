"""
Print what's in the database, so you can see the data you're working with.

    docker compose exec web python show_data.py              # everything
    docker compose exec web python show_data.py commands     # one table

Tables: users, satellites, stations, telemetry, commands, subscribers, access
"""

import sys
from app import create_app
from app.models import (
    User, Satellite, GroundStation, TelemetryReading,
    CommandLog, Subscriber, LegacyAccessLog,
)


def fmt(ts):
    return ts.strftime("%Y-%m-%d %H:%M")


def users():
    print("USERS")
    for u in User.query.order_by(User.id):
        print(f"  {u.username:<10} {u.display_name:<17} {u.job_title:<20} {u.employment_status}")


def satellites():
    print("SATELLITES")
    for s in Satellite.query.order_by(Satellite.name):
        print(f"  {s.name}  {s.status:<11} {s.orbit_altitude_km:>6} km  fuel {s.fuel_remaining_pct:>5}%  "
              f"fw {s.firmware_version:<10} antenna {s.antenna_bearing_deg:>5}  {s.power_mode:<9} "
              f"{s.subscribers_served:>5} customers  {s.coverage_region}")


def stations():
    print("GROUND STATIONS")
    for g in GroundStation.query.order_by(GroundStation.name):
        print(f"  {g.name}  {g.status:<9} {g.ip_address:<12} {g.location}")


def telemetry():
    print("TELEMETRY (newest 20)")
    for t in TelemetryReading.query.order_by(TelemetryReading.timestamp.desc()).limit(20):
        gs = t.ground_station.name if t.ground_station else "NONE"
        print(f"  {fmt(t.timestamp)}  {t.satellite.name}  via {gs:<6} battery {t.battery_pct:>5}%  "
              f"temp {t.temperature_c:>6} C  signal {t.signal_dbm} dBm  alt {t.altitude_km} km")
    bad = TelemetryReading.query.filter_by(ground_station_id=None).count()
    print(f"  ... {TelemetryReading.query.count()} readings total, {bad} with no ground station")


def commands():
    print("COMMAND LOG")
    for c in CommandLog.query.order_by(CommandLog.timestamp):
        who = c.user.username if c.user else "UNKNOWN"
        print(f"  {fmt(c.timestamp)}  {c.satellite.name}  {who:<10} {c.ip_address:<13} "
              f"{c.command_type:<16} {c.status:<9} {c.description}")


def subscribers():
    print("SUBSCRIBERS (first 10, stored in plain text)")
    for s in Subscriber.query.order_by(Subscriber.id).limit(10):
        print(f"  {s.full_name:<16} {s.email:<30} {s.phone}  {s.home_address}")
    print(f"  ... {Subscriber.query.count()} total")


def access():
    print("LEGACY ACCESS LOG (newest 40, from the old script server)")
    for a in LegacyAccessLog.query.order_by(LegacyAccessLog.timestamp.desc()).limit(40):
        print(f"  {fmt(a.timestamp)}  {a.username:<10} {a.ip_address:<14} {'ok' if a.success else 'FAILED'}")
    print(f"  ... {LegacyAccessLog.query.count()} total")


TABLES = {
    "users": users, "satellites": satellites, "stations": stations, "telemetry": telemetry,
    "commands": commands, "subscribers": subscribers, "access": access,
}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(TABLES)
    with create_app().app_context():
        for name in wanted:
            if name not in TABLES:
                print(f"Unknown table '{name}'. Options: {', '.join(TABLES)}")
                sys.exit(1)
            TABLES[name]()
            print()
