"""
MiniMax Agent Event Schema.

Provides structured event types, an Event dataclass, and helpers for
writing and reading the append-only event log at:

    ~/.claude/state/event_log.jsonl

Each line in the log is a JSON-encoded Event.  This gives the HUD v2 a
complete audit trail and replay / debugging capability.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_LOG_PATH = Path.home() / ".claude" / "state" / "event_log.jsonl"

EVENT_TYPES = frozenset(
    [
        "task_started",
        "task_completed",
        "task_failed",
        "benchmark_run_completed",
        "learning_generated",
        "learning_validated",
        "learning_rejected",
        "memory_promoted",
        "memory_retired",
        "routing_decision_made",
        "routing_failure_detected",
        "verification_completed",
        "agent_spawned",
        "agent_retired",
        "change_proposed",
        "change_confirmed",
        "change_rejected",
    ]
)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Event:
    """
    Structured event emitted by agents and the state engine.

    Attributes:
        type:       One of EVENT_TYPES.
        timestamp:  ISO8601 UTC timestamp.
        source:     Agent ID or "system".
        payload:    Arbitrary event-specific data.
        trace_id:   UUID used to correlate related events across a session.
    """

    type: str
    source: str
    payload: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise ValueError(
                f"Unknown event type {self.type!r}. "
                f"Valid types: {sorted(EVENT_TYPES)}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_trace_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def emit_event(event: Event) -> None:
    """
    Append a structured event to the append-only event log.

    The log file is created automatically if it does not exist.
    Each log line is a JSON object with no trailing comma — suitable for
    line-oriented reading (jq, grep, etc.).

    Args:
        event: An Event instance to serialise and write.
    """
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(event), ensure_ascii=False)
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def make_event(
    event_type: str,
    source: str,
    payload: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> Event:
    """
    Factory that creates and emits an event in one call.

    Returns the created Event for callers that need the trace_id.

    Args:
        event_type: One of EVENT_TYPES.
        source:     Agent ID or "system".
        payload:    Event-specific data dict.
        trace_id:   Optional trace ID; a new one is generated if omitted.

    Returns:
        The created Event instance.
    """
    evt = Event(
        type=event_type,
        source=source,
        payload=payload or {},
        timestamp=_now_iso(),
        trace_id=trace_id or _new_trace_id(),
    )
    emit_event(evt)
    return evt


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def get_events(
    since: datetime | None = None,
    event_type: str | None = None,
    source: str | None = None,
    trace_id: str | None = None,
    limit: int | None = None,
) -> list[Event]:
    """
    Read and filter the event log.

    Args:
        since:      Return only events at or after this UTC datetime.
        event_type: Return only events of this type.
        source:     Return only events from this source (agent ID).
        trace_id:   Return only events with this trace ID.
        limit:      Cap the number of returned events (most recent first).

    Returns:
        List of matching Event objects, newest first.
    """
    if not EVENT_LOG_PATH.exists():
        return []

    # Read all lines (append-only, so one pass is fine)
    events: list[Event] = []
    cutoff_iso = since.isoformat() if since else None

    with EVENT_LOG_PATH.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue  # Skip malformed lines rather than failing

            # Time filter
            if cutoff_iso and obj.get("timestamp", "") < cutoff_iso:
                continue
            # Type filter
            if event_type and obj.get("type") != event_type:
                continue
            # Source filter
            if source and obj.get("source") != source:
                continue
            # Trace filter
            if trace_id and obj.get("trace_id") != trace_id:
                continue

            try:
                events.append(Event(**obj))
            except (TypeError, ValueError):
                continue  # Skip events with unknown fields / missing required keys

    # Newest first, then apply limit
    events.sort(key=lambda e: e.timestamp, reverse=True)
    if limit is not None:
        events = events[:limit]

    return events


# ---------------------------------------------------------------------------
# Quick snapshot — last N events of each type
# ---------------------------------------------------------------------------


def get_event_counts_by_type(limit: int = 1000) -> dict[str, int]:
    """
    Return a count of each event type seen in the most recent `limit` log lines.

    Useful for the HUD dashboard at a glance.
    """
    events = get_events(limit=limit)
    counts: dict[str, int] = {}
    for evt in events:
        counts[evt.type] = counts.get(evt.type, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Module-level self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"EVENT_LOG_PATH: {EVENT_LOG_PATH}")
    print(f"Log exists: {EVENT_LOG_PATH.exists()}")
    counts = get_event_counts_by_type() if EVENT_LOG_PATH.exists() else {}
    if counts:
        print("Event counts:")
        for t, n in sorted(counts.items()):
            print(f"  {t}: {n}")
    else:
        print("  (no events logged yet)")
