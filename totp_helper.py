"""
Helper for the pre-enrolled demo accounts.

    python totp_helper.py gen          # print new TOTP_SECRET_* lines for your .env
    python totp_helper.py now admin    # print the current 6-digit code for a user
"""
import os
import sys

import pyotp
from dotenv import load_dotenv

DEMO_USERS = ["admin", "jchen", "mkowalski", "intern22"]


def main():
    args = sys.argv[1:]

    if args == ["gen"]:
        print("# Paste these lines into your .env file (NOT .env.example, which is committed to Git):")
        for user in DEMO_USERS:
            print(f"TOTP_SECRET_{user.upper()}={pyotp.random_base32()}")

    elif len(args) == 2 and args[0] == "now":
        load_dotenv()
        secret = os.environ.get(f"TOTP_SECRET_{args[1].upper()}", "").strip()
        if not secret:
            sys.exit(f"No TOTP_SECRET_{args[1].upper()} found in .env")
        print(pyotp.TOTP(secret).now())

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
