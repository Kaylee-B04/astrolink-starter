"""
=====================================================================
  THIS IS ASTROLINK'S CURRENT SYSTEM. IT IS WHAT YOU ARE REPLACING.
=====================================================================

Every operator runs this script from a terminal to control satellites.
Read it and notice:

  - Everyone uses the SAME password (it's right there in the code)
  - It doesn't record WHO sent the command
  - Anyone with the password can send ANY command, including deorbit
  - There's no "are you sure?" and no second person checking
  - If you typo the satellite name, it just goes to the wrong satellite

That's how the intern hit AL-07 instead of AL-08, and how Taylor Garcia
kept sending commands from home after leaving the company.

Try it (from the project folder):

    docker compose exec web python legacy/send_command.py AL-02 ping
    docker compose exec web python legacy/send_command.py AL-02 antenna_point 90

It will ask for the shared password: astrolink2024
"""

import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import Satellite
from app.simulator import COMMANDS, execute_command

SHARED_PASSWORD = "astrolink2024"  # everyone on the ops team knows this


def main():
    if len(sys.argv) < 3:
        print("Usage: python legacy/send_command.py <SATELLITE> <COMMAND> [PARAMETER]")
        print("Commands:", ", ".join(COMMANDS))
        sys.exit(1)

    sat_name, command = sys.argv[1].upper(), sys.argv[2]
    parameter = sys.argv[3] if len(sys.argv) > 3 else None

    if getpass.getpass("Ops password: ") != SHARED_PASSWORD:
        print("Wrong password.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        sat = Satellite.query.filter_by(name=sat_name).first()
        if not sat:
            print(f"No satellite named {sat_name}")
            sys.exit(1)
        try:
            print(execute_command(sat, command, parameter))
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        # Notice: nothing is logged. Nobody will ever know who ran this.


if __name__ == "__main__":
    main()
