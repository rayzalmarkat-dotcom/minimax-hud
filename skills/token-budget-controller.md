---
name: token-budget-controller
description: >
  Tracks and controls MiniMax request budget across sessions. Use whenever starting a large task,
  after every session to log usage, or when budget usage needs to be monitored.
  TRIGGERS: "check request usage", "how much budget left", "request budget",
  "optimize minimax usage", "/token-budget", "are we burning too fast".
  Also auto-triggers when session usage exceeds 50% of daily budget.
compatibility: [file-read, file-write]
---

# Request Budget Controller

Tracks rolling request usage per session. Warns at budget thresholds.
Adjusts agent parallelism dynamically to hit the 50-90% efficiency sweet spot.

## Daily Budget Context

- Canonical limit: 15,000 MiniMax model requests per 5-hour window
- Target usage: 50-90% (7,500–13,500 requests per cycle) when request counts are observable
- Minimum viable session: 20% (3,000 tracked requests) as a budget reference only
- Maximum burn rate: 90%+ risks running out mid-task

## How It Works

Request usage is the canonical budget unit.
Tracked request counts come from the MiniMax post-task loop and any explicit worker/request notifications that Claude Code exposes.
Estimated efficiency tokens may still be logged as secondary diagnostics, but they do not define budget.

## Request Log File

Location: C:\Users\Charlie\.claude\skills\_token_log.md

Format:
```
## Session: YYYY-MM-DD HH:MM

Task: [summary]
Tracked requests: [count]
Workflow activations: [skills or workers]
Efficiency tokens (optional): [estimate]
```

## Thresholds and Actions

| Usage | Level | Action |
|-------|-------|--------|
| 0-20% | Idle | Spawn more agents, take on bigger tasks |
| 20-50% | Light | Normal dispatch, watch burn rate |
| 50-75% | Optimal | Warn user, suggest ending soon |
| 75-90% | Heavy | Suggest wrapping up non-critical agents |
| 90%+ | Critical | Stop spawning new agents, finish current ones |

## Burn Rate Calculation

Burn rate = rolling_total_requests / session_elapsed_seconds
Requests per minute = burn_rate * 60

Estimate time to empty:
```
remaining_budget = 15000 - rolling_total
time_remaining = remaining_budget / burn_rate_seconds
```

## Adaptive Parallelism

Adjust agent count based on remaining budget and burn rate:

- Budget >75%, burn_rate >200 requests/sec: reduce to 1-2 agents
- Budget 50-75%, normal burn: 3-4 agents
- Budget <50%, low burn: 5+ agents (take on more work)

## Session Start

At session start:
1. Read _token_log.md for recent usage patterns
2. Check if today's already has logged sessions
3. Warn if previous sessions used >50% of budget
4. Calculate recommended agent parallelism for this session

## Session End

After every task:
1. Log tracked MiniMax request counts to _token_log.md
2. Calculate total tracked requests
3. Calculate requests per minute burn rate
4. Compare to target (50-90%)
5. Record whether session was under/over target
6. Append learnings to _learnings.md about request efficiency and routing quality

## Warnings Format

When crossing thresholds, report to user:
"[THRESHOLD WARNING] Used X/Y tracked requests (Z%). Burn rate: N requests/min. Est. Y minutes remaining at current rate. [recommendation]"
