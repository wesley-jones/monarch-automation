/**
 * impl.js — OpenClaw skill wrapper for Monarch Money category transactions.
 *
 * Invoked by OpenClaw when the 'monarch-transactions' skill is triggered.
 * Shells out to category_transactions.py and returns parsed JSON.
 *
 * Parameters (read from environment or argv):
 *   CATEGORY env var  — budget category name (required)
 *   MONTH env var     — month as YYYY-MM (optional, defaults to current month)
 *   argv[2]           — category fallback if env var not set
 *   argv[3]           — month fallback if env var not set
 *
 * Direct testing:
 *   node impl.js "Dining Out"
 *   node impl.js "Natural Gas" 2026-01
 */

"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

// ── Path resolution ───────────────────────────────────────────────────────────
// This file lives at:  skills/monarch-transactions/impl.js
// Project root is:     ../../  (two levels up)

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const SCRIPT_PATH = path.join(PROJECT_ROOT, "category_transactions.py");
const SESSION_PATH = path.join(PROJECT_ROOT, "session.json");

// ── Parameters ────────────────────────────────────────────────────────────────

const category = process.env.CATEGORY || process.argv[2] || "";
const month = process.env.MONTH || process.argv[3] || "";

// ── Python detection ──────────────────────────────────────────────────────────

function findPython() {
  // Prefer the project venv — it has all dependencies installed
  const venvCandidates = [
    path.join(PROJECT_ROOT, ".venv", "bin", "python"),      // Mac / Linux
    path.join(PROJECT_ROOT, ".venv", "Scripts", "python"),  // Windows
  ];
  for (const candidate of venvCandidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // Fall back to system Python 3
  for (const candidate of ["python3", "python"]) {
    try {
      const out = execSync(`${candidate} --version`, {
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      if (out.includes("Python 3")) {
        return candidate;
      }
    } catch (_) {
      // not available, try next
    }
  }
  throw new Error(
    "Python 3 not found. Create a venv at .venv/ or install Python 3 on PATH."
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

function run() {
  if (!category) {
    throw new Error(
      "No category specified. Pass it via the CATEGORY env var or as argv[2].\n" +
      "Example: node impl.js \"Dining Out\""
    );
  }

  const python = findPython();

  // Build command — quote paths and category to handle spaces
  const parts = [
    python,
    `"${SCRIPT_PATH}"`,
    "--json",
    "--category", `"${category}"`,
    "--session", `"${SESSION_PATH}"`,
  ];
  if (month) {
    parts.push("--month", month);
  }
  const command = parts.join(" ");

  let stdout;
  try {
    stdout = execSync(command, {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 30_000, // 30 seconds
    });
  } catch (err) {
    // category_transactions.py always writes a JSON error to stdout when --json
    const raw = (err.stdout || "").trim();
    if (raw) {
      try {
        const payload = JSON.parse(raw);
        const wrapped = new Error(payload.error || "Script exited with non-zero status");
        wrapped.payload = payload;
        throw wrapped;
      } catch (innerErr) {
        if (innerErr.payload) throw innerErr;
      }
    }
    const stderr = (err.stderr || "").trim();
    throw new Error(
      `category_transactions.py failed (exit ${err.status}).\n${stderr || "No stderr output."}`
    );
  }

  try {
    return JSON.parse(stdout.trim());
  } catch (_) {
    throw new Error(
      `Failed to parse JSON from category_transactions.py.\nRaw output: ${stdout.slice(0, 500)}`
    );
  }
}

// ── Export for OpenClaw ───────────────────────────────────────────────────────
module.exports = run;

// ── Direct invocation for testing ────────────────────────────────────────────
if (require.main === module) {
  try {
    const result = run();
    console.log(JSON.stringify(result, null, 2));
  } catch (err) {
    console.error("Skill error:", err.message);
    if (err.payload) {
      console.error("Payload:", JSON.stringify(err.payload, null, 2));
    }
    process.exit(1);
  }
}
