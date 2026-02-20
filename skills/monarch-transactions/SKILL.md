---
name: monarch-transactions
description: List individual transactions for a specific Monarch Money budget category in the current (or specified) month.
requires:
  - python3
version: "1.0.0"
---

# Monarch Money Category Transactions

This skill fetches the individual transactions that make up spending in a
specific Monarch Money budget category. It is designed to be used as a
drill-down after the `monarch-report` skill identifies over-budget categories.

## Purpose

Use this skill when the user wants to see the specific transactions behind
a budget category — for example after being told "Dining Out is $112 over budget",
they ask "show me those transactions" or "what did I spend on dining out?".

Example triggers:
- "Show me my dining out transactions"
- "What did I spend on natural gas this month?"
- "Break down my HOA Dues charges"
- "What transactions are in the Sporting Goods category?"

## Prerequisites

Same as `monarch-report` — a valid `session.json` must exist in the project
directory. Run `python login.py` from the `monarch-automation` project if not.

## Inputs

| Parameter  | Type   | Required | Description                                                  |
|------------|--------|----------|--------------------------------------------------------------|
| `category` | string | Yes      | The budget category name (e.g. "Dining Out", "Natural Gas")  |
| `month`    | string | No       | Month as YYYY-MM (default: current month)                    |

Pass `category` via the `CATEGORY` environment variable or as the first
argument when invoking `impl.js` directly. Pass `month` via `MONTH` env var
or as the second argument.

Category names are matched case-insensitively. If the exact name isn't found,
the skill returns a `CATEGORY_NOT_FOUND` error with a list of all available
category names — present these to the user so they can pick the correct one.

## Outputs

On success:

```json
{
  "category": "Dining Out",
  "month": "2026-02",
  "transactions": [
    {
      "date": "2026-02-15",
      "merchant": "Chipotle",
      "amount": 45.67,
      "account": "Chase Checking",
      "notes": "",
      "pending": false
    }
  ],
  "total": 312.45,
  "count": 8,
  "generated_at": "2026-02-19T14:30:00"
}
```

Transactions are sorted newest first. Amounts are positive for expenses.
Pending transactions are flagged with `"pending": true`.

On error:

```json
{
  "error": "Human-readable description",
  "code": "CATEGORY_NOT_FOUND | SESSION_ERROR | SESSION_EXPIRED | API_ERROR | DEPENDENCY_MISSING",
  "available_categories": ["..."]
}
```

`available_categories` is only present when `code` is `CATEGORY_NOT_FOUND`.

## Error Codes

| Code                 | Meaning                                            | Action                               |
|----------------------|----------------------------------------------------|--------------------------------------|
| `CATEGORY_NOT_FOUND` | No category matched the given name                 | Show `available_categories` to user  |
| `SESSION_ERROR`      | `session.json` is missing or malformed             | Re-run `python login.py`             |
| `SESSION_EXPIRED`    | The stored token has expired                       | Re-run `python login.py`             |
| `API_ERROR`          | Monarch Money API returned an unexpected error     | Check network / API status           |
| `DEPENDENCY_MISSING` | The `monarchmoney` Python package is not installed | Run `pip install -r requirements.txt`|

## Instructions

Present the transaction list as a clean table or bullet list with date,
merchant name, and dollar amount. Show the total at the bottom.

If any transactions are marked `pending: true`, note that they haven't
fully settled yet and the total may change.

If the result is `CATEGORY_NOT_FOUND`, tell the user the category wasn't
recognized and show them the `available_categories` list so they can
provide the correct name.

If the `transactions` array is empty (but no error), tell the user there
are no transactions in that category for the given month.
