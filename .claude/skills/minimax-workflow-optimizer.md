---
name: minimax-workflow-optimizer
description: >
  The meta-skill for self-improving MiniMax agent sessions. Use for ANY development
  task: code reviews, bug fixes, refactors, audits, test generation.
  TRIGGERS: "/optimize", "run the workflow", "use the self-improving system",
  "start a tracked session", "apply learnings", "run the loop".
  This skill is loaded by minimax-dev-workflow automatically.
  Composes with: minimax-dev-workflow, token-budget-controller, _learnings.md.
compatibility: [file-read, file-write, agent-spawn]
---

# minimax-workflow-optimizer

The meta-skill that runs any development task through a self-improving loop:
Run → Log → Learn → Improve. Every session makes the next one smarter.

## The Loop

```
Task arrives
    ↓
[1] Read learnings from _learnings.md
    ↓
[2] Read token budget from _token_log.md
    ↓
[3] Pre-read all files ONCE (never re-read)
    ↓
[4] Group by file — 1 agent per file
    ↓
[5] Spawn MiniMax agents (track tokens + duration per agent)
    ↓
[6] Agents complete → verify syntax (py_compile)
    ↓
[7] Log session to _token_log.md
    ↓
[8] Extract learnings → append to _learnings.md
    ↓
Next task arrives → smarter
```

## Step 1 — Read Learnings (MANDATORY)

Read C:\Users\Charlie\.claude\skills\_learnings.md
Apply these rules:
- Never repeat a mistake recorded in _learnings.md
- Use techniques that worked in past sessions
- If a past session failed with X approach, try Y instead

## Step 2 — Token Budget Check (MANDATORY)

Read C:\Users\Charlie\.claude\skills\_token_log.md
Calculate:
- Today's used tokens so far
- Remaining budget
- Recommended agent parallelism for this task

Warn the user at thresholds:
- 50%: "Half budget used. Normal dispatch."
- 75%: "75% used. Recommend finishing soon."
- 90%: "90% used. Stop spawning new agents."

## Step 3 — Pre-Read Files ONCE (MANDATORY)

Read every file that will be edited ONCE.
Paste full content into agent prompts.
NEVER let an agent re-read a file you've already read.

## Step 4 — Group by File

1 agent per file. Never 2 agents on same file.

| Files to edit | Target agents |
|--------------|--------------|
| 1-3 files | 1 agent |
| 4-7 files | 2-3 agents |
| 8+ files | 3-5 agents (cap) |

## Step 5 — Dispatch with Tracking

Spawn all agents simultaneously. Track:
- Agent name
- Files assigned
- Tokens (from notification)
- Duration (from notification)

## Step 6 — Verify and State-Produce

After all agents complete:
- `python -m py_compile [file]` for every edited file
- Report pass/fail per file
- Dispatch state-producer-agent with the full session record

### State Producer Integration

After syntax verification, dispatch state-producer-agent with all session data:

**Prompt for state-producer-agent:**
```
You are the state producer. Emit structured events and state updates for this session.

## Session Data

Agents that ran:
[paste agent name + outcome + tokens + duration for each]

Files modified:
[paste list of files edited]

Issues resolved:
[paste count per agent]

Task type: [code-fix | code-review | refactor | learning | budgeting | stockpile | git-commit | other]

Generate all applicable __STATE_EVENT__ blocks and __STATE_UPDATE__ blocks.
Always include: task_completed or task_failed, benchmark_score (if benchmarkable), compute_system_health.
```

After state-producer-agent completes, READ its output and call the state engine.

### Step 6b — Execute State Updates (Opus runs this)

After the state-producer-agent finishes, you (Opus) must parse its output and execute the state engine calls. The agent's output will contain `__STATE_EVENT__` blocks and `__STATE_UPDATE__` blocks. Execute them by running this Python:

```python
import sys
sys.path.insert(0, r"C:\Users\Charlie\.claude")
import events
import state_engine

# Parse the state-producer output and call the appropriate functions.
# Always call compute_system_health() last.

# Example pattern — adapt to what was actually emitted:
state_engine.compute_system_health()
```

If multiple state updates were emitted, call them in this order:
1. All `log_*` calls (in any order)
2. `compute_system_health()` last

**Important**: The `os` module is already available in the Python runtime. If you get a NameError on `os`, add `import os` at the top of the script block.

The HUD v2 reads state every 5 seconds. Calling these functions after every session is what makes the HUD live.

Key state_engine functions to call:
| Event | Function |
|-------|----------|
| benchmark_run_completed | `state_engine.log_benchmark(score, task_name, benchmark_confirmed, domain)` |
| agent_spawned/retired | `state_engine.update_agent(agent_data)` |
| learning_generated/validated | `state_engine.log_learning_change(pipeline_event)` |
| memory retrieval | `state_engine.log_memory_signal(hit_rate, usefulness, noise)` |
| routing decision | `state_engine.log_routing_decision(claude_calls_delta, minimax_calls_delta, escalation, bad_routing)` |
| verification | `state_engine.log_verification(coverage, error_catch, hallucination_catch)` |
| significant change | `state_engine.log_changelog_entry(entry_type, description, benchmark_impact)` |
| (always last) | `state_engine.compute_system_health()` |

The HUD v2 reads this state every 5 seconds — keep all state functions called after every session.

## Step 7 — Log Session (MANDATORY)

Write to _token_log.md:
```
## Session: YYYY-MM-DD HH:MM — [Task]

| Agent | Files | Tokens | Duration |
|-------|-------|--------|----------|
| [name] | [files] | [tokens] | [ms] |

Total tokens: [sum]
Total issues fixed: [count]
Agent count: [N]
```

## Step 8 — Extract Learnings (MANDATORY)

Spawn a MiniMax learning agent to:
1. Read the session log in _token_log.md
2. Read _learnings.md
3. Write 3-5 new learnings from this session
4. Append to _learnings.md

Learning agent prompt:
```
You are a workflow analyst. Review this session and extract learnings.

Session log:
[paste the session entry from _token_log.md]

Existing learnings:
[paste _learnings.md]

Output: Write 3-5 new learnings in this format:

### What worked
- [specific technique]

### What failed
- [specific mistake]
- [better alternative]

### Actionable improvement
- [one specific change for next time]
```

## Token Efficiency Target

| Metric | Bad | Good | Target |
|--------|-----|------|--------|
| Agents per task | 18+ | 5-10 | 2-5 |
| File re-reads | Many | Some | Zero |
| Session tokens | >1000k | 200-500k | 50-200k |
| Post-task learning | None | Some | Always |

## Anti-Patterns to Never Repeat

(from _learnings.md)
- Never spawn more than 5 agents simultaneously
- Never have 2 agents edit the same file
- Never let agents re-read files you already read
- Never skip post-task session logging
- Never skip learning extraction

## Step 9 — Auto-Benchmark (MANDATORY — Auto After Every Session)

After extracting learnings, run the agent-stockpile-manager:

1. Read _stockpile.md
2. Read _learnings.md (last 5 sessions)
3. Read _token_log.md (last 5 sessions)
4. Evaluate each active agent:
   - Quality rating: high/medium/low based on recent performance
   - Tokens per issue: compare to average
   - Improvement rate: are learnings being applied?

5. Decision per agent:
   - HIGH quality + improving → keep
   - MEDIUM quality → monitor for 2 more sessions
   - LOW quality → rewrite spec or retire
   - Never dispatched in 5 sessions → candidate for retirement

6. Look for new agent candidates:
   - Recurring task without specialist → draft candidate agent
   - Add to _stockpile.md Candidate table

7. Update _stockpile.md with:
   - Last used date (now)
   - Sessions used count (+1)
   - Quality rating
   - Any new candidates or retirements

## The Complete Self-Improving Loop

```
Task arrives
    ↓
[1] Read _learnings.md + _token_log.md
    ↓
[2] Pre-read files ONCE
    ↓
[3] Group by file → dispatch specialists (2-5 agents)
    ↓
[4] code-fix-agent + code-review-agent run
    ↓
[5] Verify syntax (py_compile)
    ↓
[6] state-producer-agent emits events + state updates → HUD gets data
    ↓
[7] git-commit-agent (if fixes verified)
    ↓
[8] token-budget-agent logs session
    ↓
[9] learning-agent extracts 3-5 new learnings
    ↓
[10] agent-stockpile-manager benchmarks + optimizes
    ↓
_stockpile.md updated
_learnings.md grows
HUD v2 shows live state
Next task arrives → smarter agent pool
```
