# MiniMax HUD

MiniMax-first orchestration for Claude Code, with Opus as controller, MiniMax workers as the default execution path, a real post-task learning loop, and a live HUD that reflects actual system activity.

This repo mirrors the active `C:\Users\Charlie\.claude` system and is now cleaned of runtime/session artifacts. GitHub tracks the system, not the local noise.

---

## Current Operating Model

```text
User input
  -> Opus controller
  -> internal MiniMax routing
  -> MiniMax workers do execution by default
  -> post-task loop logs, learns, updates stockpile/state
  -> HUD reflects real routing + learning activity
```

Primary path:
1. MiniMax delegation system
2. Internal skills
3. External/plugin/ECC agents only as fallback

This is the main normalization that was completed. The system is no longer documented or wired as ECC-first.

---

## What Was Corrected

### 1. Entry point routing was normalized

`settings.json` now injects a MiniMax-first routing policy at `UserPromptSubmit`:
- Opus follows `CLAUDE.md`
- Internal MiniMax skills are preferred first
- Worker execution is explicitly pinned to `MiniMax-M2.7` where supported
- External/plugin/ECC routes are fallback-only
- Workers report back to Opus

### 2. The post-task loop is real now

The `Stop` hook runs:

```bash
python "$HOME/.claude/scripts/hooks/minimax-post-task-loop.py"
```

After every task it:
1. logs request activity
2. extracts a learning
3. updates stockpile/session counts
4. updates state JSON
5. emits events so the HUD reflects the run

### 3. MiniMax workflows are real skills

The system now includes proper skill folders:
- `skills/minimax-delegation/SKILL.md`
- `skills/minimax-dev-workflow/SKILL.md`
- `skills/minimax-workflow-optimizer/SKILL.md`

Legacy markdown files remain only as compatibility shims where needed.

### 4. Controller identity is unified

The system now documents one controller:
- Opus is the sole controller
- MiniMax is the default execution layer
- Sonnet is not the orchestrator

### 5. Budget language is normalized

Canonical budget unit:
- `15,000 model requests / 5 hours`

Requests are the canonical planning unit.
Token estimates are secondary diagnostics only.

---

## Architecture

```text
Opus Max
  - holds context
  - reads learnings, stockpile, state, routing rules
  - chooses skills and worker layout
  - synthesizes final output

MiniMax-M2.7 workers
  - default execution engine
  - code changes
  - reviews
  - bounded research
  - delegated subtasks

State + learning loop
  - _token_log.md
  - _learnings.md
  - _stockpile.md
  - state/*.json
  - event stream

HUD
  - reads state
  - shows routing, learning, health, request budget
```

Key runtime files:
- `CLAUDE.md`
- `settings.json`
- `hud.py`
- `scripts/hooks/minimax-post-task-loop.py`
- `skills/_learnings.md`
- `skills/_token_log.md`
- `agents/_stockpile.md`
- `state/routing_state.json`
- `state/learning_pipeline.json`
- `state/system_health.json`

---

## Live State Snapshot

Current mirrored state at the time of this update:
- Routing split: `MiniMax 66.7%`, `Claude 33.3%`
- Learning pipeline: `generated 1`, `validated 1`
- System health: `benchmark-confirmed`
- Prompt health: `stable`
- Routing confidence: `1.0`
- Budget usage tracked in state: `1%`

These numbers come from the mirrored `state/*.json` files and should be treated as a snapshot, not a permanent constant.

---

## Agent Policy

### Core rules

1. Opus orchestrates. MiniMax executes.
2. Pre-read efficiently. Avoid redundant file reads when Opus can provide the needed context.
3. Prefer internal MiniMax skills before external/plugin agents.
4. Log and learn after every task.
5. Verify changes with real evidence before claiming success.

### Updated parallelism policy

Older versions of this system said:
- never 2 agents on the same file
- keep agent count very low

That is no longer the recommended rule.

New policy:
- use as many MiniMax workers as materially improve throughput
- parallelize aggressively when the task benefits from it
- multiple agents may contribute to the same file if the work is decomposed clearly
- Opus must still control ownership, merge order, and final integration

Good same-file parallel patterns:
- one agent audits, one agent patches, one agent verifies
- one agent handles logic, one agent handles tests, one agent handles docs
- one agent drafts a refactor plan while another prepares a narrow code change

Bad parallel patterns:
- duplicate agents doing the same edit blindly
- conflicting writes with no integration plan
- workers re-reading and rediscovering the same context instead of using Opus-prepared inputs

The limiting factor is not agent count by itself. The limiting factors are overlap, merge friction, and wasted context.

---

## Skills

| Skill | Purpose |
|------|---------|
| `minimax-delegation` | Default MiniMax-first delegation path |
| `minimax-dev-workflow` | Non-trivial development workflow and execution orchestration |
| `minimax-workflow-optimizer` | Self-improving workflow tuning and budget/routing optimization |
| `skill-builder` | Skill authoring and extension |
| `_learnings.md` | Persistent system learnings |
| `_token_log.md` | Request tracking and session logging |

---

## Agents

| Agent | Role |
|------|------|
| `code-fix-agent` | Fixes implementation issues |
| `code-review-agent` | Performs severity-based review |
| `learning-agent` | Extracts learnings after tasks |
| `token-budget-agent` | Tracks request budget consumption |
| `git-commit-agent` | Commits and pushes changes |
| `agent-stockpile-manager` | Maintains stockpile quality and coverage |
| `state-producer-agent` | Produces state/HUD-facing updates |

---

## HUD

`hud.py` now reflects the normalized system instead of the older token-confused model.

It is intended to surface:
- request budget status
- routing split
- agent activity
- learning pipeline state
- system health
- benchmark/readiness signals

The HUD is only as good as the post-task loop and state files. That loop is now an actual hook, not just a described concept.

---

## Repo Hygiene

This repo is intentionally kept free of runtime slop.

Ignored artifacts now include:
- top-level transcript/session `*.jsonl`
- `subagents/` runtime output
- `tool-results/`
- `.claude/commands/`
- `__pycache__/`
- `.coverage-thresholds.json`

GitHub should represent the system definition and durable state, not transient local execution debris.

---

## Working Assumptions

These are the current assumptions behind the system:
- Opus remains the controller
- MiniMax remains the default worker model
- external/plugin agents are optional tools, not the main path
- routing should optimize for execution volume and useful delegation, not minimalism for its own sake
- “efficiency” means higher useful throughput, not just fewer agents

---

## Recommended Next Plan

This is the current plan based on the audit and the fixes already completed.

### Phase A: Parallelism normalization
- Update `CLAUDE.md` and skill prompts to remove the old “never 2 agents on the same file” rule.
- Replace low-parallelism wording like “target 2-5 workers” with throughput-based guidance.
- Define allowed same-file collaboration patterns and integration responsibilities for Opus.

### Phase B: Skill competitiveness
- Confirm `minimax-dev-workflow` and `minimax-workflow-optimizer` are being selected often enough in real sessions.
- Tune trigger phrases and auto-activation so MiniMax skills win against installed marketplace skills when appropriate.
- Add telemetry or log summaries that make skill selection drift obvious.

### Phase C: Worker model enforcement
- Audit every spawning/delegation prompt for explicit `MiniMax-M2.7` model pinning.
- Where model pinning is unavailable, document the enforced routing fallback behavior clearly.
- Add a verification check that flags sessions where Claude workers were used when MiniMax should have been used.

### Phase D: Stronger post-task loop outputs
- Extend the hook output so each completed task leaves a clearer routing record.
- Surface stockpile changes directly in the HUD.
- Add a small session summary artifact or panel that shows what the loop learned from the last task.

### Phase E: Better throughput controls
- Add a delegation planner that decides worker count based on task breadth, not a hard cap.
- Introduce task slicing patterns for same-file parallel work.
- Add guardrails for merge conflicts, duplicated work, and stale context.

### Phase F: Validation
- Run real tasks and confirm MiniMax skill usage climbs over time.
- Verify the HUD changes meaningfully after each session.
- Confirm ECC/plugin routes remain fallback-only in practice, not just in docs.

---

## If You’re Operating This System

Think of it this way:
- Opus should think broadly and integrate
- MiniMax should do the bulk of the work
- the loop should learn after every task
- the HUD should tell the truth
- GitHub should stay clean

That is the current intended system behavior.
