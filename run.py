"""
Run AstroLink locally WITHOUT Docker (SQLite database, in-memory rate limiting).

    python run_local.py

Reads SECRET_KEY from your .env file. Keep DATABASE_URL OUT of your local .env:
that line points at the Docker Postgres container and would break a local run.
"""
import os

from dotenv import load_dotenv

load_dotenv()   # loads SECRET_KEY (and anything else) from .env
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)