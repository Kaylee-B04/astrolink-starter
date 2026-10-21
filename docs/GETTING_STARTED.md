# Getting Started

This guide gets the app running on your computer. Every team member should do this on their own laptop.

**Before you start:** have Git and Docker Desktop installed (covered in the Cloud Security workshop materials), and make sure Docker Desktop is open.

**Which terminal to use:**
- **Windows:** PowerShell (search "PowerShell" in the Start menu)
- **Mac:** Terminal (`Cmd + Space`, type "Terminal")
- **Linux:** your usual terminal

All commands below work the same on every system unless a step shows separate versions.

---

## Part 1: Get your team's copy of the code (~5 minutes)

**One person on your team does this:**

1. Go to the starter repo on GitHub and click **Fork** (top right) → **Create fork**. This makes your team's own copy.
2. On your fork, go to **Settings → Collaborators → Add people**, and add each teammate's GitHub username.

**Everyone then does this:**

1. Accept the collaborator invite (check your email or github.com/notifications).
2. On your team's fork, click the green **Code** button and copy the HTTPS URL.
3. In your terminal:

```bash
cd Desktop                        # or wherever you keep projects
git clone PASTE-THE-URL-HERE
cd astrolink-starter
```

---

## Part 2: Run the app (~5 minutes)

Make sure Docker Desktop is open, then run these from inside the `astrolink-starter` folder:

```bash
# 1. Create your settings file (copies the example)
#    Windows:      copy .env.example .env
#    Mac / Linux:  cp .env.example .env

# 2. Start the app and database (first time takes a few minutes to download)
docker compose up -d

# 3. Load AstroLink's data
docker compose exec web python seed.py
```

4. Open **http://localhost:8000** in your browser and log in as `admin` / `spaceadmin123`.

You should see "Logged in as Alex Rivera." It works.

**To stop the app:** `docker compose down`. **To start it again later:** `docker compose up -d`. Your data stays.

---

### No Docker yet? Run it with Python instead

You need Python 3.10 or newer (check with `python --version`, or `python3 --version` on Mac). From inside the `astrolink-starter` folder:

**Windows (PowerShell):**
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python run.py
```

**Mac:**
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py
python run.py
```

Open **http://localhost:8000**. Press `Ctrl + C` in the terminal to stop it. Next time, just activate the environment (2nd line) and run `python run.py`.

This uses a simple built-in database (SQLite) instead of PostgreSQL. Everything works the same while you build. Switch to Docker once you've installed it.

---

## Part 3: Look around

**See what's in the database:**

```bash
docker compose exec web python show_data.py               # everything
docker compose exec web python show_data.py commands      # just one table
```

Tables: `users`, `satellites`, `stations`, `telemetry`, `commands`, `subscribers`, `access`.

**Try AstroLink's current system** (the insecure script you're replacing). The password is `astrolink2024`:

```bash
docker compose exec web python legacy/send_command.py AL-02 ping
```

**Test accounts:**

| Username | Password | Who they are |
|---|---|---|
| `admin` | `spaceadmin123` | Head of Operations |
| `jchen` | `operator123` | Senior Operator |
| `mkowalski` | `operator123` | Operator |
| `intern22` | `intern12345` | Intern who sent a command to the wrong satellite |
| `tgarcia` | `operator123` | Former employee who still has access |

---

## Project Structure

```
astrolink-starter/
├── app/
│   ├── __init__.py          # App setup: register your pages here
│   ├── auth.py              # Login/register/logout (provided)
│   ├── simulator.py         # Sends commands to satellites (no security)
│   ├── models.py            # All database tables
│   ├── templates/           # HTML pages (base.html = shared layout)
│   └── static/css/style.css # Styling
├── legacy/
│   └── send_command.py      # The old insecure script you're replacing
├── docs/
│   ├── CHALLENGE.md         # The brief
│   └── GETTING_STARTED.md   # This file
├── seed.py                  # Wipes + reloads the database
├── show_data.py             # Prints what's in the database
├── run.py                   # Starts the app
├── Dockerfile               # How Docker builds the app (you don't need to edit)
├── docker-compose.yml       # Runs the app + database together (you don't need to edit)
├── requirements.txt         # Python packages
└── .env.example             # Example settings
```

## What's in the Database

| Table | What it is |
|---|---|
| `users` | 5 accounts. `job_title` is just a label, not a permission. `employment_status` is `"left"` for tgarcia. |
| `satellites` | 12 satellites and their current state |
| `ground_stations` | 4 antenna sites |
| `telemetry` | Health readings from the last 24 hours |
| `command_log` | 15 past commands, including the incidents |
| `subscribers` | 40 customers with personal info |
| `legacy_access_log` | Login history from the old script server |

---

## Sending a Command from Your Code

The simulator handles the satellite side. You handle everything around it.

```python
from app.models import Satellite
from app.simulator import COMMANDS, execute_command

sat = Satellite.query.filter_by(name="AL-02").first()

try:
    result = execute_command(sat, "antenna_point", "90")
    # result -> "AL-02 antenna moved 60.0 deg -> 90.0 deg"
except ValueError as e:
    # bad parameter, unknown command, satellite deorbiting, etc.
    print(e)

COMMANDS["deorbit"]["risk"]   # -> "critical"
```

---

## How to Add a Page

Example: a page that lists every ground station.

### Step 1: Create a new file `app/stations.py`

```python
from flask import Blueprint, render_template
from flask_login import login_required
from app.models import GroundStation

stations_bp = Blueprint("stations", __name__)

@stations_bp.route("/stations")
@login_required
def list_stations():
    stations = GroundStation.query.order_by(GroundStation.name).all()
    return render_template("stations.html", stations=stations)
```

### Step 2: Register it in `app/__init__.py`

Add these two lines where it says "Your routes go here":

```python
from app.stations import stations_bp
app.register_blueprint(stations_bp)
```

### Step 3: Create the page `app/templates/stations.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="page-header"><h1>Ground Stations</h1></div>
<section class="panel">
  <table>
    <tr><th>Name</th><th>Location</th><th>Readings received</th></tr>
    {% for g in stations %}
    <tr><td>{{ g.name }}</td><td>{{ g.location }}</td><td>{{ g.telemetry|length }}</td></tr>
    {% endfor %}
  </table>
</section>
{% endblock %}
```

To add it to the top menu, add a link in `app/templates/base.html` where it says "Add links to your own pages here":

```html
<a href="/stations">Stations</a>
```

### Step 4: Open it

Save your files. The app reloads automatically. Go to **http://localhost:8000/stations**.

If you see an error, run `docker compose logs web` to see what went wrong.

---

## Changing the Database

Need a new column, like a role for each user? Add it in `app/models.py`:

```python
class User(UserMixin, db.Model):
    ...
    role = db.Column(db.String(20), default="viewer")
```

Then reload the database. This wipes and rebuilds every table:

```bash
docker compose exec web python seed.py
```

To give the test accounts roles, update the accounts in `seed.py` too.

---

## Working as a Team with Git

```bash
git pull                          # get your teammates' latest changes (do this first!)
git add .                         # stage your changes
git commit -m "Add stations page" # save them with a message
git push                          # upload to your team's fork
```

Commit often. Judges look at commit history to see that everyone contributed.

---

## Useful Commands

| Command | What it does |
|---|---|
| `docker compose up -d` | Start the app |
| `docker compose down` | Stop the app |
| `docker compose exec web python seed.py` | Reset and reload all data |
| `docker compose exec web python show_data.py` | Print the database |
| `docker compose logs web` | See errors and app output |
| `docker compose up -d --build` | Rebuild after changing `requirements.txt` |
| `docker compose down -v` | Stop and **delete** the database completely |

## Common Issues

**"Cannot connect to the Docker daemon"**: Docker Desktop isn't open. Open it and wait for it to finish starting.

**"docker-compose: command not found"**: use `docker compose` (with a space). That's the current version.

**Page won't load at localhost:8000**: run `docker compose ps`. If `web` isn't "running," run `docker compose logs web` to see why.

**"Port 8000 already in use"**: in `docker-compose.yml`, change `"8000:8000"` to `"8001:8000"` and use http://localhost:8001.

**Error about a table or column after changing models**: run `docker compose exec web python seed.py`.

**Installed a new Python package**: add it to `requirements.txt`, then `docker compose up -d --build`.

**Windows: "running scripts is disabled on this system"** (when activating venv): run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, type `Y`, then try `venv\Scripts\activate` again.

**Windows: "docker is not recognized"**: Docker Desktop isn't installed or isn't open. Open it, wait for it to finish starting, then open a new PowerShell window.
