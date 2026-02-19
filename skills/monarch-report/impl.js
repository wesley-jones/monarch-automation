/**
 * impl.js — OpenClaw skill wrapper for the Monarch Money over-budget report.
 *
 * Invoked by OpenClaw when the 'monarch-report' skill is triggered.
 * Shells out to over_budget_report.py and returns parsed JSON.
 *
 * Parameters (read from environment or argv):
 *   THRESHOLD env var — dollar threshold (default: 50)
 *   argv[2]           — threshold fallback if env var not set
 *
 * Direct testing:
 *   node impl.js          # uses threshold 50
 *   node impl.js 100      # uses threshold 100
 */

"use strict";

const { execSync } = require("child_process");
const path = require("path");

// ── Path resolution ───────────────────────────────────────────────────────────
// This file lives at:  skills/monarch-report/impl.js
// Project root is:     ../../  (two levels up)

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const SCRIPT_PATH = path.join(PROJECT_ROOT, "over_budget_report.py");
const SESSION_PATH = path.join(PROJECT_ROOT, "session.json");

// ── Parameters ────────────────────────────────────────────────────────────────

const threshold = process.env.THRESHOLD || process.argv[2] || "50";

// ── Python detection ──────────────────────────────────────────────────────────

function findPython() {
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
    "Python 3 is not available on PATH. " +
      "Install Python 3 and ensure it is accessible as 'python3' or 'python'."
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

function run() {
  const python = findPython();

  // Quote paths to handle spaces; --json ensures only JSON goes to stdout
  const command = [
    python,
    `"${SCRIPT_PATH}"`,
    "--json",
    "--threshold",
    threshold,
    "--session",
    `"${SESSION_PATH}"`,
  ].join(" ");

  let stdout;
  try {
    stdout = execSync(command, {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 30_000, // 30 seconds
    });
  } catch (err) {
    // execSync throws on non-zero exit.
    // over_budget_report.py always writes a JSON error object to stdout
    // when invoked with --json, so try to parse that first.
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
    // Fallback: surface raw stderr
    const stderr = (err.stderr || "").trim();
    throw new Error(
      `over_budget_report.py failed (exit ${err.status}).\n${stderr || "No stderr output."}`
    );
  }

  try {
    return JSON.parse(stdout.trim());
  } catch (_) {
    throw new Error(
      `Failed to parse JSON from over_budget_report.py.\nRaw output: ${stdout.slice(0, 500)}`
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
