# MiniMax Agent System — Opus Orchestrated

## Core Architecture

**Opus Max** (`claude-opus-4-7-20251120`) is the sole controller.
**MiniMax-M2.7** workers are the default execution path.

Opus holds the full context: stockpile, learnings, routing policy, agent specs,
project state, and session state. MiniMax executes the work. External
marketplace/plugin agents are fallback tools, not the primary path.

## Routing Priority

For any coding, design, planning, research, writing, or file-operation task:
1. Opus applies the internal MiniMax routing policy first
2. Opus loads matching internal MiniMax skills
3. Opus dispatches MiniMax-M2.7 workers explicitly
4. External/plugin agents are used only when the user explicitly asks for them or no internal MiniMax route fits

## Operating Modes

### Opus Orchestrator Mode
Opus receives the request → reads `_learnings.md` + `_stockpile.md` → chooses the internal MiniMax skill path → pre-reads files → dispatches MiniMax workers → synthesizes results → the post-task loop updates state

### MiniMax Bystander Mode
MiniMax workers handle simple one-shots directly and report back to Opus

## Decision Tree

```text
Is this a simple task? (single file, one fix)
  → YES → Route through minimax-delegation and spawn a MiniMax-M2.7 worker directly

Is this multi-step / multi-file / complex?
  → YES → Route through minimax-dev-workflow → Opus pre-reads → dispatches MiniMax-M2.7 workers → synthesize → post-task loop

Is this a planning / architecture decision?
  → YES → Opus stays controller, may spawn MiniMax-M2.7 workers for bounded research/execution

Would an external/plugin agent help?
  → ONLY if the user explicitly asked for it or no internal MiniMax skill / stockpiled MiniMax agent covers the task
```

## Pre-Task Checklist (Opus runs every time)

Before ANY task:
1. Read `C:\Users\Charlie\.claude\skills\_learnings.md` — apply learnings, never repeat mistakes
2. Read `C:\Users\Charlie\.claude\skills\_token_log.md` — requests are the canonical budget unit; warn at 50/75/90%
3. Read `C:\Users\Charlie\.claude\agents\_stockpile.md` — know who your agents are
4. Choose internal MiniMax skills before considering external/plugin agents
5. Pre-read files ONCE — paste to workers, never let them re-read

## Post-Task Loop (runs after EVERY task automatically)

The Stop hook at `C:\Users\Charlie\.claude\scripts\hooks\minimax-post-task-loop.py`
runs after each response and updates:

1. `_token_log.md` with tracked MiniMax request activity
2. `_learnings.md` with an auto-extracted routing/loop learning
3. `_stockpile.md` session counts for the loop agents
4. `state_engine.py` + `events.py` so the HUD reflects routing and learning activity

## MiniMax Agent Discipline

**RULE 1: Pre-read once, paste to workers.**
Read each file exactly once. Paste content into worker prompts. No re-reads.

**RULE 2: One worker per file.**
Never spawn two workers on the same file. Group all issues into one worker.

**RULE 3: Group by file, not by issue.**
1 worker × 10 fixes in 1 file > 10 workers × 1 fix each. Target: 2-5 workers per project.

**RULE 4: Opus orchestrates. MiniMax executes.**
Research, synthesis, planning = Opus. Code, fixes, reviews = MiniMax workers.

**RULE 5: Log every session.**
`_token_log.md` + `_learnings.md` + `_stockpile.md` + state JSON files all update after every task.

**RULE 6: Explicit MiniMax worker pinning.**
When spawning workers, explicitly set `model: "MiniMax-M2.7"` whenever the Agent tool supports it. If model pinning is unavailable in the current build, do not silently reroute work to Claude/plugin workers.

## Skill Load Order

For any coding/design/planning task:
1. `_learnings.md` (apply past learnings)
2. `_token_log.md` (check request budget)
3. `_stockpile.md` (know active agents)
4. `minimax-delegation` (default execution routing)
5. `minimax-dev-workflow` (dispatch workflow)
6. `minimax-workflow-optimizer` (tracked/self-improving runs)
7. `skill-builder` (if building new skills)

## Specialist Agents

| Agent | Role |
|-------|------|
| code-fix-agent | Fix all issues in one file |
| code-review-agent | Rubric-scored review (CRITICAL → LOW) |
| learning-agent | Session retrospectives → `_learnings.md` |
| token-budget-agent | Request tracking → `_token_log.md` |
| git-commit-agent | Conventional commits → push to GitHub |
| agent-stockpile-manager | Benchmark + optimize stockpile → `_stockpile.md` |

## Request Budget

- **MiniMax-M2.7 canonical budget: 15,000 model requests / 5 hours**
- Requests are the only canonical budget unit
- Efficiency token estimates are secondary diagnostics only
- Warn at: 50%, 75%, 90% of 15,000
- The hook/state pipeline tracks conservative lower-bound request activity when raw request counts are not exposed by Claude Code

## Meta-System

Opus is learning. Every session makes the next one better:
- `_learnings.md` grows (mistakes + techniques)
- `_stockpile.md` quality-rates agents
- `_token_log.md` tracks request activity
- `state_engine.py` / `event_log.jsonl` keep the HUD live

## End Every Response With

**Next:** [1-3 relevant skills/agents]. Skip if purely administrative.
