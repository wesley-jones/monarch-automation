# Monarch Money Over-Budget Report

A Python tool that queries [Monarch Money](https://monarchmoney.com) and reports
budget categories where actual spending has exceeded the planned amount for the
current month. Includes an [OpenClaw](https://openclaw.dev) skill wrapper for
AI assistant integration.

---

## Requirements

- Python 3.8+
- Node.js 16+ _(for the OpenClaw skill only)_
- A Monarch Money account with budgets configured
- OpenClaw _(for skill integration)_

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/monarch-automation.git
cd monarch-automation
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (bash)
source .venv/Scripts/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Authenticate with Monarch Money

Run the login helper once. It will prompt for your email, password, and MFA
code if two-factor authentication is enabled.

```bash
python login.py
```

This creates `session.json` in the project directory. The session token
typically lasts several months. Re-run `login.py` if the report starts
failing with an authentication error.

> **Security note:** `session.json` contains your Monarch Money session token.
> It is listed in `.gitignore` and must never be committed to version control.

---

## Usage

### Console report _(human-readable)_

```bash
python over_budget_report.py
```

Example output:

```
  Monarch Money Over-Budget Report
  Month: 2026-02   |   Threshold: $50+
  ────────────────────────────────────────────────────────────────────
  Category                     Group              Planned     Actual   Over By
  ──────────────────────────── ────────────────── ───────── ───────── ─────────
  Dining Out                   Food & Drink        $200.00   $312.45   $112.45
  Entertainment                Lifestyle            $50.00   $107.20    $57.20
  ────────────────────────────────────────────────────────────────────
  2 categories over budget.  Total overage: $169.65
```

### JSON output _(machine-readable)_

```bash
python over_budget_report.py --json
```

### Options

| Flag              | Default        | Description                                  |
|-------------------|----------------|----------------------------------------------|
| `--threshold N`   | `50`           | Minimum overage in dollars to include        |
| `--json`          | off            | Output JSON to stdout instead of a table     |
| `--session PATH`  | `session.json` | Path to session file                         |
| `--debug`         | off            | Dump raw API response to stderr              |

---

## OpenClaw Skill Integration

### Install the skill

**Option A — Symlink (recommended, keeps skill in sync with repo):**

```bash
# macOS / Linux
ln -s "$(pwd)/skills/monarch-report" ~/.openclaw/skills/monarch-report

# Windows (run as Administrator)
mklink /D "%USERPROFILE%\.openclaw\skills\monarch-report" "%CD%\skills\monarch-report"
```

**Option B — Copy:**

```bash
# macOS / Linux
cp -r skills/monarch-report ~/.openclaw/skills/

# Windows
xcopy /E skills\monarch-report %USERPROFILE%\.openclaw\skills\monarch-report\
```

> **If you copied (Option B):** Open
> `~/.openclaw/skills/monarch-report/impl.js` and update `PROJECT_ROOT` to
> point to wherever you cloned this repo:
>
> ```js
> // Replace this line:
> const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
> // With the absolute path, e.g.:
> const PROJECT_ROOT = "/Users/yourname/projects/monarch-automation";
> ```

### Reload OpenClaw

Use the OpenClaw UI reload button or restart the app after placing the skill.

### Example prompts

- "Am I over budget this month?"
- "Show me my budget overruns"
- "Which categories did I overspend by more than $100?" _(OpenClaw passes `threshold=100`)_

### Test the skill manually before using in OpenClaw

```bash
# Default $50 threshold
node skills/monarch-report/impl.js

# Custom threshold
node skills/monarch-report/impl.js 100
```

---

## Troubleshooting

**`Session file not found: session.json`**
Run `python login.py` to create the session file.

**`Session appears to be expired`**
Re-run `python login.py` to refresh your token.

**`monarchmoney is not installed`**
Run `pip install -r requirements.txt` (inside the activated venv).

**Report shows no categories**
Either you have no expenses over the threshold this month, or Monarch Money
doesn't have budgets configured for the current month. You can also run with
`--debug` to inspect the raw API response and verify the data structure.

**`impl.js` can't find `over_budget_report.py`**
If you copied the skill folder to `~/.openclaw/skills/` rather than symlinking,
update `PROJECT_ROOT` in `impl.js` as described in the install section above.

---

## Project Structure

```
monarch-automation/
├── login.py                    # Interactive auth helper — run once
├── over_budget_report.py       # Main report script
├── requirements.txt            # Python dependencies
├── session.json                # Created by login.py — DO NOT COMMIT
├── .gitignore
├── README.md
└── skills/
    └── monarch-report/
        ├── SKILL.md            # OpenClaw skill definition & LLM instructions
        └── impl.js             # Node.js wrapper invoked by OpenClaw
```
