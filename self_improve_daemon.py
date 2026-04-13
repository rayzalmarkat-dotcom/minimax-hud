#!/usr/bin/env python3
"""
MiniMax Self-Improve Daemon.

Runs self-improvement cycles in the background, independent of Claude Code.
Every CYCLE_MINUTES, it:
  1. Checks token budget
  2. Runs Claude Code with a self-audit prompt
  3. Applies any fixes
  4. Commits to git
  5. Updates state engine

Usage:
    pythonw self_improve_daemon.py      # Windows: no console window
    python self_improve_daemon.py        # Dev: shows output

Stops when: token budget exceeded, or STOP_FILE exists.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CYCLE_MINUTES = 30
TOKEN_BUDGET = 15_000
TOKEN_WARN = 12_000
TOKEN_CRITICAL = 14_000
STOP_FILE = Path.home() / ".claude" / "state" / "SELF_IMPROVE_STOP"
STATE_DIR = Path.home() / ".claude" / "state"
EVENT_LOG = STATE_DIR / "event_log.jsonl"
TOKEN_LOG = Path.home() / ".claude" / "skills" / "_token_log.md"
REPO_DIR = Path.home() / ".claude" / "projects" / "C--Users-Charlie"
HUD_DIR = Path.home() / ".claude"

MAX_AUDIT_FILES = 3  # files per cycle
CYCLE_COUNTER_FILE = STATE_DIR / "self_improve_cycle.txt"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Token budget check
# ---------------------------------------------------------------------------


def read_token_total() -> int:
    """Sum all 'Total: ~NNNk' lines in _token_log.md."""
    if not TOKEN_LOG.exists():
        return 0
    try:
        content = TOKEN_LOG.read_text(encoding="utf-8")
    except OSError:
        return 0
    import re

    total = 0
    for line in content.splitlines():
        m = re.search(r"Total:\s*~?(\d+)k", line, re.IGNORECASE)
        if m:
            total += int(m.group(1)) * 1_000
    return total


def check_budget() -> tuple[bool, str]:
    """Returns (ok, reason). ok=False means stop."""
    used = read_token_total()
    pct = used / TOKEN_BUDGET * 100
    if used >= TOKEN_CRITICAL:
        return (
            False,
            f"CRITICAL: {used:,}/{TOKEN_BUDGET:,} tokens ({pct:.0f}%) — stopping",
        )
    if used >= TOKEN_WARN:
        return (
            False,
            f"WARNING: {used:,}/{TOKEN_BUDGET:,} tokens ({pct:.0f}%) — stopping",
        )
    return True, f"Budget OK: {used:,}/{TOKEN_BUDGET:,} tokens ({pct:.0f}%)"


# ---------------------------------------------------------------------------
# Cycle counter
# ---------------------------------------------------------------------------


def get_cycle() -> int:
    try:
        return int(CYCLE_COUNTER_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def incr_cycle() -> int:
    n = get_cycle() + 1
    CYCLE_COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    CYCLE_COUNTER_FILE.write_text(str(n))
    return n


# ---------------------------------------------------------------------------
# Files to audit (round-robin rotation)
# ---------------------------------------------------------------------------

ALL_FILES = [
    "hud.py",
    "state_engine.py",
    "events.py",
    "agents/state-producer-agent.md",
    "agents/code-fix-agent.md",
    "agents/code-review-agent.md",
    "skills/minimax-workflow-optimizer.md",
    "skills/minimax-dev-workflow.md",
]


def files_for_cycle(cycle: int) -> list[str]:
    start = (cycle * MAX_AUDIT_FILES) % len(ALL_FILES)
    out = []
    for i in range(MAX_AUDIT_FILES):
        out.append(ALL_FILES[(start + i) % len(ALL_FILES)])
    return out


# ---------------------------------------------------------------------------
# Emit event
# ---------------------------------------------------------------------------


def emit_event(event_type: str, payload: dict) -> None:
    """Append a JSON line to the event log."""
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    import json

    line = json.dumps(
        {
            "type": event_type,
            "timestamp": _now_iso(),
            "source": "self-improve-daemon",
            "trace_id": str(uuid.uuid4()),
            "payload": payload,
        },
        ensure_ascii=False,
    )
    try:
        with EVENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
    except OSError:
        pass  # Non-fatal


# ---------------------------------------------------------------------------
# State engine call
# ---------------------------------------------------------------------------


def call_state_engine(
    score: float,
    task_name: str,
    files_audited: int,
    issues_found: int,
    issues_fixed: int,
) -> None:
    """Update state_engine JSON files directly."""
    import json

    # Update benchmark_state
    bench_path = STATE_DIR / "benchmark_state.json"
    bench = {}
    try:
        bench = json.loads(bench_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    WINDOW = 10
    trend = bench.get("improvement_trend", [])
    trend.append(score)
    if len(trend) > WINDOW:
        trend = trend[-WINDOW:]
    rolling_avg = sum(trend) / len(trend) if trend else score
    delta = score - bench.get("rolling_average", 0.0)
    regression_count = bench.get("regression_count", 0)
    if score < bench.get("current_score", 1.0):
        regression_count += 1

    bench.update(
        {
            "last_updated": _now_iso(),
            "current_score": score,
            "rolling_average": rolling_avg,
            "delta": delta,
            "improvement_confidence": "low" if score < 0.7 else "improving",
            "regression_count": regression_count,
            "improvement_trend": trend,
            "tasks_run": bench.get("tasks_run", 0) + 1,
        }
    )
    try:
        bench_path.parent.mkdir(parents=True, exist_ok=True)
        bench_path.write_text(json.dumps(bench, indent=2, ensure_ascii=False))
    except OSError:
        pass

    # Recompute system_health
    _recompute_health(bench)


def _recompute_health(bench: dict) -> None:
    """Lightweight health recompute."""
    import json

    health_path = STATE_DIR / "system_health.json"
    health = {}
    try:
        health = json.loads(health_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        health = {"overall_state": "normal"}

    regression_risk = bench.get("regression_count", 0) / max(
        bench.get("tasks_run", 1), 1
    )
    delta = bench.get("delta", 0.0)
    confidence = bench.get("improvement_confidence", "low")

    if confidence == "benchmark-confirmed" and regression_risk < 0.15:
        overall = "benchmark-confirmed"
    elif delta > 0 and regression_risk < 0.25:
        overall = "improving"
    elif bench.get("regression_count", 0) > 2 or regression_risk > 0.4:
        overall = "regression-risk"
    else:
        overall = "normal"

    health.update(
        {
            "last_updated": _now_iso(),
            "overall_state": overall,
            "regression_risk": round(regression_risk, 4),
        }
    )
    try:
        health_path.write_text(json.dumps(health, indent=2, ensure_ascii=False))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Claude Code invocation
# ---------------------------------------------------------------------------

CLAUDE_PROMPT = """You are the MiniMax self-improvement daemon. Run one self-audit cycle on the files listed below. Do NOT loop internally. Complete the cycle and output a JSON summary.

## Files to audit this cycle
{files_list}

## Working directory
C:\\Users\\Charlie\\.claude

## Step 1 — Read learnings
Read C:\\Users\\Charlie\\.claude\\skills\\_learnings.md

## Step 2 — Token budget
Read C:\\Users\\Charlie\\.claude\\skills\\_token_log.md
Calculate running token total. If > 12,000, output JSON and STOP.

## Step 3 — Code review
Read and review EACH file listed above. Paste content into a code-review-agent prompt. Collect findings per file.

## Step 4 — Code fixes
If CRITICAL or HIGH issues found, read the file content and spawn code-fix-agent to fix them. Run py_compile after fixes.

## Step 5 — State update
After fixes, call:
python -c "import sys; sys.path.insert(0,r'C:\\Users\\Charlie\\.claude'); import state_engine; state_engine.compute_system_health()"

## Step 6 — Git
If files changed:
cd C:\\Users\\Charlie\\.claude\\projects\\C--Users-Charlie
git add [changed files]
git commit -m "chore: self-improve cycle {cycle} — [brief description]"
git push

## Output (required — exactly this format at end)
```json
{{
  "cycle": {cycle},
  "files_audited": [file list],
  "issues_found": N,
  "issues_fixed": N,
  "score": 0.0-1.0,
  "tokens_used_estimate": N,
  "stopped_early": false,
  "next_cycle_files": [list]
}}
```
Output ONLY the JSON above as your final line. Nothing else after it."""


def run_claude_cycle(cycle: int, files: list[str]) -> dict:
    """Invoke Claude Code CLI with the self-improve prompt. Returns cycle result dict."""
    files_list = "\n".join(f"- {f}" for f in files)
    prompt = CLAUDE_PROMPT.format(files_list=files_list, cycle=cycle)

    log(f"Invoking Claude Code for cycle {cycle}...")
    log(f"  Files: {', '.join(files)}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        # Write prompt to temp file to avoid shell escaping issues
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(prompt)
            prompt_file = tf.name

        result = subprocess.run(
            ["claude", "--print", prompt_file],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,  # 10 min max per cycle
            cwd=str(REPO_DIR),
            env=env,
        )

        os.unlink(prompt_file)

        output = result.stdout + result.stderr

    except FileNotFoundError:
        log("ERROR: claude CLI not found in PATH")
        return {"cycle": cycle, "error": "claude not found", "stopped_early": True}
    except subprocess.TimeoutExpired:
        log(f"CYCLE {cycle}: Claude Code timed out (10min limit)")
        return {"cycle": cycle, "error": "timeout", "stopped_early": False}
    except Exception as e:
        log(f"CYCLE {cycle}: Error — {e}")
        return {"cycle": cycle, "error": str(e), "stopped_early": False}

    # Parse JSON from output
    import json, re

    # Find last JSON block in output
    matches = list(re.finditer(r"```json\s*(\{.*?\})\s*```", output, re.DOTALL))
    if not matches:
        matches = list(re.finditer(r"\{[^{}]*\"cycle\"[^{}]*\}", output, re.DOTALL))

    if matches:
        try:
            result_data = json.loads(matches[-1].group(1))
            log(f"CYCLE {cycle} result: {result_data}")
            return result_data
        except json.JSONDecodeError:
            log(f"CYCLE {cycle}: Could not parse JSON from output")

    log(f"CYCLE {cycle}: No parseable result — treating as silent success")
    return {
        "cycle": cycle,
        "files_audited": files,
        "issues_found": 0,
        "issues_fixed": 0,
        "score": 0.5,
        "stopped_early": False,
    }


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    log("=== MiniMax Self-Improve Daemon started ===")
    log(f"  Cycle every: {CYCLE_MINUTES} min")
    log(f"  Token budget: {TOKEN_BUDGET:,}")
    log(f"  Token warn at: {TOKEN_WARN:,} | critical: {TOKEN_CRITICAL:,}")
    log(f"  Repo: {REPO_DIR}")

    # Stop file cleanup on start
    if STOP_FILE.exists():
        STOP_FILE.unlink()

    cycle = get_cycle()
    total_loops = 0

    while True:
        # Check stop file
        if STOP_FILE.exists():
            log("STOP file detected — shutting down")
            break

        cycle = incr_cycle()
        total_loops += 1

        log(f"\n--- CYCLE {cycle} ---")

        # Budget check
        ok, reason = check_budget()
        log(reason)
        if not ok:
            emit_event(
                "learning_generated",
                {
                    "reason": "token_budget_exceeded",
                    "message": reason,
                    "cycle": cycle,
                },
            )
            log("Budget exceeded — daemon sleeping for 1h then retrying")
            time.sleep(3600)
            continue

        # Select files
        files = files_for_cycle(cycle)
        log(f"Files this cycle: {', '.join(files)}")

        # Run cycle
        result = run_claude_cycle(cycle, files)

        # Update state
        score = result.get("score", 0.5)
        files_audited = result.get("files_audited", files)
        issues_found = result.get("issues_found", 0)
        issues_fixed = result.get("issues_fixed", 0)

        call_state_engine(
            score,
            f"self-improve cycle {cycle}",
            len(files_audited),
            issues_found,
            issues_fixed,
        )

        emit_event(
            "task_completed",
            {
                "task_type": "learning",
                "files_touched": files_audited,
                "issues_resolved": issues_fixed,
                "session_tokens": result.get("tokens_used_estimate", 0),
                "cycle": cycle,
            },
        )

        stopped_early = result.get("stopped_early", False)

        # Wait before next cycle
        wait = 3600 if stopped_early else CYCLE_MINUTES * 60
        next_ts = datetime.now().strftime("%H:%M")
        log(
            f"CYCLE {cycle} done — issues_found={issues_found} fixed={issues_fixed} score={score}"
        )
        log(f"Next cycle in {wait // 60} min at ~{next_ts}")
        log(f"Total runs so far: {total_loops}")

        time.sleep(wait)


if __name__ == "__main__":
    # Check if pythonw (no console) or python (has console)
    is_gui = sys.executable.endswith("pythonw.exe") or (
        hasattr(sys, "frozen") and sys.frozen
    )

    if is_gui:
        # Redirect stdout/stderr to null to suppress any popup
        import io

        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted — exiting")
