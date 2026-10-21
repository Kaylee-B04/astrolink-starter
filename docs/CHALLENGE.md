# AstroLink Challenge

## The Brief

Your team has been hired by **AstroLink**, a satellite communications startup that provides internet to remote areas through low-earth orbit satellites.

Right now they have:

- No centralized system for managing operations
- Commands sent through scripts with shared passwords
- No record of who did what or when
- An intern who accidentally repositioned the wrong satellite
- A former employee who still had access weeks after leaving

Ground stations are high-value targets. Unauthorized access could mean interrupted service for thousands of users, corrupted telemetry data, or worse.

**Your job: design and build a secure tool that solves their security problems.** What you build is up to your team.

## What's in This Starter

- **Login, register, and logout** already working (Flask + PostgreSQL + Docker)
- **AstroLink's data**: users, 12 satellites, ground stations, telemetry, command history, customers, and old login records. The intern incident and the former employee's activity are in there. Run `python show_data.py` to see it all.
- **`legacy/send_command.py`**: the script AstroLink uses today, with its shared password. This is what you're replacing.
- **`app/simulator.py`**: send a command to a satellite with one function call. You don't need to know anything about satellites.

See `GETTING_STARTED.md` for setup. You're free to use a different stack.

## Judging

1. Does it work? Live demo.
2. Can you explain why you designed it this way?
3. Can someone get around your security?
4. Can every team member walk a judge through it?

**AI tools** are allowed, but you must be able to defend every security decision.

## Quick Glossary

| Term | Meaning |
|---|---|
| Ground station | An antenna site on Earth that talks to the satellites |
| Command | An instruction sent to a satellite (move it, point its antenna, update its software) |
| Telemetry | Health data a satellite sends back (battery, temperature, signal) |
| Firmware | The satellite's software |
| Safe mode | The satellite shuts down everything except the essentials |
| Deorbit | Bringing a satellite down permanently |
