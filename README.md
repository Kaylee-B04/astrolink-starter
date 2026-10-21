# AstroLink Starter

Starter repository for the WiCyS @ UCI Cyber Project Competition (Fall 2026).

AstroLink controls its 12 satellites with a script and one shared password. Your team builds a secure tool to solve their problems. What you build is up to you. Read [docs/CHALLENGE.md](docs/CHALLENGE.md) first.

You're free to use a different stack. This starter is here to save you setup time.

## Quick Start

You need Git and Docker Desktop installed (see the Cloud Security workshop materials). Full walkthrough: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

```bash
git clone <your-team-fork-url>
cd astrolink-starter
cp .env.example .env      # Windows: copy .env.example .env
docker compose up -d
docker compose exec web python seed.py
```

Then open http://localhost:8000 and log in as `admin` / `spaceadmin123`.

## What's Included

- **Flask + PostgreSQL + Docker**, set up and ready to go
- **Login / register / logout** with bcrypt password hashing
- **`show_data.py`**: prints what's in the database so you can see the data
- **Command simulator** (`app/simulator.py`): call one function, and the satellite responds. No security built in.
- **The legacy script** (`legacy/send_command.py`): AstroLink's current insecure system, and what you're replacing
- **Scenario data**: the intern incident, the former employee's commands, a brute-force attempt, fake telemetry, and customer PII in plain text

**Not included:** your tool. That part is yours.

## Test Accounts

| Username | Password | Who they are |
|---|---|---|
| `admin` | `spaceadmin123` | Head of Operations |
| `jchen` | `operator123` | Senior Operator |
| `mkowalski` | `operator123` | Operator |
| `intern22` | `intern12345` | Intern who sent a command to the wrong satellite |
| `tgarcia` | `operator123` | Former employee who still has access |

## Docs

| Document | What's in it |
|---|---|
| [docs/CHALLENGE.md](docs/CHALLENGE.md) | The brief and what's in this starter |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Running the app, adding pages, team Git workflow |

## Questions?

Ask in your team's Discord channel or tag a board officer in the CPC main channel.
