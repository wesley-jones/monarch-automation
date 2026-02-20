#!/usr/bin/env python3
"""
category_transactions.py — List transactions for a specific Monarch Money budget category.

Use this as a drill-down after running over_budget_report.py to see what
individual transactions make up a category's spending.

Usage:
    python category_transactions.py --category "Dining Out"
    python category_transactions.py --category "Natural Gas" --month 2026-01
    python category_transactions.py --category "Dining Out" --json
    python category_transactions.py --category "Dining Out" --limit 200
"""

import argparse
import asyncio
import calendar
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
DEFAULT_LIMIT = 100


def parse_args():
    parser = argparse.ArgumentParser(
        description="List transactions for a specific Monarch Money budget category"
    )
    parser.add_argument(
        "--category",
        required=True,
        help='Category name to look up (e.g. "Dining Out", "Natural Gas")',
    )
    parser.add_argument(
        "--month",
        default=None,
        help="Month to query as YYYY-MM (default: current month)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max transactions to return (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION_FILE,
        help=f"Path to session.json (default: {DEFAULT_SESSION_FILE})",
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
        help="Dump raw API responses to stderr for troubleshooting",
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


def is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in ["unauthorized", "401", "403", "forbidden", "token", "auth"])


def get_month_range(month_str: str | None) -> tuple[str, str]:
    """
    Return (start_date, end_date) for the given month as "YYYY-MM-DD" strings.
    If month_str is None, defaults to the current month.
    """
    if month_str:
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            raise ValueError(f"Invalid month format '{month_str}'. Use YYYY-MM (e.g. 2026-02).")
    else:
        today = date.today()
        year, month = today.year, today.month

    last_day = calendar.monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{last_day:02d}"
    return start, end


def find_category(categories_data: dict, name: str, debug: bool) -> tuple[str | None, str, list]:
    """
    Case-insensitive search for a category by name.
    Returns (category_id, matched_name, all_category_names).
    """
    categories = categories_data.get("categories", [])
    if debug:
        print(f"[DEBUG] Total categories returned: {len(categories)}", file=sys.stderr)

    all_names = sorted(c.get("name", "") for c in categories if not c.get("isDisabled", False))
    name_lower = name.lower()

    for cat in categories:
        if cat.get("isDisabled", False):
            continue
        if cat.get("name", "").lower() == name_lower:
            return cat["id"], cat["name"], all_names

    return None, name, all_names


def format_transactions(results: list) -> list:
    """Normalize raw API transaction objects into a clean list of dicts."""
    out = []
    for txn in results:
        merchant = (txn.get("merchant") or {}).get("name") or txn.get("plaidName") or ""
        account = (txn.get("account") or {}).get("displayName") or ""
        out.append({
            "date": txn.get("date", ""),
            "merchant": merchant,
            "amount": round(abs(float(txn.get("amount") or 0)), 2),
            "account": account,
            "notes": txn.get("notes") or "",
            "pending": bool(txn.get("pending", False)),
        })
    # Sort newest first
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def print_console_report(transactions: list, category: str, month: str):
    """Print a formatted aligned table to stdout."""
    width = 70
    print()
    print(f"  Transactions: {category} - {month}")
    print(f"  {'-' * width}")

    if not transactions:
        print(f"  No transactions found for '{category}' in {month}.")
        print(f"  {'-' * width}")
        print()
        return

    print(f"  {'Date':<12} {'Merchant':<30} {'Account':<18} {'Amount':>9}")
    print(f"  {'-' * 12} {'-' * 30} {'-' * 18} {'-' * 9}")

    for txn in transactions:
        merchant = txn["merchant"][:29]
        account = txn["account"][:17]
        pending = " *" if txn["pending"] else ""
        print(f"  {txn['date']:<12} {merchant:<30} {account:<18} ${txn['amount']:>8.2f}{pending}")

    total = sum(t["amount"] for t in transactions)
    count = len(transactions)
    print(f"  {'-' * width}")
    print(f"  {count} transaction{'s' if count != 1 else ''}   Total: ${total:.2f}")
    if any(t["pending"] for t in transactions):
        print(f"  * = pending")
    print()


async def run(args):
    # Parse and validate month
    try:
        start_date, end_date = get_month_range(args.month)
        month_label = start_date[:7]  # "YYYY-MM"
    except ValueError as e:
        msg = str(e)
        if args.json_output:
            print(json.dumps({"error": msg, "code": "INVALID_ARGS"}))
        else:
            print(f"ERROR: {msg}")
        sys.exit(1)

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

    # Fetch categories to resolve name → ID
    try:
        categories_data = await mm.get_transaction_categories()
    except Exception as e:
        if is_auth_error(e):
            msg = "Session appears to be expired. Re-run 'python login.py'."
            code = "SESSION_EXPIRED"
        else:
            msg = f"Failed to fetch categories: {e}"
            code = "API_ERROR"
        if args.json_output:
            print(json.dumps({"error": msg, "code": code}))
        else:
            print(f"ERROR: {msg}")
        sys.exit(1)

    if args.debug:
        print("[DEBUG] categories_data:", json.dumps(categories_data, indent=2, default=str),
              file=sys.stderr)

    cat_id, matched_name, all_names = find_category(categories_data, args.category, args.debug)

    if cat_id is None:
        msg = f"Category '{args.category}' not found."
        if args.json_output:
            print(json.dumps({
                "error": msg,
                "code": "CATEGORY_NOT_FOUND",
                "available_categories": all_names,
            }))
        else:
            print(f"ERROR: {msg}")
            print(f"\nAvailable categories:\n  " + "\n  ".join(all_names))
        sys.exit(1)

    # Fetch transactions
    try:
        txn_data = await mm.get_transactions(
            start_date=start_date,
            end_date=end_date,
            category_ids=[cat_id],
            limit=args.limit,
        )
    except Exception as e:
        if is_auth_error(e):
            msg = "Session appears to be expired. Re-run 'python login.py'."
            code = "SESSION_EXPIRED"
        else:
            msg = f"Failed to fetch transactions: {e}"
            code = "API_ERROR"
        if args.json_output:
            print(json.dumps({"error": msg, "code": code}))
        else:
            print(f"ERROR: {msg}")
        sys.exit(1)

    if args.debug:
        print("[DEBUG] txn_data keys:", list(txn_data.keys()), file=sys.stderr)

    results = (txn_data.get("allTransactions") or {}).get("results", [])
    transactions = format_transactions(results)

    if args.json_output:
        output = {
            "category": matched_name,
            "month": month_label,
            "transactions": transactions,
            "total": round(sum(t["amount"] for t in transactions), 2),
            "count": len(transactions),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        print(json.dumps(output, indent=2))
    else:
        print_console_report(transactions, matched_name, month_label)


def main():
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
