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
# MiniMax M2.7 10x Starter: 15,000 model REQUESTS / 5 hours
# This is a REQUEST count limit, NOT a token limit
REQUEST_BUDGET = 15_000
REQUEST_WARN = 11_250  # 75%
REQUEST_CRITICAL = 13_500  # 90%
STOP_FILE = Path.home() / ".claude" / "state" / "SELF_IMPROVE_STOP"
STATE_DIR = Path.home() / ".claude" / "state"
EVENT_LOG = STATE_DIR / "event_log.jsonl"
TOKEN_LOG = Path.home() / ".claude" / "skills" / "_token_log.md"
REPO_DIR = Path.home() / ".claude" / "projects" / "C--Users-Charlie"
HUD_DIR = Path.home() / ".claude"

sys.path.insert(0, str(HUD_DIR))
try:
    import state_engine
except Exception:
    state_engine = None

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
    """Returns (ok, reason). ok=False means stop.

    NOTE: MiniMax M2.7 10x Starter = 15,000 requests/5h. The token log tracks
    estimated tokens for efficiency monitoring — it is NOT the budget limiter.
    The real limit is MiniMax API request count (not tracked here).
    """
    used = read_token_total()
    pct = used / REQUEST_BUDGET * 100
    if used >= REQUEST_CRITICAL:
        return (
            False,
            f"WARNING: {used:,} estimated tokens logged — high usage, monitoring",
        )
    if used >= REQUEST_WARN:
        return (
            True,
            f"Budget OK: {used:,} est. tokens ({pct:.0f}% of request headroom)",
        )
    return True, f"Budget OK: {used:,} est. tokens ({pct:.0f}% of request headroom)"


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
    "skills/minimax-workflow-optimizer/SKILL.md",
    "skills/minimax-dev-workflow/SKILL.md",
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
    verified: bool,
    evidence: dict[str, Any],
) -> None:
    """Update benchmark/health state through the shared state engine."""
    if state_engine is None:
        return

    benchmark_confirmed = verified and score >= 0.6
    try:
        state_engine.log_benchmark(
            score=score,
            task_name=task_name,
            benchmark_confirmed=benchmark_confirmed,
            domain="self-improve-daemon",
            evidence=evidence,
        )
        state_engine.log_verification(
            coverage=float(evidence.get("coverage", 0.0) or 0.0),
            error_catch=1.0 if evidence.get("parseable_result", False) else 0.0,
            hallucination_catch=1.0 if evidence.get("verified", False) else 0.0,
            contradiction_catch=1.0 if benchmark_confirmed else 0.0,
            adversarial_review=bool(evidence.get("changed_files")),
            overconfidence=bool(score >= 0.75 and not benchmark_confirmed),
            underconfidence=bool(benchmark_confirmed and score < 0.5),
        )
        state_engine.log_changelog_entry(
            "self-improve",
            (
                f"{task_name}: audited {files_audited} file(s), "
                f"found {issues_found}, fixed {issues_fixed}"
            ),
            benchmark_impact="positive" if score >= 0.75 else "neutral",
            validated_by="self-improve-daemon",
        )
        state_engine.compute_system_health()
    except Exception as exc:
        log(f"WARNING: state_engine update failed: {exc}")


# ---------------------------------------------------------------------------
# Claude Code invocation
# ---------------------------------------------------------------------------

def _git_changed_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_DIR), "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
    except Exception:
        return []

    changed: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            path = line[3:].strip()
            if path:
                changed.append(path)
    return changed


def _verify_python_files(paths: list[str]) -> tuple[bool, list[str]]:
    python_files = [path for path in paths if path.lower().endswith(".py")]
    if not python_files:
        return True, []

    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", *python_files],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=str(REPO_DIR),
            check=False,
        )
    except Exception as exc:
        return False, [str(exc)]

    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        return False, [output or "py_compile failed"]
    return True, []


def _build_local_verification(
    cycle: int,
    files: list[str],
    result: dict[str, Any],
) -> dict[str, Any]:
    changed_files = _git_changed_files()
    python_compile_ok, python_compile_errors = _verify_python_files(changed_files)
    parseable_result = (
        isinstance(result, dict)
        and isinstance(result.get("cycle"), int)
        and "score" in result
        and result.get("error") is None
    )
    required_fields_present = all(
        key in result for key in ("files_audited", "issues_found", "issues_fixed")
    )
    changed_files_detected = bool(changed_files)
    issues_found = int(result.get("issues_found", 0) or 0)
    issues_fixed = int(result.get("issues_fixed", 0) or 0)

    checks = {
        "parseable_result": 1.0 if parseable_result else 0.0,
        "required_fields": 1.0 if required_fields_present else 0.0,
        "changed_files": 1.0 if changed_files_detected else 0.0,
        "python_compile_ok": 1.0 if python_compile_ok else 0.0,
        "issues_reported_consistent": (
            1.0 if issues_found >= 0 and issues_fixed >= 0 else 0.0
        ),
    }
    total_checks = len(checks)
    coverage = sum(checks.values()) / total_checks if total_checks else 0.0
    verified = parseable_result and python_compile_ok and changed_files_detected
    benchmark_confirmed = verified and coverage >= 0.6
    reported_score = float(result.get("score", 0.0) or 0.0)
    score = round(
        min(1.0, (0.75 * coverage) + (0.25 * reported_score if verified else 0.0)),
        2,
    )

    return {
        "cycle": cycle,
        "files_requested": files,
        "changed_files": changed_files,
        "python_compile_ok": python_compile_ok,
        "python_compile_errors": python_compile_errors,
        "parseable_result": parseable_result,
        "required_fields_present": required_fields_present,
        "coverage": round(coverage, 2),
        "verified": verified,
        "benchmark_confirmed": benchmark_confirmed,
        "score": score,
        "issues_found": issues_found,
        "issues_fixed": issues_fixed,
    }


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

    return {
        "cycle": cycle,
        "error": "no parseable result",
        "files_audited": files,
        "issues_found": 0,
        "issues_fixed": 0,
        "score": 0.0,
        "stopped_early": True,
    }


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    log("=== MiniMax Self-Improve Daemon started ===")
    log(f"  Cycle every: {CYCLE_MINUTES} min")
    log(f"  MiniMax limit: {REQUEST_BUDGET} requests / 5h (10x Starter)")
    log(f"  Token-warn at: {REQUEST_WARN} | critical: {REQUEST_CRITICAL}")
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

        verification = _build_local_verification(cycle, files, result)
        score = verification["score"]
        files_audited = result.get("files_audited", files)
        issues_found = verification["issues_found"]
        issues_fixed = verification["issues_fixed"]

        if not verification["verified"]:
            log(
                f"WARNING: cycle {cycle} verification is speculative "
                f"(changed_files={len(verification['changed_files'])}, "
                f"py_compile_ok={verification['python_compile_ok']})"
            )

        call_state_engine(
            score,
            f"self-improve cycle {cycle}",
            len(files_audited),
            issues_found,
            issues_fixed,
            verification["verified"],
            verification,
        )

        emit_event(
            "task_completed",
            {
                "task_type": "learning",
                "files_touched": files_audited,
                "issues_resolved": issues_fixed,
                "session_tokens": result.get("tokens_used_estimate", 0),
                "cycle": cycle,
                "verification": verification,
            },
        )

        stopped_early = result.get("stopped_early", False)

        # Wait before next cycle
        wait = 3600 if stopped_early else CYCLE_MINUTES * 60
        next_ts = datetime.now().strftime("%H:%M")
        log(
            f"CYCLE {cycle} done — issues_found={issues_found} fixed={issues_fixed} "
            f"score={score} verified={verification['verified']}"
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
