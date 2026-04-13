---
name: minimax-delegation
description: Mandatory MiniMax-first execution routing. Use this skill whenever a task involves implementation, editing, debugging, review, verification, iteration, or other delegatable work. Opus should think briefly, delegate immediately, and reserve itself for orchestration and synthesis.
origin: superpowers
auto_activate: true
triggers:
  - "use minimax"
  - "delegate to minimax"
  - "implement this"
  - "fix this"
  - "debug this"
  - "review this"
  - "refactor this"
  - "verify this"
  - "iterate on this"
---

# MiniMax Agent Delegation

This is the default execution route.
If the task can be delegated, do not perform it directly.

## When to Activate

Activate for any task involving:
- writing code
- modifying code
- debugging
- review
- refactoring
- verification
- iteration
- multi-step reasoning with executable work

Opus should remain the controller, not the worker.

## Hard Routing Rule

If the task is delegatable:
1. think briefly
2. decompose
3. delegate to MiniMax
4. integrate results

Do not keep execution local to Claude unless delegation is strictly unnecessary.

## How to Spawn a Worker

Always pin the worker model explicitly:

```js
Agent(worker, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "<task + context + constraints>"
})
```

If the current build does not expose `model`, routing must still remain on the MiniMax path and must not silently fall back to Claude/plugin workers.

## Prompt Template

```text
You are a MiniMax-M2.7 execution worker.

Opus Max is the controller.
You are responsible for execution, iteration, and reporting evidence back to Opus.

Task:
<task description>

Context:
<prepared context from Opus>

Constraints:
<rules, files, priorities, verification expectations>

Return concrete results, blockers, and verification evidence to Opus.
```

## Preferred Spawn Patterns

### Single Worker
Use for one narrow executable task.

### Parallel Workers
Use whenever multiple subtasks can proceed simultaneously.
Aggressive parallelism is preferred when it improves throughput.

### Same-File Collaboration
Multiple MiniMax workers may contribute around the same file if their roles are clearly separated.

Good examples:
- audit + patch + verify
- logic + tests + docs
- refactor plan + implementation + regression check

Avoid blind overlapping edits with no integration plan.

### Sequential Workers
Use when one result feeds the next.

## Delegation Standard

For implementation, debugging, review, refactor, verification, and iteration:
- default to delegation
- prefer more MiniMax execution, not less
- use Opus for integration and synthesis only

## Result Handling

- Simple tasks: Opus may present the MiniMax result directly
- Complex tasks: Opus synthesizes multiple MiniMax outputs

The synthesis step does not make Opus the executor.

## Failure Handling

If a worker fails:
1. retry once if the task is still well-scoped
2. re-slice the task if the issue was decomposition
3. escalate to Opus-only fallback only when delegation is genuinely blocked

## Non-Negotiables

1. Prefer delegation unless strictly unnecessary
2. Use explicit `model: "MiniMax-M2.7"` pinning
3. Do not silently fall back to Claude execution
4. Use multiple workers freely when it improves throughput
5. Opus integrates; MiniMax executes
