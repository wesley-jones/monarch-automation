#!/usr/bin/env python3
"""
login.py — Interactive login helper for Monarch Money.

Run this once to create session.json. The token can last several months.
Re-run if over_budget_report.py reports a session expired error.

Usage:
    python login.py
    python login.py --session /path/to/custom_session.json
"""

import argparse
import asyncio
import json
import os
import sys

try:
    from monarchmoney import MonarchMoney
except ImportError:
    print("ERROR: monarchmoney is not installed.")
    print("       Run: pip install -r requirements.txt")
    sys.exit(1)

DEFAULT_SESSION_FILE = "session.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Log into Monarch Money and save token to session.json"
    )
    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION_FILE,
        help=f"Path to write session token (default: {DEFAULT_SESSION_FILE})",
    )
    return parser.parse_args()


async def do_login(session_path: str):
    mm = MonarchMoney()

    print("Starting interactive Monarch Money login...")
    print("You will be prompted for your email, password, and MFA code if enabled.")
    print()

    await mm.interactive_login()

    # Extract the token — try public property first, fall back to private attribute
    token = None
    if hasattr(mm, "token"):
        token = mm.token
    elif hasattr(mm, "_token"):
        token = mm._token

    if not token:
        print()
        print("ERROR: Login appeared to succeed but no token was returned.")
        print("       This may indicate an API change in the monarchmoney library.")
        print("       Check: https://github.com/hammem/monarchmoney")
        sys.exit(1)

    session_data = {"token": token}
    with open(session_path, "w") as f:
        json.dump(session_data, f, indent=2)

    print()
    print(f"Login successful.")
    print(f"Session token saved to: {os.path.abspath(session_path)}")
    print()
    print("Token typically lasts several months.")
    print("Re-run login.py if the report fails with a session expired error.")


def main():
    args = parse_args()
    asyncio.run(do_login(args.session))


if __name__ == "__main__":
    main()
