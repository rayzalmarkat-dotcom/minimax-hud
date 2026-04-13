"""
MiniMax Agent State Engine.

Single source of truth for all HUD v2 state. Manages read/write of all
state JSON files under ~/.claude/state/, with atomic writes throughout.

Pre-read-once pattern: callers are expected to hold state in memory and
pass it back on update — never re-read from disk mid-operation.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = Path.home() / ".claude" / "state"

VALID_HEALTH_STATES = frozenset(
    [
        "normal",
        "improving",
        "warning",
        "degraded",
        "noisy",
        "bloated",
        "regression-risk",
        "benchmark-confirmed",
    ]
)

# State filenames (all relative to STATE_DIR)
_AGENT_REGISTRY_FILE = "agent_registry.json"
_BENCHMARK_FILE = "benchmark_state.json"
_LEARNING_PIPELINE_FILE = "learning_pipeline.json"
_MEMORY_STATE_FILE = "memory_state.json"
_SYSTEM_HEALTH_FILE = "system_health.json"
_CHANGELOG_FILE = "changelog.json"
_ROUTING_STATE_FILE = "routing_state.json"
_VERIFICATION_FILE = "verification_state.json"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, return empty dict on error (file missing/corrupt)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    """
    Atomic write: write to a temp file in the same directory, then rename.
    Prevents partial-write corruption on crash.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".tmp_",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        shutil.move(tmp_path, path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Core read / write
# ---------------------------------------------------------------------------


def read_state(filename: str) -> dict[str, Any]:
    """
    Read a single state JSON file.

    Args:
        filename: Name of the file inside STATE_DIR (e.g. "agent_registry.json")

    Returns:
        Parsed JSON as a dict. Empty dict if file is missing or corrupt.
    """
    path = STATE_DIR / filename
    return _read_json(path)


def write_state(filename: str, data: dict[str, Any]) -> None:
    """
    Atomically write a dict to a state JSON file.

    Args:
        filename: Name of the file inside STATE_DIR.
        data: State dict to serialise.
    """
    path = STATE_DIR / filename
    _atomic_write(path, data)


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------


def update_agent(agent_data: dict[str, Any]) -> None:
    """
    Add or update an agent in agent_registry.json.

    Computes global_metrics automatically:
    - agents_created_today:  agents with sessions == 0
    - agents_retired_today:  agents with lifecycle_state == "retired"
    - active_spawned_agents: non-core agents
    - redundancy_rate:      fraction of non-core agents (spawned/called ratio)
    - low_value_agent_rate: non-core agents with calls > 0 but no sessions

    Args:
        agent_data: Dict with agent_id and fields to upsert.
    """
    state = read_state(_AGENT_REGISTRY_FILE)
    agents = state.get("agents", [])
    idx = next(
        (i for i, a in enumerate(agents) if a["agent_id"] == agent_data["agent_id"]),
        -1,
    )
    if idx >= 0:
        agents[idx] = {**agents[idx], **agent_data}
    else:
        agents.append(agent_data)

    # Recompute global_metrics
    core_count = sum(1 for a in agents if a.get("lifecycle_state") == "core")
    non_core = [a for a in agents if a.get("lifecycle_state") != "core"]
    created_today = sum(1 for a in agents if a.get("sessions", 0) == 0)
    retired_today = sum(1 for a in agents if a.get("lifecycle_state") == "retired")
    active_spawned = len(non_core)
    total_calls = sum(a.get("calls", 0) for a in agents)
    low_value = sum(
        1 for a in non_core if a.get("calls", 0) > 0 and a.get("sessions", 0) == 0
    )

    state["agents"] = agents
    state["global_metrics"] = {
        "agents_created_today": created_today,
        "agents_retired_today": retired_today,
        "active_spawned_agents": active_spawned,
        "spawn_success_rate": (
            1.0 if total_calls == 0 else (total_calls - low_value) / total_calls
        ),
        "redundancy_rate": (0.0 if len(agents) == 0 else len(non_core) / len(agents)),
        "low_value_agent_rate": (
            0.0 if active_spawned == 0 else low_value / active_spawned
        ),
    }
    state["last_updated"] = _now_iso()
    write_state(_AGENT_REGISTRY_FILE, state)


# ---------------------------------------------------------------------------
# Benchmark state
# ---------------------------------------------------------------------------


def log_benchmark(
    score: float,
    task_name: str,
    benchmark_confirmed: bool,
    domain: str,
) -> None:
    """
    Record a benchmark result in benchmark_state.json.

    Shifts rolling_average over the last N=10 tasks, updates delta, appends
    to improvement_trend, and increments regression_count if score dropped.

    Args:
        score:              Numeric score for this run.
        task_name:          Human-readable name of the benchmark task.
        benchmark_confirmed: Whether this is a confirmed (not speculative) benchmark.
        domain:             Domain area (e.g. "code-fix", "routing").
    """
    state = read_state(_BENCHMARK_FILE)
    WINDOW = 10

    prev_avg = state.get("rolling_average", 0.0)
    prev_score = state.get("current_score", 0.0)

    # Shift rolling average
    trend = state.get("improvement_trend", [])
    trend.append(score)
    if len(trend) > WINDOW:
        trend = trend[-WINDOW:]
    rolling_avg = sum(trend) / len(trend)

    delta = score - prev_avg
    regression_count = state.get("regression_count", 0)
    regression_severity: list[str] = state.get("regression_severity", [])

    if score < prev_score:
        regression_count += 1
        severity = "severe" if (prev_score - score) > 0.1 else "minor"
        regression_severity.append(f"{task_name}:{severity}")
        if len(regression_severity) > WINDOW:
            regression_severity = regression_severity[-WINDOW:]

    # Determine improvement confidence
    if benchmark_confirmed:
        if delta > 0 and regression_count == 0:
            confidence = "benchmark-confirmed"
        elif delta > 0:
            confidence = "improving"
        elif regression_count > 2:
            confidence = "regression-risk"
        else:
            confidence = "low"
    else:
        confidence = "low"

    state.update(
        {
            "last_updated": _now_iso(),
            "previous_score": prev_score,
            "current_score": score,
            "rolling_average": rolling_avg,
            "delta": delta,
            "improvement_confidence": confidence,
            "regression_count": regression_count,
            "regression_severity": regression_severity,
            "tasks_run": state.get("tasks_run", 0) + 1,
            "improvement_trend": trend,
            "strongest_domain": (
                domain
                if rolling_avg > (state.get("rolling_average") or 0.0)
                else state.get("strongest_domain", "")
            ),
            "weakest_domain": (
                domain
                if rolling_avg < (state.get("rolling_average") or 0.0)
                else state.get("weakest_domain", "")
            ),
            "benchmark_freshness_seconds": 0,
            "benchmark_confirmed_vs_speculative_ratio": (
                state.get("tasks_run", 0)
                / max(state.get("tasks_run", 0) + (0 if benchmark_confirmed else 1), 1)
            ),
        }
    )
    write_state(_BENCHMARK_FILE, state)


# ---------------------------------------------------------------------------
# Learning pipeline
# ---------------------------------------------------------------------------

VALID_PIPELINE_EVENTS = frozenset(
    [
        "generated",
        "validated",
        "promoted",
        "rejected",
        "disproven",
        "pending",
    ]
)


def log_learning_change(pipeline_event: str) -> None:
    """
    Increment a counter in learning_pipeline.json.

    Args:
        pipeline_event: One of "generated", "validated", "promoted",
                       "rejected", "disproven", "pending".
    """
    if pipeline_event not in VALID_PIPELINE_EVENTS:
        raise ValueError(f"Unknown pipeline event: {pipeline_event!r}")

    state = read_state(_LEARNING_PIPELINE_FILE)
    state[pipeline_event] = state.get(pipeline_event, 0) + 1
    state["last_updated"] = _now_iso()
    write_state(_LEARNING_PIPELINE_FILE, state)


# ---------------------------------------------------------------------------
# Memory state
# ---------------------------------------------------------------------------


def log_memory_signal(
    hit_rate: float,
    usefulness: float,
    noise: float,
) -> None:
    """
    Update memory_state.json with a new retrieval signal.

    Args:
        hit_rate:   Retrieval hit rate (0.0–1.0).
        usefulness: Usefulness score of retrieved memories (0.0–1.0).
        noise:      Noise score of retrieved memories (0.0–1.0).
    """
    state = read_state(_MEMORY_STATE_FILE)

    # Exponential moving average (alpha=0.2) for smooth tracking
    alpha = 0.2
    state["retrieval_hit_rate"] = alpha * hit_rate + (1 - alpha) * state.get(
        "retrieval_hit_rate", 0.0
    )
    state["usefulness_score"] = alpha * usefulness + (1 - alpha) * state.get(
        "usefulness_score", 0.0
    )
    state["noise_score"] = alpha * noise + (1 - alpha) * state.get("noise_score", 0.0)
    state["last_updated"] = _now_iso()
    write_state(_MEMORY_STATE_FILE, state)


# ---------------------------------------------------------------------------
# Routing state
# ---------------------------------------------------------------------------


def log_routing_decision(
    claude_calls_delta: int = 0,
    minimax_calls_delta: int = 0,
    escalation: bool = False,
    bad_routing: bool = False,
) -> None:
    """
    Update routing_state.json after a routing decision.

    Recomputes workload_split_pct from cumulative totals.

    Args:
        claude_calls_delta:   Change in Claude (Opus/Sonnet) call count.
        minimax_calls_delta:  Change in MiniMax call count.
        escalation:           Whether this decision required human escalation.
        bad_routing:          Whether routing was suboptimal.
    """
    state = read_state(_ROUTING_STATE_FILE)

    state["claude_calls"] = state.get("claude_calls", 0) + claude_calls_delta
    state["minimax_calls"] = state.get("minimax_calls", 0) + minimax_calls_delta

    if escalation:
        state["escalation_count"] = state.get("escalation_count", 0) + 1
    if bad_routing:
        state["bad_routing_incidents"] = state.get("bad_routing_incidents", 0) + 1

    total = state["claude_calls"] + state["minimax_calls"]
    if total > 0:
        state["workload_split_pct"] = {
            "claude": state["claude_calls"] / total,
            "minimax": state["minimax_calls"] / total,
        }
        state["claude_overuse"] = state["claude_calls"] / total > 0.5
    else:
        state["workload_split_pct"] = {"claude": 0.0, "minimax": 0.0}
        state["claude_overuse"] = False

    state["last_updated"] = _now_iso()
    write_state(_ROUTING_STATE_FILE, state)


# ---------------------------------------------------------------------------
# Verification state
# ---------------------------------------------------------------------------


def log_verification(
    coverage: float,
    error_catch: float,
    hallucination_catch: float,
    contradiction_catch: float = 0.0,
    adversarial_review: bool = False,
    overconfidence: bool = False,
    underconfidence: bool = False,
) -> None:
    """
    Update verification_state.json with a verification result.

    All rate values are smoothed with exponential moving average (alpha=0.2).

    Args:
        coverage:            Verification coverage (0.0–1.0).
        error_catch:         Error catch rate (0.0–1.0).
        hallucination_catch: Hallucination catch rate (0.0–1.0).
        contradiction_catch: Contradiction catch rate (0.0–1.0).
        adversarial_review:  Whether this was an adversarial review pass.
        overconfidence:      Whether overconfidence was detected.
        underconfidence:     Whether underconfidence was detected.
    """
    state = read_state(_VERIFICATION_FILE)
    alpha = 0.2

    state["verification_coverage"] = alpha * coverage + (1 - alpha) * state.get(
        "verification_coverage", 0.0
    )
    state["error_catch_rate"] = alpha * error_catch + (1 - alpha) * state.get(
        "error_catch_rate", 0.0
    )
    state["hallucination_catch_rate"] = alpha * hallucination_catch + (
        1 - alpha
    ) * state.get("hallucination_catch_rate", 0.0)
    state["contradiction_catch_rate"] = alpha * contradiction_catch + (
        1 - alpha
    ) * state.get("contradiction_catch_rate", 0.0)
    if adversarial_review:
        state["adversarial_review_count"] = state.get("adversarial_review_count", 0) + 1
    if overconfidence:
        state["overconfidence_incidents"] = state.get("overconfidence_incidents", 0) + 1
    if underconfidence:
        state["underconfidence_incidents"] = (
            state.get("underconfidence_incidents", 0) + 1
        )

    state["last_updated"] = _now_iso()
    write_state(_VERIFICATION_FILE, state)


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------


def compute_system_health(
    prompt_health: str | None = None,
    memory_quality: float | None = None,
    routing_confidence: float | None = None,
    token_budget_pct: float | None = None,
    session_count_today: int | None = None,
) -> dict[str, Any]:
    """
    Read all state files, compute overall_state label, write system_health.json.

    Label priority (first match wins):
      1. "benchmark-confirmed"  — improvement_confidence == "benchmark-confirmed"
                                  AND regression_risk < 0.15
      2. "improving"            — delta > 0 AND regression_risk < 0.25
      3. "regression-risk"      — regression_count > 2 OR regression_risk > 0.4
      4. "degraded"             — token_budget_pct > 85 OR verification_coverage < 0.6
      5. "warning"              — any tracked metric below its threshold
      6. "normal"               — everything nominal

    Args:
        prompt_health:        Override for prompt_health field.
        memory_quality:       Override for memory_quality field.
        routing_confidence:   Override for routing_confidence field.
        token_budget_pct:    Override for token_budget_pct field.
        session_count_today: Override for session_count_today field.

    Returns:
        The full system_health dict that was written.
    """
    benchmark = read_state(_BENCHMARK_FILE)
    routing = read_state(_ROUTING_STATE_FILE)
    verification = read_state(_VERIFICATION_FILE)
    memory = read_state(_MEMORY_STATE_FILE)
    current_health = read_state(_SYSTEM_HEALTH_FILE)

    regression_risk = benchmark.get("regression_count", 0) / max(
        benchmark.get("tasks_run", 1), 1
    )
    delta = benchmark.get("delta", 0.0)
    improvement_confidence = benchmark.get("improvement_confidence", "low")
    verification_coverage = verification.get("verification_coverage", 0.0)
    memory_quality_val = memory.get("usefulness_score", 0.0)
    routing_confidence_val = routing.get("claude_calls", 0) + routing.get(
        "minimax_calls", 0
    )
    total_calls = routing.get("claude_calls", 0) + routing.get("minimax_calls", 0)
    routing_confidence_val = (
        1.0 - (routing.get("bad_routing_incidents", 0) / max(total_calls, 1))
        if total_calls > 0
        else 0.0
    )

    token_budget = (
        token_budget_pct
        if token_budget_pct is not None
        else current_health.get("token_budget_pct", 0.0)
    )
    sessions_today = (
        session_count_today
        if session_count_today is not None
        else current_health.get("session_count_today", 0)
    )

    # Determine overall_state label
    if improvement_confidence == "benchmark-confirmed" and regression_risk < 0.15:
        overall_state = "benchmark-confirmed"
    elif delta > 0 and regression_risk < 0.25:
        overall_state = "improving"
    elif benchmark.get("regression_count", 0) > 2 or regression_risk > 0.4:
        overall_state = "regression-risk"
    elif token_budget > 85 or verification_coverage < 0.6:
        overall_state = "degraded"
    elif (
        prompt_health == "degraded"
        or memory_quality_val < 0.5
        or routing_confidence_val < 0.7
        or regression_risk > 0.2
    ):
        overall_state = "warning"
    else:
        overall_state = "normal"

    result = {
        "last_updated": _now_iso(),
        "prompt_health": (
            prompt_health
            if prompt_health is not None
            else current_health.get("prompt_health", "stable")
        ),
        "rule_count": current_health.get("rule_count", 0),
        "memory_quality": (
            memory_quality if memory_quality is not None else memory_quality_val
        ),
        "routing_confidence": (
            routing_confidence
            if routing_confidence is not None
            else routing_confidence_val
        ),
        "regression_risk": round(regression_risk, 4),
        "overall_state": overall_state,
        "token_budget_pct": round(token_budget, 2),
        "session_count_today": sessions_today,
    }
    write_state(_SYSTEM_HEALTH_FILE, result)
    return result


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------


def log_changelog_entry(
    entry_type: str,
    description: str,
    benchmark_impact: str = "neutral",
    status: str = "applied",
    validated_by: str = "system",
) -> None:
    """
    Append an entry to changelog.json.

    Args:
        entry_type:       Category label for the change.
        description:      Human-readable description.
        benchmark_impact: "positive", "negative", "neutral".
        status:           "applied", "pending", "reverted".
        validated_by:     Agent or system that validated this.
    """
    state = read_state(_CHANGELOG_FILE)
    entry = {
        "timestamp": _now_iso(),
        "type": entry_type,
        "description": description,
        "benchmark_impact": benchmark_impact,
        "status": status,
        "validated_by": validated_by,
    }
    entries = state.get("entries", [])
    entries.append(entry)
    state["entries"] = entries
    state["last_updated"] = _now_iso()
    write_state(_CHANGELOG_FILE, state)


# ---------------------------------------------------------------------------
# Bulk read
# ---------------------------------------------------------------------------


def get_all_state() -> dict[str, dict[str, Any]]:
    """
    Read all state files and return as a single dict keyed by filename.

    Used by the HUD renderer to fetch full state in one call.

    Returns:
        {
          "agent_registry": {...},
          "benchmark_state": {...},
          ...
        }
    """
    files = [
        _AGENT_REGISTRY_FILE,
        _BENCHMARK_FILE,
        _LEARNING_PIPELINE_FILE,
        _MEMORY_STATE_FILE,
        _SYSTEM_HEALTH_FILE,
        _CHANGELOG_FILE,
        _ROUTING_STATE_FILE,
        _VERIFICATION_FILE,
    ]
    return {fname: read_state(fname) for fname in files}


# ---------------------------------------------------------------------------
# Module-level self-test (run with: python -m state_engine)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"STATE_DIR: {STATE_DIR}")
    print(f"STATE_DIR exists: {STATE_DIR.exists()}")
    if STATE_DIR.exists():
        for f in sorted(STATE_DIR.iterdir()):
            size = f.stat().st_size
            print(f"  {f.name} ({size} bytes)")
    else:
        print("  (directory not yet created — run module to initialise)")
