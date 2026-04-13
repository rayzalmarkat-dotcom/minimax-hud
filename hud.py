#!/usr/bin/env python3
"""
MiniMax Agent HUD v2 — Live terminal dashboard.

Reads pre-computed state via state_engine.get_all_state() and renders
with rich.Live using in-place ANSI updates (no flicker, no new terminals).

Architecture:
    Agents → state_engine → JSON state files → hud.py reads → rich renders

Usage:
    PYTHONIOENCODING=utf-8 python ~/.claude/hud.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.box import Box
from rich.console import Console, Group as RichGroup
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Path bootstrap — ensure state_engine is importable from home dir
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path.home()))
from state_engine import get_all_state  # noqa: E402

# ---------------------------------------------------------------------------
# Bootstrap stdout to UTF-8 (Windows CP console defaults to cp1252,
# which cannot encode Unicode box-drawing / emoji characters used by the HUD)
# ---------------------------------------------------------------------------

import sys as _sys

if hasattr(_sys.stdout, "reconfigure"):
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except (
        Exception
    ):  # pragma: no cover — reconfigure can fail on some file-like objects
        pass


# ---------------------------------------------------------------------------
# Console singleton
# ---------------------------------------------------------------------------

console = Console(
    force_terminal=True,
    legacy_windows=False,  # use ANSI/VT sequences, not Win32 Console API (cp1252)
)

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

OVERALL_STATE_COLORS: dict[str, str] = {
    "normal": "green",
    "improving": "bright_green",
    "benchmark-confirmed": "cyan",
    "warning": "yellow",
    "degraded": "red",
    "noisy": "magenta",
    "bloated": "red dim",
    "regression-risk": "red bold",
}

CONFidence_COLORS: dict[str, str] = {
    "low": "red",
    "medium": "yellow",
    "benchmark-confirmed": "green",
}


def _delta_color(delta: float) -> str:
    if delta > 0:
        return "green"
    if delta < 0:
        return "red"
    return "dim"


def _score_color(score: float | None) -> str:
    if score is None:
        return "dim"
    if score > 80:
        return "green"
    if score > 50:
        return "yellow"
    return "red"


def _noise_label(noise: float | None) -> tuple[str, str]:
    if noise is None:
        return "—", "dim"
    if noise > 0.3:
        return "HIGH", "red"
    if noise > 0.15:
        return "OK", "yellow"
    return "LOW", "green"


def _overall_state_color(state: str | None) -> str:
    if state is None:
        return "dim"
    for key, color in OVERALL_STATE_COLORS.items():
        if key in state:
            return color
    return "white"


# ---------------------------------------------------------------------------
# Text-bar helpers
# ---------------------------------------------------------------------------


def _mini_trend_bar(trend: list[float], current_avg: float) -> Text:
    """Render last 10 benchmark scores as a text bar using █ / ▒."""
    if not trend:
        return Text("no data", style="dim")

    # Normalise to 0-1 range for display
    lo, hi = min(trend), max(trend)
    span = hi - lo if hi != lo else 1.0

    parts: list[tuple[str, str]] = []
    for s in trend[-10:]:
        norm = (s - lo) / span
        char = "█" if norm >= 0.6 else ("▒" if norm >= 0.35 else "░")
        color = "green" if norm >= 0.6 else "yellow" if norm >= 0.35 else "red"
        parts.append((char, color))

    result = Text()
    for char, color in parts:
        result.append(char, style=color)
    return result


def _split_bar(claude_pct: float, minimax_pct: float) -> Text:
    """Claude vs MiniMax workload split bar."""
    total = 30
    claude_w = round(claude_pct * total)
    minimax_w = total - claude_w
    t = Text()
    t.append("█" * claude_w, style="cyan")
    t.append("▓" * minimax_w, style="bright_black")
    return t


def _pipeline_bar(counts: dict[str, int]) -> Text:
    """6-state horizontal bar: GEN VAL PRO REJ DIS PEN."""
    states = [
        ("GEN", "generated"),
        ("VAL", "validated"),
        ("PRO", "promoted"),
        ("REJ", "rejected"),
        ("DIS", "disproven"),
        ("PEN", "pending"),
    ]
    state_colors = {
        "generated": "dim",
        "validated": "yellow",
        "promoted": "green",
        "rejected": "red",
        "disproven": "red",
        "pending": "dim",
    }

    result = Text()
    for label, key in states:
        n = counts.get(key, 0)
        # fill with ▓ proportional to n, capped at 8 chars
        filled = min(n, 8)
        color = state_colors[key]
        result.append(f"{label} ", style="dim")
        result.append("▓" * filled, style=color)
        result.append("░" * (8 - filled), style="dim")
        result.append(f" {n}  ", style=color)
    return result


def _count_bar(value: float, max_val: float = 100.0) -> Text:
    """Generic filled-bar for percentages."""
    width = 10
    filled = min(int(width * value / max_val), width)
    color = (
        "green"
        if filled < width * 0.6
        else "yellow" if filled < width * 0.85 else "red"
    )
    t = Text()
    t.append("▓" * filled, style=color)
    t.append("░" * (width - filled), style="dim")
    return t


# ---------------------------------------------------------------------------
# State accessors (return safe defaults when keys are absent)
# ---------------------------------------------------------------------------

SAFE = 0.0
STR_SAFE = ""


def _agents(state: dict) -> list[dict]:
    return state.get("agents", [])


def _top_agent(state: dict) -> str | None:
    agents = _agents(state.get("agent_registry", {}))
    if not agents:
        return None
    return max(agents, key=lambda a: a.get("contribution_score", 0)).get("agent_id")


def _no_data_table(title: str, cols: list[tuple[str, str]]) -> Table:
    t = Table(box=None, show_header=False, padding=(0, 1))
    for label, _ in cols:
        t.add_column(label, style="bold dim")
    t.add_row(*["—"] * len(cols))
    return t


# ---------------------------------------------------------------------------
# Renderable builders
# ---------------------------------------------------------------------------


def _build_top_zone(state: dict) -> Panel:
    """TOP ZONE (50%) — IMPROVEMENT PANEL."""
    bench = state.get("benchmark_state", {})

    current_score: float = bench.get("current_score", 0.0)
    delta: float = bench.get("delta", 0.0)
    rolling_avg: float = bench.get("rolling_average", 0.0)
    regression_count: int = bench.get("regression_count", 0)
    confidence: str = bench.get("improvement_confidence", "low")
    trend: list[float] = bench.get("improvement_trend", [])
    freshness: int = bench.get("benchmark_freshness_seconds", 0)

    conf_color = CONFidence_COLORS.get(confidence, "dim")
    delta_str = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
    delta_color = _delta_color(delta)

    # Header row
    score_line = Text()
    score_line.append(f"BENCHMARK SCORE  ", style="bold dim")
    score_line.append(f"{current_score:.1f}", style="bold bright_white")
    score_line.append(f"  ", style="dim")
    score_line.append(f"({delta_str})", style=delta_color)

    trend_bar = _mini_trend_bar(trend, rolling_avg)

    conf_badge_style = f"bold {conf_color}"
    confidence_label = confidence.upper().replace("-", " ")

    inner = Table(box=None, show_header=False, padding=(0, 2))
    inner.add_column()
    inner.add_row(score_line)
    inner.add_row(
        Text(
            f"Rolling Avg: {rolling_avg:.2f}    "
            f"Regressions: {regression_count}    "
            f"Benchmark freshness: {freshness}s ago",
            style="dim",
        )
    )
    inner.add_row(
        Text(
            f"Confidence: ",
            style="dim",
        )
        + Text(
            f"[{conf_badge_style}]{confidence_label}[/{conf_badge_style}]",
            style=conf_color,
        )
    )
    inner.add_row(Text("Trend (last 10): ", style="dim") + trend_bar)

    return Panel(
        inner,
        title="  IMPROVEMENT  ",
        border_style="bright_blue",
        padding=(0, 1),
    )


def _build_agent_registry(state: dict) -> Panel:
    """LEFT MIDDLE (55%) — AGENT REGISTRY."""
    agents_state = state.get("agent_registry", {})
    agents_list: list[dict] = agents_state.get("agents", [])
    top_id = _top_agent(state)

    # Sort by contribution_score desc
    sorted_agents = sorted(
        agents_list,
        key=lambda a: a.get("contribution_score", 0),
        reverse=True,
    )

    t = Table(
        box=None,
        show_header=True,
        header_style="bold dim",
        padding=(0, 1),
    )
    t.add_column("AGENT", style="bold cyan", width=18)
    t.add_column("SCORE", justify="center", width=6)
    t.add_column("STATUS", style="dim", width=10)

    max_show = 8
    for i, agent in enumerate(sorted_agents[:max_show]):
        name: str = agent.get("agent_id", "?")[:18]
        score: float = agent.get("contribution_score", 0)
        noise: float = agent.get("noise_score", 0)
        delta_score: float = agent.get("delta_contribution", 0)

        # Status indicators
        indicators = ""
        if agent.get("agent_id") == top_id:
            indicators = "★"
        elif noise > 0.3:
            indicators = "⚠"
        elif delta_score < -0.05:
            indicators = "▼"
        elif delta_score > 0.05:
            indicators = "▲"

        score_str = f"{score:.0f}"
        score_color = _score_color(score)

        row_style = "" if i % 2 == 0 else "dim"
        t.add_row(
            Text(f"{name} {indicators}", style=row_style),
            Text(score_str, style=score_color),
            Text(indicators, style=row_style),
        )

    overflow = len(sorted_agents) - max_show
    if overflow > 0:
        t.add_row(Text(f"...and {overflow} more", style="dim"), "", "")

    if not sorted_agents:
        t.add_row(Text("waiting for agents...", style="dim"), "", "")

    return Panel(
        t,
        title="  AGENT REGISTRY  ",
        border_style="bright_blue",
        padding=(0, 1),
    )


def _build_routing_panel(state: dict) -> Panel:
    """ROUTING mini-panel (part of right-middle cluster)."""
    rout = state.get("routing_state", {})

    claude_pct: float = rout.get("workload_split_pct", {}).get("claude", 0.0)
    minimax_pct: float = rout.get("workload_split_pct", {}).get("minimax", 0.0)
    escalation_count: int = rout.get("escalation_count", 0)
    bad_routing: int = rout.get("bad_routing_incidents", 0)
    claude_overuse: bool = rout.get("claude_overuse", False)

    bar = _split_bar(claude_pct, minimax_pct)

    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column(style="bold dim", width=10)
    t.add_column()

    t.add_row("Claude", f"{claude_pct * 100:.0f}%")
    t.add_row("MiniMax", f"{minimax_pct * 100:.0f}%")
    t.add_row("Split", str(bar))
    t.add_row("Escalations", str(escalation_count))
    t.add_row("Bad routing", str(bad_routing))

    if claude_overuse:
        t.add_row("", Text("  [!] Claude overuse", style="red bold"))

    return Panel(t, title="  ROUTING  ", border_style="bright_magenta", padding=(0, 1))


def _build_memory_panel(state: dict) -> Panel:
    """MEMORY mini-panel."""
    mem = state.get("memory_state", {})

    hit_rate: float = mem.get("retrieval_hit_rate", 0.0)
    usefulness: float = mem.get("usefulness_score", 0.0)
    noise: float = mem.get("noise_score", 0.0)

    noise_label, noise_color = _noise_label(noise)
    hit_bar = _count_bar(hit_rate, 1.0)

    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column(style="bold dim", width=12)
    t.add_column()
    t.add_row("Hit Rate", f"{hit_rate * 100:.0f}%  {hit_bar}")
    t.add_row("Usefulness", f"{usefulness * 100:.0f}%")
    t.add_row(
        "Noise",
        Text(f"{noise * 100:.0f}%  [{noise_color}]{noise_label}[/{noise_color}]"),
    )

    return Panel(t, title="  MEMORY  ", border_style="bright_magenta", padding=(0, 1))


def _build_verification_panel(state: dict) -> Panel:
    """VERIFICATION mini-panel."""
    ver = state.get("verification_state", {})

    coverage: float = ver.get("verification_coverage", 0.0)
    error_catch: float = ver.get("error_catch_rate", 0.0)
    hallucination: float = ver.get("hallucination_catch_rate", 0.0)

    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column(style="bold dim", width=16)
    t.add_column()
    t.add_row("Coverage", f"{coverage * 100:.0f}%")
    t.add_row("Error catch", f"{error_catch * 100:.0f}%")
    t.add_row("Hallucination catch", f"{hallucination * 100:.0f}%")

    return Panel(
        t, title="  VERIFICATION  ", border_style="bright_magenta", padding=(0, 1)
    )


def _build_diagnostics_cluster(state: dict) -> Table:
    """MIDDLE ZONE (30%) — Two-column diagnostics cluster."""
    left = _build_agent_registry(state)

    right_stack = Table(box=None, padding=0)
    right_stack.add_column()
    right_stack.add_row(_build_routing_panel(state))
    right_stack.add_row(_build_memory_panel(state))
    right_stack.add_row(_build_verification_panel(state))

    row = Table(box=None, padding=0)
    row.add_column(ratio=55)
    row.add_column(ratio=45)
    row.add_row(left, right_stack)
    return row


def _build_changelog_panel(state: dict) -> Panel:
    """LEFT BOTTOM — CHANGELOG."""
    changelog = state.get("changelog", {})
    entries: list[dict] = changelog.get("entries", [])

    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column()

    STATUS_COLORS: dict[str, str] = {
        "CONF": "green",
        "REV": "yellow",
        "SPEC": "dim",
        "REJ": "red",
        "applied": "green",
        "pending": "yellow",
        "reverted": "red",
        "discarded": "red dim",
    }

    for entry in entries[-4:]:
        desc: str = entry.get("description", "?")[:30]
        status: str = entry.get("status", "")[:4].upper()
        status_color = STATUS_COLORS.get(status, "dim")
        entry_type: str = entry.get("type", "")[:8]

        row_text = Text()
        row_text.append("● ", style="dim")
        row_text.append(f"{desc}", style="white")
        row_text.append("  ", style="dim")
        row_text.append(
            f"[{status_color}]{status}[/{status_color}]", style=status_color
        )
        t.add_row(row_text)

    if not entries:
        t.add_row(Text("no entries yet", style="dim"))

    return Panel(
        t,
        title="  CHANGELOG  ",
        border_style="bright_green",
        padding=(0, 1),
    )


def _build_learning_pipeline_panel(state: dict) -> Panel:
    """CENTER BOTTOM — LEARNING PIPELINE."""
    pipeline = state.get("learning_pipeline", {})

    # Map shorthand to full keys
    key_map = {
        "generated": "generated",
        "validated": "validated",
        "promoted": "promoted",
        "rejected": "rejected",
        "disproven": "disproven",
        "pending": "pending",
    }
    counts = {k: pipeline.get(k, 0) for k in key_map.values()}

    bar = _pipeline_bar(counts)

    inner = Table(box=None, show_header=False, padding=(0, 1))
    inner.add_column()
    inner.add_row(Text("GEN VAL PRO REJ DIS PEN", style="bold dim"))
    inner.add_row(bar)
    inner.add_row(
        Text(
            f"  gen={counts['generated']}  "
            f"val={counts['validated']}  "
            f"pro={counts['promoted']}  "
            f"rej={counts['rejected']}  "
            f"dis={counts['disproven']}  "
            f"pen={counts['pending']}",
            style="dim",
        )
    )

    return Panel(
        inner,
        title="  LEARNING PIPELINE  ",
        border_style="bright_yellow",
        padding=(0, 1),
    )


def _build_system_health_panel(state: dict) -> Panel:
    """RIGHT BOTTOM — SYSTEM HEALTH."""
    health = state.get("system_health", {})

    overall_state: str = health.get("overall_state", "—")
    prompt_health: str = health.get("prompt_health", "—")
    regression_risk: float = health.get("regression_risk", 0.0)
    token_budget_pct: float = health.get("token_budget_pct", 0.0)

    state_color = _overall_state_color(overall_state)

    state_label = f"[{state_color}]{overall_state.upper()}[/{state_color}]"
    if overall_state not in ("normal", "—"):
        state_label = (
            f"[bold {state_color}]{overall_state.upper()}[/bold {state_color}]"
        )

    token_bar = _count_bar(token_budget_pct, 100.0)

    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column(style="bold dim", width=14)
    t.add_column()
    t.add_row("State", Text(state_label, style=state_color))
    t.add_row("Prompt health", prompt_health)
    t.add_row("Regression risk", f"{regression_risk * 100:.0f}%")
    t.add_row("Token budget", f"{token_budget_pct:.0f}%  {token_bar}")

    return Panel(
        t,
        title="  SYSTEM HEALTH  ",
        border_style="bright_red",
        padding=(0, 1),
    )


def _build_bottom_zone(state: dict) -> Table:
    """BOTTOM ZONE (20%) — Three equal columns."""
    left = _build_changelog_panel(state)
    center = _build_learning_pipeline_panel(state)
    right = _build_system_health_panel(state)

    row = Table(box=None, padding=0)
    row.add_column(ratio=1)
    row.add_column(ratio=1)
    row.add_column(ratio=1)
    row.add_row(left, center, right)
    return row


def _build_header(state: dict) -> Panel:
    """Header bar: timestamp + overall_state."""
    health = state.get("system_health", {})
    overall_state: str = health.get("overall_state", "—")
    state_color = _overall_state_color(overall_state)

    header_text = Text()
    header_text.append("MINIMAX HUD v2", style="bold deep_pink3")
    header_text.append("  ", style="dim")
    header_text.append(datetime.now().strftime("%H:%M:%S"), style="dim")
    header_text.append("  ·  ", style="dim")
    header_text.append(
        f"[{state_color}]{overall_state}[/{state_color}]", style=state_color
    )

    return Panel(
        header_text,
        style="bold white on black",
        border_style="black",
        padding=(0, 1),
    )


def build_renderable(state: dict) -> RichGroup:
    """
    Build the complete HUD RichGroup from a single state snapshot.

    Separates data preparation from rendering as required.
    """
    return RichGroup(
        _build_header(state),
        _build_top_zone(state),
        _build_diagnostics_cluster(state),
        _build_bottom_zone(state),
    )


# ---------------------------------------------------------------------------
# get_renderable callable — drives Live's auto-refresh thread
# ---------------------------------------------------------------------------


def hud_getter():
    """
    Called by rich.Live's background refresh thread each time it polls.

    Returns a fresh RichGroup per call. Never blocks — reads state and returns
    immediately so the refresh thread is never starved.
    """
    state = get_all_state()
    # Map filename keys (from state_engine) to logical keys (expected by render functions)
    _FILE_TO_LOGICAL: dict[str, str] = {
        "agent_registry.json": "agent_registry",
        "benchmark_state.json": "benchmark_state",
        "learning_pipeline.json": "learning_pipeline",
        "memory_state.json": "memory_state",
        "system_health.json": "system_health",
        "changelog.json": "changelog",
        "routing_state.json": "routing_state",
        "verification_state.json": "verification_state",
    }
    state = {_FILE_TO_LOGICAL.get(k, k): v for k, v in state.items()}
    return build_renderable(state)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    console.print(
        "[bold deep_pink3]Starting HUD v2...[/]  screen=False, refresh=0.2 Hz"
    )
    time.sleep(1)
    try:
        with Live(
            get_renderable=hud_getter,
            console=console,
            screen=False,  # in-place ANSI updates — no new terminal
            refresh_per_second=0.2,  # 5-second refresh cadence
            transient=False,  # don't clear on exit — let last frame linger
        ) as live:
            # Live drives the refresh thread automatically. Keep the main
            # thread alive until the user sends KeyboardInterrupt (Ctrl+C).
            while live.is_started:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[bold green]HUD closed.[/]\n")


if __name__ == "__main__":
    main()
