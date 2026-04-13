---
name: minimax-dev-workflow
description: Opus-controlled MiniMax-M2.7 development workflow for code review, bug fixes, refactors, tests, audits, and other non-trivial engineering work. Use when execution should default to MiniMax workers with pre-read-once discipline, grouped dispatch, verification, and a real post-task loop.
triggers:
  - "review my code"
  - "fix the bugs"
  - "refactor"
  - "audit"
  - "add tests"
  - "full code review"
  - "use minimax workflow"
  - "run minimax workflow"
auto_activate: true
compatibility: [file-read, file-write, agent-spawn]
---

# minimax-dev-workflow

Self-improving MiniMax development workflow for code review, bug fixes, refactors,
and multi-step development tasks. Reads `_learnings.md` before every task.
Writes learnings after every session. Opus orchestrates; MiniMax-M2.7 workers execute.

## Core Principle: Read Learnings First

**MANDATORY**: Before every task, read `C:\Users\Charlie\.claude\skills\_learnings.md`
Apply any relevant learnings from past sessions. Never repeat the same mistake twice.

## Core Principle: Pre-Read Once

Read each source file EXACTLY ONCE. Paste file content directly into worker prompts.
Never let a worker re-read a file you've already read this session.

## When to Use

- Code review of a project or directory
- Fixing bugs across multiple files
- Refactoring a codebase
- Adding test coverage
- Security audits
- Any multi-step development task

## When NOT to Use

- Single-file, single-fix: use `minimax-delegation` for one MiniMax worker
- Planning-only tasks where Opus can answer without worker execution

## Workflow

### Step 1 — Read Learnings (MANDATORY)

Read `C:\Users\Charlie\.claude\skills\_learnings.md`
Apply these rules to every decision:
- GROUP all fixes for the same file into ONE worker
- PRE-READ files once, paste content into prompts
- TARGET: 2-5 workers per project regardless of issue count
- LOG session metrics through the post-task loop

### Step 2 — Explore Files (Opus does this)

Read ALL relevant files ONCE. Build an issue map:
- What files exist and what are their logical units?
- What issues need addressing in each file?
- Are there CLAUDE.md or project rules to reference?

Do NOT spawn workers yet.

### Step 3 — Plan Dispatch

Group by file: 1 worker per file. Never 2 workers on the same file.

| Grouping | Target workers |
|----------|----------------|
| 1-3 related files | 1 worker |
| 4-10 files | 2-3 workers |
| 10+ files | 4-5 workers (cap) |

### Step 4 — Pre-Read Files (Opus does this)

Paste full file content into each worker prompt. No re-reads.

For files >5k tokens: split into logical sections with clear markers.

### Step 5 — Spawn Parallel MiniMax Workers

Use `minimax-delegation` patterns. Spawn ALL workers simultaneously and explicitly pin:

```js
Agent(workerA, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "<task + file content + rules>"
})
```

If the current build does not support the `model` field, keep the route internal to the MiniMax system and do not silently substitute marketplace/plugin workers.

### Step 6 — Verify and Synthesize

When workers complete:
1. Confirm syntax: `python -m py_compile` on every edited file
2. Report what was done per file
3. Note any issues workers couldn't resolve

### Step 7 — Post-Task Loop (MANDATORY)

The Stop hook at `C:\Users\Charlie\.claude\scripts\hooks\minimax-post-task-loop.py`
runs after the response and updates:
- `_token_log.md`
- `_learnings.md`
- `_stockpile.md`
- `state_engine.py` / `events.py`

When you are inside a tracked run, still treat the loop as mandatory and make
sure your final summary leaves enough detail for the hook/state pipeline to be useful.

## Worker Prompt Template

````
You are a MiniMax-M2.7 development worker.

## Controller
Opus Max is orchestrating this task. Report back to Opus.

## Context
[Paste relevant learnings from _learnings.md here]

## Project Rules
[Paste CLAUDE.md or relevant project rules]

## Your Task
[Specific task description]

## Files to Edit

### File: [path]
```[language]
[paste full file content here]
```

## Issues to Address

Prioritized by severity. Address all CRITICAL and HIGH first.
1. [CRITICAL] [issue + exact fix]
2. [HIGH] [issue + exact fix]
3. [MEDIUM] [issue + fix if straightforward]

## Rules
- Do not re-read files already provided
- Keep changes scoped to your assigned files
- After changes: `python -m py_compile [file]`
- If you cannot complete something: describe why, continue to the next issue

## Verify Before Finishing
Run `python -m py_compile [file]` for every edited file. Report clean/dirty per file.
````

## Important Rules

1. **No merge conflicts**: 1 worker per file
2. **No redundant reads**: paste content into prompt, worker does not re-read
3. **Max 5 simultaneous workers**: beyond this, runtime overhead exceeds parallelism benefit
4. **Fail gracefully**: note blockers, continue to the next issue
5. **MiniMax is explicit**: use `model: "MiniMax-M2.7"` whenever available

## Output Format

Always end with:

| File | Issues | Status |
|------|--------|--------|
| file_a.py | 3 CRITICAL, 2 HIGH | Done |
| file_b.py | 1 HIGH | Done |
| file_c.py | 1 CRITICAL | Skipped - reason |
