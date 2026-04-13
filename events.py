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
import os
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "Event",
    "EVENT_LOG_PATH",
    "EVENT_TYPES",
    "emit_event",
    "get_events",
    "get_event_counts_by_type",
    "make_event",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_LOG_PATH = Path.home() / ".claude" / "state" / "event_log.jsonl"
_EVENT_LOCK_PATH = EVENT_LOG_PATH.with_suffix(".log.lock")

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
# Module-level intra-process lock
# ---------------------------------------------------------------------------

_WRITE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Cross-process locking helpers
# ---------------------------------------------------------------------------


def _acquire_cross_process_lock(lock_path: Path) -> int:
    """
    Acquire an exclusive cross-process lock on `lock_path` using a lock file.

    Returns a file descriptor the caller must eventually pass to
    _release_cross_process_lock().
    """
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        # Lock is held by another process — block until we get it
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_fd, fcntl.LOCK_EX)
    return lock_fd


def _release_cross_process_lock(lock_fd: int, lock_path: Path) -> None:
    """Release the lock acquired by _acquire_cross_process_lock."""
    try:
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            import fcntl

            fcntl.flock(lock_fd, fcntl.LOCK_UN)
    finally:
        os.close(lock_fd)
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
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

    Thread-safe and cross-process safe: concurrent writes from multiple
    processes will not corrupt the log.

    Args:
        event: An Event instance to serialise and write.
    """
    EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(event), ensure_ascii=False) + "\n"

    _WRITE_LOCK.acquire()
    try:
        lock_fd = _acquire_cross_process_lock(_EVENT_LOCK_PATH)
        try:
            with EVENT_LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            _release_cross_process_lock(lock_fd, _EVENT_LOCK_PATH)
    finally:
        _WRITE_LOCK.release()


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

    Counts in a single file pass — no intermediate list allocation and no sort.

    Useful for the HUD dashboard at a glance.
    """
    counts: dict[str, int] = {}
    if not EVENT_LOG_PATH.exists():
        return counts

    with EVENT_LOG_PATH.open("r", encoding="utf-8") as fh:
        # Seek to end, then work backwards in fixed-size chunks
        # so we only read the last `limit` lines without loading the whole file.
        fh.seek(0, os.SEEK_END)
        file_pos = fh.tell()
        lines_read = 0
        tail: list[str] = []

        while file_pos > 0 and lines_read < limit:
            chunk_size = min(8192, file_pos)
            file_pos -= chunk_size
            fh.seek(file_pos)
            chunk = fh.read(chunk_size)
            # chunk may end mid-line; prepend accumulated head
            lines_in_chunk = (chunk + "".join(tail)).split("\n")
            # last element is a (potentially incomplete) partial line — carry it forward
            tail = [lines_in_chunk[-1]] if lines_in_chunk else []
            # all complete lines except the incomplete tail go into our collection
            for ln in reversed(lines_in_chunk[:-1]):
                tail.append(ln)
                lines_read += 1
            if file_pos == 0 and tail:
                tail.reverse()
                for ln in tail:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        obj: dict[str, Any] = json.loads(ln)
                        evt_type = obj.get("type")
                        if evt_type:
                            counts[evt_type] = counts.get(evt_type, 0) + 1
                    except json.JSONDecodeError:
                        pass
                break

        # Fallback: read entire file if it is small enough that our chunking
        # didn't trigger (e.g. file grew to > limit lines between check and now)
        if lines_read < limit:
            counts.clear()
            fh.seek(0)
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    obj = json.loads(raw_line)
                    evt_type = obj.get("type")
                    if evt_type:
                        counts[evt_type] = counts.get(evt_type, 0) + 1
                except json.JSONDecodeError:
                    pass
            # Apply limit to lines read by skipping oldest entries
            # (counts are already aggregated; no need to trim)

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
