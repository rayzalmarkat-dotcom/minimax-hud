---
name: minimax-dev-workflow
description: Opus-controlled, MiniMax-dominant development workflow for implementation, debugging, review, refactor, testing, verification, and iterative engineering work. Use when execution should move to MiniMax immediately and Opus should stay in orchestration/integration mode.
triggers:
  - "review my code"
  - "fix the bugs"
  - "refactor"
  - "audit"
  - "add tests"
  - "debug this"
  - "verify this"
  - "iterate on this"
  - "run minimax workflow"
auto_activate: true
compatibility: [file-read, file-write, agent-spawn]
---

# minimax-dev-workflow

MiniMax-first development workflow.
Opus should think briefly, prepare context, delegate aggressively, and integrate results.

## Use For

- code writing
- code modification
- debugging
- reviews
- refactors
- tests
- verification
- iterative multi-step engineering work

## Do Not Keep Local To Opus

Do not keep these tasks on Claude just because they look manageable.
If they are executable, they are delegatable by default.

## Workflow

### Step 1 — Read Learnings

Read `C:\Users\Charlie\.claude\skills\_learnings.md` and apply relevant lessons.

### Step 2 — Read Budget + Stockpile

Read:
- `C:\Users\Charlie\.claude\skills\_token_log.md`
- `C:\Users\Charlie\.claude\agents\_stockpile.md`

### Step 3 — Fast Opus Pass

Opus should:
- identify task category
- decompose the work
- prepare worker context
- decide parallel layout

Opus should not take over execution.

### Step 4 — Dispatch Immediately

If the task involves implementation, debugging, review, verification, refactor, or iteration:
- delegate to MiniMax

Always pin workers explicitly:

```js
Agent(workerA, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "<task + context + ownership>"
})
```

If `model` is unavailable in the current build, keep the route on the MiniMax system and do not silently substitute Claude/plugin execution.

### Step 5 — Parallelize Aggressively

Use as many workers as materially improve throughput.
There is no fixed low worker cap in this workflow.

Allowed patterns:
- one worker per area
- multiple workers across the same feature
- same-file collaboration when roles are separated
- audit/patch/verify split
- logic/tests/docs split
- refactor/implementation/regression split

Opus must keep ownership clear and integrate final changes.

### Step 6 — Verification Also Defaults To MiniMax

Verification loops should default to MiniMax workers too.
Opus should review evidence and integrate, not run repetitive verification itself.

### Step 7 — Integrate + Synthesize

When workers complete:
1. collect outputs
2. resolve any integration conflicts
3. summarize results for the user
4. leave enough detail for the post-task loop to log routing and learnings cleanly

### Step 8 — Post-Task Loop

The Stop hook at `C:\Users\Charlie\.claude\scripts\hooks\minimax-post-task-loop.py`
runs after the response and updates:
- `_token_log.md`
- `_learnings.md`
- `_stockpile.md`
- routing state
- HUD-visible metrics

## Worker Prompt Template

````text
You are a MiniMax-M2.7 development worker.

Controller:
Opus Max

Your role:
Execution, iteration, verification, and evidence reporting.

Task:
[specific task]

Context:
[prepared context from Opus]

Ownership:
[what you own, what other workers own, and how to avoid collision]

Rules:
- stay within assigned scope unless Opus explicitly broadens it
- return concrete results and blockers
- include verification evidence where applicable
````

## Non-Negotiables

1. Prefer delegation unless strictly unnecessary
2. Do not impose a small-worker cap by default
3. Same-file collaboration is allowed when decomposed clearly
4. Verification loops are delegatable
5. Explicitly pin `model: "MiniMax-M2.7"` whenever supported
6. Opus integrates; MiniMax executes
