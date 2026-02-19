---
name: monarch-report
description: Fetch Monarch Money budget data and return categories over budget for the current month.
requires:
  - python3
version: "1.0.0"
---

# Monarch Money Over-Budget Report

This skill connects to the Monarch Money personal finance platform and identifies
spending categories where actual spending has exceeded the planned budget amount
by a configurable threshold.

## Purpose

Use this skill when the user asks about budget overruns, over-spending, or wants
to know which categories they have gone over budget in for the current month.

Example triggers:
- "Am I over budget this month?"
- "Which categories have I overspent?"
- "Show me my budget overruns"
- "What did I go over budget on by more than $100?"

## Prerequisites

Before this skill can run, the user must have:

1. Installed the monarchmoney Python library:
   ```
   pip install -r requirements.txt
   ```
2. Run `python login.py` from the `monarch-automation` project directory to
   authenticate and create `session.json`. The session token typically lasts
   several months. Re-run `login.py` if the skill reports a session expired error.

## Inputs

| Parameter   | Type   | Default | Description                                             |
|-------------|--------|---------|---------------------------------------------------------|
| `threshold` | number | 50      | Minimum dollar amount over budget to include in results |

Pass `threshold` via the `THRESHOLD` environment variable or as the first
argument when invoking `impl.js` directly.

## Outputs

On success, the skill returns a JSON object:

```json
{
  "month": "2026-02",
  "threshold": 50,
  "over_budget": [
    {
      "category": "Dining Out",
      "group": "Food & Drink",
      "planned": 200.00,
      "actual": 312.45,
      "overage": 112.45
    }
  ],
  "total_overage": 112.45,
  "generated_at": "2026-02-19T14:30:00"
}
```

Results are sorted from highest overage to lowest.

On error, the skill returns:

```json
{
  "error": "Human-readable description",
  "code": "SESSION_ERROR | SESSION_EXPIRED | API_ERROR | DEPENDENCY_MISSING"
}
```

## Error Codes

| Code                 | Meaning                                              | Action                          |
|----------------------|------------------------------------------------------|---------------------------------|
| `SESSION_ERROR`      | `session.json` is missing or malformed               | Re-run `python login.py`        |
| `SESSION_EXPIRED`    | The stored token has expired                         | Re-run `python login.py`        |
| `API_ERROR`          | Monarch Money API returned an unexpected error       | Check network / API status      |
| `DEPENDENCY_MISSING` | The `monarchmoney` Python package is not installed   | Run `pip install -r requirements.txt` |

## Instructions

When this skill returns data, present the `over_budget` list to the user in a
clear, readable format. Highlight the worst offenders (sorted by overage). You
may calculate percentage over-budget if helpful.

If the `over_budget` list is empty, tell the user they are within budget on all
categories for the current month.

If the skill returns an error with code `SESSION_EXPIRED` or `SESSION_ERROR`,
instruct the user to run `python login.py` in the `monarch-automation` directory.
