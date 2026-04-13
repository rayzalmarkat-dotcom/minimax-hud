---
name: minimax-delegation
description: Route executable work from Opus to MiniMax-M2.7 workers. Default execution path for internal coding, writing, research, and file-operation tasks when MiniMax should do the work and report back to Opus.
origin: superpowers
auto_activate: true
triggers:
  - "use minimax"
  - "delegate to minimax"
  - "run the minimax system"
  - "implement this"
  - "fix this"
  - "build this"
  - "do this"
---

# MiniMax Agent Delegation

Spawn MiniMax-M2.7 workers to execute tasks while Opus stays in controller/synthesis mode.

## When to Activate

- Any task requiring execution (code, write, research, file operations)
- User asks to "do" something
- Task could be split into parallel sub-tasks
- A skill matches the task and MiniMax should execute using that skill's guidance
- Default routing should stay here before considering marketplace/plugin agents

## How to Spawn an Agent

Use the Agent tool and explicitly pin the worker model to `MiniMax-M2.7` whenever the current build supports model selection.

```
Agent(tool, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "<task description + any relevant context>"
})
```

If the Agent tool in the current Claude build does not expose `model`, routing logic must still treat MiniMax as required and must not silently fall back to Claude/plugin workers.

## Prompt Template for Spawning

```
You are a MiniMax-M2.7 execution worker.

<Task description from Opus>

<Any skill-specific rules/goals if applicable>

Return your findings/results to the orchestrator (Opus Max).
```

## Spawn Patterns

### Single Agent
For straightforward single-task execution.

```
Agent(task_agent, {
  subagent_type: "general-purpose",
  model: "MiniMax-M2.7",
  prompt: "Fix the bug in file X. The issue is..."
})
```

### Parallel Agents
For independent sub-tasks that can run simultaneously.

```
Agent(agent_A, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Task A" })
Agent(agent_B, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Task B" })
Agent(agent_C, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Task C" })
// Wait for all → synthesize
```

### Sequential Agents
For chained tasks where output feeds into next.

```
Agent(first, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Step 1" })
// Take output → feed into step 2
Agent(second, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Step 2, based on: " + first.output })
```

### Hybrid
For complex multi-phase workflows.

```
// Phase 1: Parallel research
Agent(r1, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Research aspect A" })
Agent(r2, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Research aspect B" })

// Phase 2: Synthesize findings (Opus)
// Phase 3: Parallel execution
Agent(e1, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Execute based on research A" })
Agent(e2, { subagent_type: "general-purpose", model: "MiniMax-M2.7", prompt: "Execute based on research B" })
```

## Decision: Single vs Parallel vs Sequential

| Task Structure | Pattern |
|---------------|---------|
| One independent task | SINGLE |
| 2+ independent sub-tasks | PARALLEL |
| Tasks with dependencies | SEQUENTIAL |
| Complex multi-phase | HYBRID |

**Rule of thumb:** If you can say "X and Y can happen at the same time" → PARALLEL.

## Error Handling for Spawned Agents

```
If agent fails:
  → Retry once with same prompt
  → Still fails → Log failure, report to user
  → Partial failure in parallel → collect outputs from successful agents, report failed ones
```

## Returning Results to User

- **Simple tasks:** MiniMax reports directly (bystander mode)
- **Complex tasks:** Opus synthesizes MiniMax outputs before presenting

Default to direct reporting. Synthesize when:
- Multiple agents ran in parallel
- Results need cross-referencing
- User would benefit from a summary

## Quality Standards for Spawned Agents

Each MiniMax agent should:
- Complete the assigned task fully
- Report clearly what was done and what was found
- Flag any blockers or uncertainties
- Return actionable output (working code, complete text, etc.)

## Examples

```
"Build me a Python script that does X"
→ Spawn single MiniMax agent

"Refactor the auth module and add tests"
→ Sequential: refactor → test

"Research competitor products A, B, and C simultaneously"
→ 3 parallel MiniMax-M2.7 workers, one per competitor

"Build a full user authentication system"
→ Hybrid: parallel workers for components → synthesize → parallel workers for integration
```
