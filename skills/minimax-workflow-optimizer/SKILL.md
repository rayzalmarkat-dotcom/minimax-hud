---
name: minimax-workflow-optimizer
description: Meta-skill for enforcing MiniMax-dominant routing. Use when Opus should drive a task through the full execution loop, maximize MiniMax utilization, track delegation misses, and update routing/state/HUD signals.
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

This meta-skill enforces delegation-first behavior.
Its job is not to reduce worker usage. Its job is to maximize useful MiniMax execution and make routing failures visible.

## Routing Objective

Target steady-state split:
- MiniMax: 90–95%
- Claude/Opus: 5–10%

Desired by category:
- implementation: ~100% MiniMax
- debugging: ~100% MiniMax
- review: ~100% MiniMax
- verification: ~100% MiniMax
- orchestration: Claude
- synthesis: Claude

## Loop

```text
Task arrives
  -> classify task category
  -> read learnings and budget
  -> Opus decomposes briefly
  -> delegate to MiniMax immediately if delegatable
  -> run execution and verification on MiniMax
  -> integrate results in Opus
  -> post-task loop updates routing, miss rate, stockpile, state, HUD
```

## Required Behavior

### 1. Classify The Task

Every tracked task should be treated as one of:
- implementation
- debugging
- review
- verification
- orchestration
- synthesis

### 2. Prefer Delegation Unless Strictly Unnecessary

If the task falls into implementation, debugging, review, verification, or iteration:
- delegate
- pin `MiniMax-M2.7`
- avoid silent Claude execution

### 3. Track Leakage

If Claude executes work that should have been delegated:
- count it as a delegation miss
- surface it in routing state
- lower routing confidence

### 4. Parallelism Is A Throughput Tool

Do not enforce small fixed worker counts.
Use the worker count that makes the task move fastest without uncontrolled overlap.

Same-file collaboration is allowed when:
- responsibilities are explicit
- merge order is clear
- Opus handles final integration

## Dispatch Standard

Always pin workers explicitly:

```js
Agent(worker, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "<task + category + ownership + constraints>"
})
```

If explicit model pinning is unavailable, keep routing logic MiniMax-first and make fallback visible.

## What To Optimize For

Optimize for:
- higher MiniMax utilization
- lower delegation miss rate
- lower Claude execution leak
- clearer category-level routing
- stronger post-task observability

Do not optimize for:
- fewer workers for their own sake
- local Claude execution of delegatable work
- conservative routing that drifts away from MiniMax

## Anti-Patterns To Remove

- keeping implementation local to Claude
- keeping debugging loops local to Claude
- fixed small-worker caps
- “never 2 workers on the same file”
- vague fallback behavior
- hidden Claude execution for delegatable tasks

## Output Contract

End tracked runs with enough structure for the state loop to recover:
- task category
- whether the task was delegatable
- whether MiniMax handled execution
- files touched
- verification status
- blockers
