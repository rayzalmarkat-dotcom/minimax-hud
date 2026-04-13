#!/usr/bin/env python
"""
MiniMax post-task loop.

Runs on the Stop hook after each Claude response. This script keeps the local
MiniMax system honest by updating:

- skills/_token_log.md
- skills/_learnings.md
- agents/_stockpile.md
- state_engine / events state used by the HUD

The loop is idempotent per transcript snapshot.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


HOME = Path.home()
CLAUDE_ROOT = HOME / ".claude"
STATE_ROOT = CLAUDE_ROOT / "state"
APP_STATE_PATH = STATE_ROOT / "minimax_post_task_loop.json"
CLAUDE_JSON_PATH = HOME / ".claude.json"
TOKEN_LOG_PATH = CLAUDE_ROOT / "skills" / "_token_log.md"
LEARNINGS_PATH = CLAUDE_ROOT / "skills" / "_learnings.md"
STOCKPILE_PATH = CLAUDE_ROOT / "agents" / "_stockpile.md"
CANONICAL_REQUEST_BUDGET = 15_000
WORKFLOW_KEYS = (
    "minimax-delegation",
    "minimax-dev-workflow",
    "minimax-workflow-optimizer",
)
LOOP_AGENTS = (
    "token-budget-agent",
    "learning-agent",
    "agent-stockpile-manager",
    "state-producer-agent",
)

sys.path.insert(0, str(CLAUDE_ROOT))

try:
    import events
    import state_engine
except Exception:
    events = None
    state_engine = None


@dataclass
class TranscriptSummary:
    task_name: str
    category: str
    delegatable: bool
    files_modified: list[str]
    tools_used: list[str]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _append_if_missing(path: Path, marker: str, block: str) -> None:
    content = _read_text(path)
    if marker in content:
        return
    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n" + block.strip() + "\n"
    path.write_text(content, encoding="utf-8")


def _parse_hook_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _extract_text(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content.strip()
    if isinstance(raw_content, list):
        parts: list[str] = []
        for block in raw_content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return " ".join(parts).strip()
    return ""


def _classify_task(task_name: str, tools_used: list[str]) -> tuple[str, bool]:
    text = f"{task_name} {' '.join(tools_used)}".lower()

    if any(word in text for word in ("review", "audit", "code review")):
        return "review", True
    if any(
        word in text
        for word in ("verify", "verification", "test", "pytest", "py_compile")
    ):
        return "verification", True
    if any(
        word in text
        for word in ("debug", "bug", "fix", "error", "failure", "broken")
    ):
        return "debugging", True
    if any(
        word in text
        for word in (
            "implement",
            "build",
            "create",
            "write",
            "modify",
            "edit",
            "change",
            "refactor",
            "add",
        )
    ):
        return "implementation", True
    if any(word in text for word in ("summarize", "summary", "explain", "synthesis")):
        return "synthesis", False
    if any(
        word in text for word in ("plan", "orchestrate", "route", "decompose", "policy")
    ):
        return "orchestration", False
    return "implementation", True


def _summarize_transcript(transcript_path: Path | None) -> TranscriptSummary:
    if not transcript_path or not transcript_path.exists():
        category, delegatable = _classify_task("implementation task", [])
        return TranscriptSummary(
            task_name="implementation task",
            category=category,
            delegatable=delegatable,
            files_modified=[],
            tools_used=[],
        )

    last_user_message = "implementation task"
    files_modified: list[str] = []
    tools_used: list[str] = []
    seen_files: set[str] = set()
    seen_tools: set[str] = set()

    for line in _read_text(transcript_path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue

        if entry.get("type") == "user" or entry.get("message", {}).get("role") == "user":
            text = _extract_text(entry.get("message", {}).get("content", entry.get("content")))
            if text:
                last_user_message = text

        if entry.get("type") == "tool_use" or entry.get("tool_name"):
            tool_name = entry.get("tool_name") or entry.get("name")
            if tool_name and tool_name not in seen_tools:
                seen_tools.add(tool_name)
                tools_used.append(tool_name)
            file_path = (
                entry.get("tool_input", {}).get("file_path")
                or entry.get("input", {}).get("file_path")
            )
            if file_path and file_path not in seen_files:
                seen_files.add(file_path)
                files_modified.append(file_path)

        if entry.get("type") == "assistant":
            for block in entry.get("message", {}).get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name")
                if tool_name and tool_name not in seen_tools:
                    seen_tools.add(tool_name)
                    tools_used.append(tool_name)
                file_path = block.get("input", {}).get("file_path")
                if file_path and file_path not in seen_files:
                    seen_files.add(file_path)
                    files_modified.append(file_path)

    task_name = re.sub(r"\s+", " ", last_user_message).strip()[:120]
    tools_used = tools_used[:12]
    category, delegatable = _classify_task(task_name, tools_used)
    return TranscriptSummary(
        task_name=task_name,
        category=category,
        delegatable=delegatable,
        files_modified=files_modified[:12],
        tools_used=tools_used,
    )


def _current_skill_counts() -> dict[str, int]:
    data = _read_json(CLAUDE_JSON_PATH, {})
    skill_usage = data.get("skillUsage", {})
    return {
        key: int(skill_usage.get(key, {}).get("usageCount", 0))
        for key in WORKFLOW_KEYS
    }


def _signature(transcript_path: Path | None, counts: dict[str, int], summary: TranscriptSummary) -> str:
    payload = {
        "transcript": str(transcript_path) if transcript_path else "",
        "size": transcript_path.stat().st_size if transcript_path and transcript_path.exists() else 0,
        "counts": counts,
        "task": summary.task_name,
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _tracked_request_total() -> tuple[int, int]:
    content = _read_text(TOKEN_LOG_PATH)
    tracked_requests = 0
    sessions = 0
    for line in content.splitlines():
        match = re.search(r"Tracked requests:\s*(\d+)", line, re.IGNORECASE)
        if match:
            tracked_requests += int(match.group(1))
            sessions += 1
    return tracked_requests, sessions


def _update_stockpile(today: str) -> None:
    content = _read_text(STOCKPILE_PATH)
    if not content:
        return

    lines = content.splitlines()
    updated: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Updated:"):
            updated.append(f"Updated: {today}")
            continue
        if not stripped.startswith("|"):
            updated.append(line)
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 8:
            updated.append(line)
            continue
        agent_name = parts[1]
        if agent_name not in LOOP_AGENTS:
            updated.append(line)
            continue
        last_used = today
        try:
            sessions = int(parts[5]) + 1
        except Exception:
            sessions = 1
        new_line = (
            f"| {parts[1]} | {parts[2]} | {parts[3]} | {last_used} | {sessions} | {parts[6]} |"
        )
        updated.append(new_line)

    STOCKPILE_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _emit_state(summary: TranscriptSummary, tracked_requests_delta: int, activations: dict[str, int], today: str) -> None:
    if events is None or state_engine is None:
        return

    trace_event = events.make_event(
        "task_completed",
        "minimax-post-task-loop",
        {
            "task": summary.task_name,
            "category": summary.category,
            "delegatable": summary.delegatable,
            "tracked_requests": tracked_requests_delta,
            "workflows": activations,
            "files": summary.files_modified,
        },
    )
    delegation_miss = summary.delegatable and tracked_requests_delta <= 0
    minimax_delta = 0
    claude_delta = 0
    if summary.category in {"orchestration", "synthesis"} and not summary.delegatable:
        claude_delta = 1
    elif delegation_miss:
        claude_delta = 1
    else:
        minimax_delta = max(1, tracked_requests_delta)

    events.make_event(
        "routing_decision_made",
        "minimax-post-task-loop",
        {
            "chosen_route": "claude" if claude_delta > 0 else "minimax",
            "controller": "Opus",
            "worker_model": "MiniMax-M2.7",
            "task": summary.task_name,
            "category": summary.category,
            "delegation_miss": delegation_miss,
        },
        trace_id=trace_event.trace_id,
    )
    events.make_event(
        "learning_generated",
        "minimax-post-task-loop",
        {
            "task": summary.task_name,
            "source": "auto-post-task-loop",
            "category": summary.category,
        },
        trace_id=trace_event.trace_id,
    )
    state_engine.log_routing_decision(
        claude_calls_delta=claude_delta,
        minimax_calls_delta=minimax_delta,
        escalation=False,
        bad_routing=delegation_miss,
        category=summary.category,
        claude_executed_delegatable=delegation_miss,
    )
    state_engine.log_learning_change("generated")

    registry = state_engine.read_state("agent_registry.json").get("agents", [])
    registry_by_id = {
        item.get("agent_id"): item
        for item in registry
        if isinstance(item, dict) and item.get("agent_id")
    }
    for agent_id in LOOP_AGENTS:
        prev = registry_by_id.get(agent_id, {})
        state_engine.update_agent(
            {
                "agent_id": agent_id,
                "display_name": agent_id,
                "lifecycle_state": "core",
                "calls": int(prev.get("calls", 0)) + 1,
                "sessions": int(prev.get("sessions", 0)) + 1,
                "last_used": today,
            }
        )

    total_requests, session_count = _tracked_request_total()
    pct_budget = (total_requests / CANONICAL_REQUEST_BUDGET) * 100 if CANONICAL_REQUEST_BUDGET else 0.0
    state_engine.log_changelog_entry(
        "learning",
        f"MiniMax post-task loop processed: {summary.task_name}",
        "neutral",
        validated_by="minimax-post-task-loop",
    )
    state_engine.compute_system_health(
        token_budget_pct=min(pct_budget, 100.0),
        session_count_today=session_count,
    )


def main() -> int:
    hook_input = _parse_hook_input()
    transcript_path = None
    transcript_raw = hook_input.get("transcript_path")
    if isinstance(transcript_raw, str) and transcript_raw.strip():
        transcript_path = Path(transcript_raw)

    counts = _current_skill_counts()
    summary = _summarize_transcript(transcript_path)
    signature = _signature(transcript_path, counts, summary)
    snapshot = _read_json(
        APP_STATE_PATH,
        {"last_signature": "", "skill_counts": {key: 0 for key in WORKFLOW_KEYS}},
    )
    previous_counts = snapshot.get("skill_counts", {})
    activations = {
        key: max(0, counts.get(key, 0) - int(previous_counts.get(key, 0)))
        for key in WORKFLOW_KEYS
    }
    tracked_requests_delta = sum(activations.values())

    if snapshot.get("last_signature") == signature:
        return 0

    snapshot_payload = {"last_signature": signature, "skill_counts": counts}

    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M")
    today = now.strftime("%Y-%m-%d")
    marker = f"<!-- minimax-loop:{signature} -->"

    activation_summary = ", ".join(
        f"{key} +{value}" for key, value in activations.items() if value > 0
    )
    if not activation_summary:
        activation_summary = "none"
    files_summary = ", ".join(summary.files_modified) if summary.files_modified else "none observed"
    tools_summary = ", ".join(summary.tools_used) if summary.tools_used else "none observed"

    token_block = f"""
{marker}
## Session: {stamp} — Auto MiniMax loop

Task: {summary.task_name}
Category: {summary.category}
Delegatable: {"yes" if summary.delegatable else "no"}
Tracked requests: {tracked_requests_delta}
Workflow activations: {activation_summary}
Files touched: {files_summary}
Tools observed: {tools_summary}
Efficiency tokens: unavailable from hook
"""
    _append_if_missing(TOKEN_LOG_PATH, marker, token_block)

    learning_block = f"""
{marker}
## Session: {stamp} — Auto loop: {summary.task_name}

### What worked
- Task category: `{summary.category}`.
- Delegatable: `{summary.delegatable}`.
- Routing outcome: `{"delegation miss" if summary.delegatable and tracked_requests_delta <= 0 else "MiniMax execution"}`.

### What failed
- Claude Code hooks do not expose raw MiniMax worker request totals, so tracked requests are a conservative lower bound.

### Actionable improvement
- Keep worker dispatch pinned to `MiniMax-M2.7`, prefer internal MiniMax skills, and treat Claude execution of delegatable work as a routing penalty.
"""
    _append_if_missing(LEARNINGS_PATH, marker, learning_block)

    _update_stockpile(today)
    _emit_state(summary, tracked_requests_delta, activations, today)
    _write_json(APP_STATE_PATH, snapshot_payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)
