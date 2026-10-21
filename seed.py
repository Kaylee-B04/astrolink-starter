"""
Seed the database with AstroLink's data.

Run:  docker compose exec web python seed.py

WARNING: this wipes the database and reloads everything.
"""

import random
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import (
    User, Satellite, GroundStation, TelemetryReading,
    CommandLog, Subscriber, LegacyAccessLog,
)

random.seed(42)  # same data every time


def at(days_ago, hour, minute=0):
    """A timestamp `days_ago` days back, at a specific hour (UTC)."""
    base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return base - timedelta(days=days_ago) + timedelta(hours=hour, minutes=minute)


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---------------- USERS ----------------
        accounts = [
            # username, password, name, job title, employment status
            ("admin", "spaceadmin123", "Alex Rivera", "Head of Operations", "employed"),
            ("jchen", "operator123", "Jordan Chen", "Senior Operator", "employed"),
            ("mkowalski", "operator123", "Morgan Kowalski", "Operator", "employed"),
            ("intern22", "intern12345", "Casey Park", "Intern", "employed"),
            ("tgarcia", "operator123", "Taylor Garcia", "Operator", "left"),  # left 3 weeks ago
        ]
        users = {}
        for username, pw, name, title, status in accounts:
            u = User(username=username, display_name=name, job_title=title, employment_status=status)
            u.set_password(pw)
            db.session.add(u)
            users[username] = u

        # ---------------- GROUND STATIONS ----------------
        stations = [
            GroundStation(name="GS-IRV", location="Irvine, California", status="online", ip_address="10.0.2.10"),
            GroundStation(name="GS-SVB", location="Svalbard, Norway", status="online", ip_address="10.0.2.20"),
            GroundStation(name="GS-PUQ", location="Punta Arenas, Chile", status="degraded", ip_address="10.0.2.30"),
            GroundStation(name="GS-PER", location="Perth, Australia", status="online", ip_address="10.0.2.40"),
        ]
        db.session.add_all(stations)

        # ---------------- SATELLITES ----------------
        # Current state reflects everything that's happened, including tgarcia's changes.
        sat_rows = [
            # name, status, altitude, region, fuel, firmware, bearing, power, customers
            ("AL-01", "active", 550.0, "North America", 87.3, "3.0.0-rc1", 45.0, "normal", 2140),   # tgarcia pushed untested firmware
            ("AL-02", "active", 545.0, "North America", 91.2, "3.2.1", 60.0, "normal", 1980),
            ("AL-03", "active", 523.0, "Europe", 66.0, "3.2.1", 110.0, "normal", 1720),             # tgarcia lowered 25 km
            ("AL-04", "active", 552.0, "Europe", 84.1, "3.2.1", 95.0, "normal", 1650),
            ("AL-05", "active", 547.0, "Asia Pacific", 92.0, "3.2.1", 200.0, "low_power", 2310),    # tgarcia set low power
            ("AL-06", "maintenance", 551.0, "Asia Pacific", 65.3, "3.1.0", 210.0, "normal", 0),
            ("AL-07", "safe_mode", 535.0, "South America", 45.2, "3.2.1", 280.0, "normal", 0),      # intern incident
            ("AL-08", "active", 549.0, "South America", 88.7, "3.2.1", 312.7, "normal", 1430),      # tgarcia redirected antenna
            ("AL-09", "active", 553.0, "Africa / Middle East", 95.1, "3.2.1", 150.0, "normal", 1205),
            ("AL-10", "launching", 0.0, "Unassigned", 100.0, "3.2.1", 0.0, "normal", 0),
            ("AL-11", "deorbiting", 320.0, "Decommissioned", 12.4, "3.1.0", 0.0, "normal", 0),
            ("AL-12", "active", 546.0, "Oceania", 89.9, "3.2.0", 170.0, "normal", 990),
        ]
        sats = {}
        for name, status, alt, region, fuel, fw, bearing, power, cust in sat_rows:
            s = Satellite(
                name=name, status=status, orbit_altitude_km=alt, coverage_region=region,
                fuel_remaining_pct=fuel, firmware_version=fw, antenna_bearing_deg=bearing,
                power_mode=power, subscribers_served=cust, launched_at=at(400, 12),
            )
            db.session.add(s)
            sats[name] = s

        db.session.flush()

        # ---------------- TELEMETRY (last 24 hours, every 2 hours) ----------------
        station_for = {
            "North America": stations[0], "Europe": stations[1], "South America": stations[2],
            "Asia Pacific": stations[3], "Oceania": stations[3], "Africa / Middle East": stations[1],
        }
        telemetry_count = 0
        for s in sats.values():
            if s.status in ("launching", "deorbiting"):
                continue
            for h in range(0, 24, 2):
                battery = 82 + random.uniform(-6, 6)
                if s.name == "AL-07":
                    battery = 31 + random.uniform(-3, 3)  # still recovering from the incident
                if s.name == "AL-05":
                    battery = 95 + random.uniform(-2, 2)
                db.session.add(TelemetryReading(
                    satellite_id=s.id,
                    ground_station_id=station_for[s.coverage_region].id,
                    timestamp=at(0, h) - timedelta(hours=24),
                    battery_pct=round(battery, 1),
                    temperature_c=round(random.uniform(-10, 25), 1),
                    signal_dbm=round(random.uniform(-95, -75), 1),
                    altitude_km=round(s.orbit_altitude_km + random.uniform(-0.3, 0.3), 2),
                ))
                telemetry_count += 1

        # Readings that DIDN'T come from any ground station, with impossible values.
        # Someone may be injecting fake telemetry.
        for h, temp, batt in [(3, 412.0, 140.0), (5, -260.0, 0.0)]:
            db.session.add(TelemetryReading(
                satellite_id=sats["AL-09"].id, ground_station_id=None,
                timestamp=at(1, h), battery_pct=batt, temperature_c=temp,
                signal_dbm=-20.0, altitude_km=0.0,
            ))
            telemetry_count += 1

        # ---------------- COMMAND HISTORY ----------------
        commands = [
            # (satellite, user or None, timestamp, type, parameter, description, status, ip)

            # Shared-password era: nobody knows who sent these
            ("AL-01", None, at(90, 14), "firmware_update", "3.2.1", "Updated AL-01 firmware 3.1.0 -> 3.2.1", "executed", "10.0.1.50"),
            ("AL-02", None, at(88, 10), "orbit_adjust", "3", "Orbit +3 km on AL-02", "executed", "10.0.1.50"),
            ("AL-03", None, at(85, 16), "antenna_point", "110", "Antenna realignment AL-03", "executed", "10.0.1.50"),
            ("AL-11", None, at(60, 11), "deorbit", None, "Deorbit AL-11 (end of life)", "executed", "10.0.1.50"),

            # Normal operations
            ("AL-04", "jchen", at(30, 15), "firmware_update", "3.2.1", "Updated AL-04 firmware to 3.2.1", "executed", "10.0.1.101"),
            ("AL-06", "mkowalski", at(25, 9), "power_mode", "low_power", "AL-06 low power for eclipse", "executed", "10.0.1.102"),

            # THE INTERN INCIDENT: meant AL-08, typed AL-07
            ("AL-07", "intern22", at(14, 13, 22), "orbit_adjust", "-15", "Orbit -15 km on AL-07 (was supposed to be AL-08)", "executed", "10.0.1.200"),
            ("AL-07", "jchen", at(14, 13, 41), "orbit_adjust", "0", "EMERGENCY: attempted revert on AL-07", "failed", "10.0.1.101"),
            ("AL-07", "admin", at(14, 13, 55), "safe_mode", None, "AL-07 in safe mode pending investigation", "executed", "10.0.1.100"),

            # FORMER EMPLOYEE: tgarcia left 21 days ago. These are after, late at night, from home.
            ("AL-01", "tgarcia", at(5, 2, 14), "firmware_update", "3.0.0-rc1", "Pushed firmware 3.0.0-rc1 (untested build)", "executed", "192.168.1.42"),
            ("AL-03", "tgarcia", at(4, 3, 2), "orbit_adjust", "-25", "Lowered AL-03 orbit by 25 km", "executed", "192.168.1.42"),
            ("AL-05", "tgarcia", at(2, 1, 47), "power_mode", "low_power", "Switched AL-05 to low power", "executed", "192.168.1.42"),
            ("AL-08", "tgarcia", at(1, 3, 30), "antenna_point", "312.7", "Redirected AL-08 antenna to 312.7 deg", "executed", "192.168.1.42"),

            # Recent normal operations
            ("AL-09", "jchen", at(1, 15), "antenna_point", "150", "Optimized AL-09 antenna", "executed", "10.0.1.101"),
            ("AL-12", "mkowalski", at(0, 10), "firmware_update", "3.2.1", "Scheduled firmware update AL-12", "pending", "10.0.1.102"),
        ]
        for sat, user, ts, ctype, param, desc, status, ip in commands:
            db.session.add(CommandLog(
                satellite_id=sats[sat].id, user_id=users[user].id if user else None,
                timestamp=ts, command_type=ctype, parameter=param,
                description=desc, status=status, ip_address=ip,
            ))

        # ---------------- SUBSCRIBERS (fictional people) ----------------
        first = ["Maria", "James", "Aisha", "Wei", "Elena", "Kofi", "Priya", "Lucas", "Sofia", "Daniel",
                 "Amara", "Noah", "Yuki", "Omar", "Grace", "Mateo", "Leila", "Ethan", "Zara", "Ravi"]
        last = ["Santos", "Okafor", "Lindqvist", "Tanaka", "Moreau", "Mensah", "Iyer", "Fischer", "Rossi", "Kim",
                "Abara", "Walsh", "Sato", "Haddad", "Byrne", "Vargas", "Nasser", "Cole", "Ahmed", "Patel"]
        streets = ["Ridge Rd", "Valley Way", "Harbor St", "Pine Ln", "Mesa Dr"]
        active_sats = [s for s in sats.values() if s.subscribers_served > 0]
        for i in range(40):
            f, l = first[i % 20], last[(i * 7) % 20]
            db.session.add(Subscriber(
                full_name=f"{f} {l}",
                email=f"{f.lower()}.{l.lower()}{i}@example.com",
                home_address=f"{100 + i * 13} {streets[i % 5]}, Remote Township",
                phone=f"555-01{i:02d}",
                plan=["basic", "standard", "business"][i % 3],
                satellite_id=active_sats[i % len(active_sats)].id,
            ))

        # ---------------- LEGACY ACCESS LOG (old script server) ----------------
        access = []
        # Months of shared-account logins during work hours
        for d in range(90, 30, -3):
            access.append((at(d, random.randint(9, 17), random.randint(0, 59)), "ops_shared", "10.0.1.50", True))
        # Individual accounts introduced ~30 days ago
        for d in range(30, 0, -1):
            for name, ip in [("jchen", "10.0.1.101"), ("mkowalski", "10.0.1.102")]:
                if random.random() < 0.6:
                    access.append((at(d, random.randint(8, 18), random.randint(0, 59)), name, ip, True))
        for d in (16, 15, 14):
            access.append((at(d, 13, 5), "intern22", "10.0.1.200", True))
        # tgarcia: normal work logins before leaving...
        for d in range(30, 21, -2):
            access.append((at(d, 10, 15), "tgarcia", "10.0.1.103", True))
        # ...then logins from home, in the middle of the night, after leaving
        for d, h, m in [(5, 2, 10), (4, 2, 58), (2, 1, 44), (1, 3, 27)]:
            access.append((at(d, h, m), "tgarcia", "192.168.1.42", True))
        # Brute-force attempt on the admin account from an unknown IP, 3 days ago
        for i in range(28):
            access.append((at(3, 4, 0) + timedelta(seconds=i * 20), "admin", "203.0.113.77", False))
        # A few normal typos
        access.append((at(12, 9, 1), "mkowalski", "10.0.1.102", False))
        access.append((at(7, 14, 30), "jchen", "10.0.1.101", False))

        for ts, name, ip, ok in access:
            db.session.add(LegacyAccessLog(timestamp=ts, username=name, ip_address=ip, success=ok))

        db.session.commit()

        print("Database seeded!\n")
        print("Accounts:")
        for username, pw, name, title, status in accounts:
            note = "  <- LEFT THE COMPANY, still has access" if status == "left" else ""
            print(f"  {username:<10} / {pw:<14} {title}{note}")
        print(f"\n  {len(sats)} satellites, {len(stations)} ground stations, {telemetry_count} telemetry readings")
        print(f"  {len(commands)} commands, 40 subscribers, {len(access)} legacy access log entries")
        print("\nOpen http://localhost:8000 and log in.")


if __name__ == "__main__":
    seed()
