---
name: minimax-workflow-optimizer
description: Meta-skill for tracked MiniMax-M2.7 runs. Use when Opus should run a development task through the full self-improving loop: route to MiniMax workers, update request/logging state, extract learnings, refresh the stockpile, and keep the HUD synchronized.
triggers:
  - "/optimize"
  - "run the workflow"
  - "use the self-improving system"
  - "start a tracked session"
  - "apply learnings"
  - "run the loop"
auto_activate: false
compatibility: [file-read, file-write, agent-spawn]
---

# minimax-workflow-optimizer

The meta-skill that runs development tasks through a self-improving loop:
Run -> Log -> Learn -> Improve. Every session makes the next one smarter.

## The Loop

```text
Task arrives
    ↓
[1] Read learnings from _learnings.md
    ↓
[2] Read request budget from _token_log.md
    ↓
[3] Pre-read all files ONCE
    ↓
[4] Group by file - 1 worker per file
    ↓
[5] Spawn MiniMax-M2.7 workers
    ↓
[6] Verify results
    ↓
[7] Post-task loop updates logs, learnings, stockpile, state engine, HUD
    ↓
Next task arrives -> smarter
```

## Step 1 — Read Learnings (MANDATORY)

Read `C:\Users\Charlie\.claude\skills\_learnings.md`
Apply these rules:
- Never repeat a mistake recorded in `_learnings.md`
- Use techniques that worked in past sessions
- If a past session failed with X approach, try Y instead

## Step 2 — Request Budget Check (MANDATORY)

Read `C:\Users\Charlie\.claude\skills\_token_log.md`

Canonical budget:
- `15,000` MiniMax model requests per 5-hour window
- Requests are the only canonical budget unit
- Efficiency token estimates are secondary diagnostics only

When exact request totals are unavailable, use the tracked lower-bound request
counts produced by the post-task loop and avoid pretending token estimates are the budget.

## Step 3 — Pre-Read Files ONCE (MANDATORY)

Read every file that will be edited ONCE.
Paste full content into worker prompts.
NEVER let a worker re-read a file you've already read.

## Step 4 — Group by File

1 worker per file. Never 2 workers on the same file.

| Files to edit | Target workers |
|--------------|----------------|
| 1-3 files | 1 worker |
| 4-7 files | 2-3 workers |
| 8+ files | 3-5 workers (cap) |

## Step 5 — Dispatch with Tracking

Spawn all workers simultaneously and explicitly pin:

```js
Agent(worker, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "<task + file content + rules>"
})
```

Track:
- Worker name
- Files assigned
- Verification status
- Whether the route stayed on MiniMax

## Step 6 — Verify and State-Produce

After all workers complete:
- `python -m py_compile [file]` for every edited file
- Report pass/fail per file
- Keep enough structured detail in your final response for the post-task loop to write state cleanly

## Step 7 — Real Post-Task Loop

The Stop hook `C:\Users\Charlie\.claude\scripts\hooks\minimax-post-task-loop.py`
is the real mechanism that runs after each response. It:

1. Logs task activity to `_token_log.md`
2. Extracts a short learning into `_learnings.md`
3. Updates `_stockpile.md`
4. Emits task/routing/learning events
5. Updates state via `state_engine.py`
6. Refreshes HUD-visible metrics

## Anti-Patterns to Never Repeat

- Never spawn more than 5 workers simultaneously
- Never have 2 workers edit the same file
- Never let workers re-read files you already read
- Never skip verification before completion
- Never let external/plugin agents become the default path for work the MiniMax system already covers

## Output Contract

Keep the end-of-task summary compact and structured so Opus and the post-task loop
can recover:
- task summary
- files touched
- verification run
- blockers or unresolved items
