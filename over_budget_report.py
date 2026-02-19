#!/usr/bin/env python3
"""
over_budget_report.py — Monarch Money over-budget category report.

Finds budget categories where actual spending exceeds planned by a threshold.

Usage:
    python over_budget_report.py
    python over_budget_report.py --threshold 100
    python over_budget_report.py --json
    python over_budget_report.py --debug
    python over_budget_report.py --session /custom/path/session.json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime

try:
    from monarchmoney import MonarchMoney
except ImportError:
    if "--json" in sys.argv:
        print(json.dumps({"error": "monarchmoney not installed. Run: pip install -r requirements.txt",
                          "code": "DEPENDENCY_MISSING"}))
    else:
        print("ERROR: monarchmoney is not installed.")
        print("       Run: pip install -r requirements.txt")
    sys.exit(1)

DEFAULT_SESSION_FILE = "session.json"
DEFAULT_THRESHOLD = 50.0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Report Monarch Money budget categories over a spending threshold"
    )
    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION_FILE,
        help=f"Path to session.json (default: {DEFAULT_SESSION_FILE})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum overage in dollars to include (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON instead of a formatted table",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Dump the raw API response to stderr for troubleshooting",
    )
    return parser.parse_args()


def load_token(session_path: str) -> str:
    """Load the auth token from session.json."""
    if not os.path.exists(session_path):
        raise FileNotFoundError(
            f"Session file not found: {session_path}\n"
            "Run 'python login.py' to create it."
        )
    with open(session_path, "r") as f:
        data = json.load(f)
    token = data.get("token")
    if not token:
        raise ValueError(
            f"'token' key missing or empty in {session_path}.\n"
            "Re-run 'python login.py' to regenerate the session file."
        )
    return token


def get_target_month() -> str:
    """Return current month as 'YYYY-MM' for filtering API data."""
    today = date.today()
    return f"{today.year}-{today.month:02d}"


def build_category_lookup(budget_data: dict) -> dict:
    """
    Walk categoryGroups[].categories[] to build:
        { category_id: {"name": str, "group": str} }
    """
    lookup = {}
    for group in budget_data.get("categoryGroups", []):
        group_name = group.get("name", "Unknown Group")
        for category in group.get("categories", []):
            cat_id = category.get("id")
            if cat_id:
                lookup[cat_id] = {
                    "name": category.get("name", "Unknown Category"),
                    "group": group_name,
                }
    return lookup


def extract_over_budget(budget_data: dict, threshold: float, debug: bool) -> list:
    """
    Traverse the budget API response and return categories where
    actual - planned >= threshold for the current month.
    """
    if debug:
        print("[DEBUG] Raw budget_data keys:", list(budget_data.keys()), file=sys.stderr)

    category_lookup = build_category_lookup(budget_data)
    target_month = get_target_month()  # e.g. "2026-02"
    over_budget = []

    # The API returns budgetData with monthlyAmountsByCategory
    budget_section = budget_data.get("budgetData", {})
    if debug:
        print("[DEBUG] budgetData keys:", list(budget_section.keys()), file=sys.stderr)

    monthly_by_cat = budget_section.get("monthlyAmountsByCategory", [])
    if debug:
        print(f"[DEBUG] monthlyAmountsByCategory entries: {len(monthly_by_cat)}", file=sys.stderr)

    for entry in monthly_by_cat:
        cat_obj = entry.get("category", {})
        cat_id = cat_obj.get("id")
        monthly_amounts = entry.get("monthlyAmounts", [])

        for month_entry in monthly_amounts:
            month_str = month_entry.get("month", "")
            # month_str is "YYYY-MM-DD"; compare only the YYYY-MM prefix
            if not month_str.startswith(target_month):
                continue

            planned = float(month_entry.get("plannedCashFlowAmount") or 0)
            actual = float(month_entry.get("actualAmount") or 0)

            # Skip income/transfer rows (both negative or both zero)
            if planned <= 0 and actual <= 0:
                continue

            overage = actual - planned
            if overage >= threshold:
                cat_info = category_lookup.get(cat_id, {})
                over_budget.append({
                    "category": cat_info.get("name", f"ID:{cat_id}"),
                    "group": cat_info.get("group", "Unknown"),
                    "planned": round(planned, 2),
                    "actual": round(actual, 2),
                    "overage": round(overage, 2),
                })

    # Sort worst offenders first
    over_budget.sort(key=lambda x: x["overage"], reverse=True)
    return over_budget


def print_console_report(over_budget: list, threshold: float, month: str):
    """Print a formatted, aligned table to stdout."""
    width = 68
    print()
    print(f"  Monarch Money Over-Budget Report")
    print(f"  Month: {month}   |   Threshold: ${threshold:.0f}+")
    print(f"  {'─' * width}")

    if not over_budget:
        print(f"  No categories are over budget by ${threshold:.0f} or more.")
        print(f"  {'─' * width}")
        print()
        return

    # Header
    print(f"  {'Category':<28} {'Group':<18} {'Planned':>9} {'Actual':>9} {'Over By':>9}")
    print(f"  {'─' * 28} {'─' * 18} {'─' * 9} {'─' * 9} {'─' * 9}")

    for item in over_budget:
        cat = item["category"][:27]
        grp = item["group"][:17]
        print(
            f"  {cat:<28} {grp:<18}"
            f"  ${item['planned']:>8.2f}  ${item['actual']:>8.2f}  ${item['overage']:>8.2f}"
        )

    total = sum(i["overage"] for i in over_budget)
    count = len(over_budget)
    print(f"  {'─' * width}")
    print(f"  {count} categor{'y' if count == 1 else 'ies'} over budget.  "
          f"Total overage: ${total:.2f}")
    print()


def is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in ["unauthorized", "401", "403", "forbidden", "token", "auth"])


async def run(args):
    # Load token
    try:
        token = load_token(args.session)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        msg = str(e)
        if args.json_output:
            print(json.dumps({"error": msg, "code": "SESSION_ERROR"}))
        else:
            print(f"ERROR: {msg}")
        sys.exit(1)

    mm = MonarchMoney(token=token)

    # Fetch budgets
    try:
        budget_data = await mm.get_budgets()
    except Exception as e:
        if is_auth_error(e):
            msg = ("Session appears to be expired or invalid. "
                   "Re-run 'python login.py' to refresh the session.")
            code = "SESSION_EXPIRED"
        else:
            msg = f"Failed to fetch budget data: {e}"
            code = "API_ERROR"

        if args.json_output:
            print(json.dumps({"error": msg, "code": code}))
        else:
            print(f"ERROR: {msg}")
        sys.exit(1)

    if args.debug:
        print("[DEBUG] Full API response:", file=sys.stderr)
        print(json.dumps(budget_data, indent=2, default=str), file=sys.stderr)

    over_budget = extract_over_budget(budget_data, args.threshold, args.debug)
    target_month = get_target_month()

    if args.json_output:
        output = {
            "month": target_month,
            "threshold": args.threshold,
            "over_budget": over_budget,
            "total_overage": round(sum(i["overage"] for i in over_budget), 2),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        print(json.dumps(output, indent=2))
    else:
        print_console_report(over_budget, args.threshold, target_month)


def main():
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
