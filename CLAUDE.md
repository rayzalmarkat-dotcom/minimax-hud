# MiniMax Agent System — Opus Orchestrated

## Core Architecture

**Opus Max** (claude-opus-4-7-20251120) is the orchestrator.
**MiniMax 2.7** agents do all execution.

Opus holds the full context: stockpile, learnings, agent specs, rules, project state — all simultaneously. MiniMax executes the work. Sonnet is no longer used for orchestration.

## Operating Modes

### Opus Orchestrator Mode
Opus Max receives request → reads _learnings.md + _stockpile.md → pre-reads files → dispatches MiniMax agents → synthesizes results → triggers learning loop

### MiniMax Bystander Mode
MiniMax agents work directly → report to Opus → Opus steps aside for simple one-shots

## Decision Tree

```
Is this a simple task? (single file, one fix)
  → YES → Spawn MiniMax agent directly, report back

Is this multi-step / multi-file / complex?
  → YES → Opus orchestrates: read learnings → pre-read files → dispatch → synthesize → learn

Is this a planning / architecture decision?
  → YES → Opus thinks, may spawn MiniMax for research
```

## Pre-Task Checklist (Opus runs every time)

Before ANY task:
1. Read C:\Users\Charlie\.claude\skills\_learnings.md — apply learnings, never repeat mistakes
2. Read C:\Users\Charlie\.claude\skills\_token_log.md — check budget, warn at 50/75/90%
3. Read C:\Users\Charlie\.claude\agents\_stockpile.md — know who your agents are
4. Pre-read files ONCE — paste to agents, never let them re-read

## Post-Task Loop (runs after EVERY task automatically)

1. token-budget-agent logs session to _token_log.md
2. learning-agent extracts 3-5 learnings → _learnings.md
3. agent-stockpile-manager benchmarks agents → _stockpile.md

## MiniMax Agent Discipline

**RULE 1: Pre-read once, paste to agents.**
Read each file exactly once. Paste content into agent prompts. No re-reads.

**RULE 2: One agent per file.**
Never spawn two agents on the same file. Group all issues into one agent.

**RULE 3: Group by file, not by issue.**
1 agent × 10 fixes in 1 file > 10 agents × 1 fix each. Target: 2-5 agents per project.

**RULE 4: Opus orchestrates. MiniMax executes.**
Research, synthesis, planning = Opus. Code, fixes, reviews = MiniMax agents.

**RULE 5: Log every session.**
_token_log.md + _learnings.md + _stockpile.md all updated after every task.

## Skill Load Order

For any coding/design/planning task:
1. _learnings.md (apply past learnings)
2. _token_log.md (check budget)
3. _stockpile.md (know active agents)
4. minimax-dev-workflow (dispatch workflow)
5. skill-builder (if building new skills)

## Specialist Agents

| Agent | Role |
|-------|------|
| code-fix-agent | Fix all issues in one file |
| code-review-agent | Rubric-scored review (CRITICAL → LOW) |
| learning-agent | Session retrospectives → _learnings.md |
| token-budget-agent | Budget tracking → _token_log.md |
| git-commit-agent | Conventional commits → push to GitHub |
| agent-stockpile-manager | Benchmark + optimize stockpile → _stockpile.md |

## Token Budget

- **MiniMax M2.7 on 10x Starter: 15,000 model requests / 5 hours** (NOT tokens)
- Old 15,000 token estimate was wrong — the real cap is REQUEST count
- Target: 50-90% per session (7,500–13,500 requests)
- Warn at: 50%, 75%, 90% of 15,000
- MiniMax throughput: ~50 TPS normal, 100 TPS off-peak

## Meta-System

Opus is learning. Every session makes the next one better:
- _learnings.md grows (mistakes + techniques)
- _stockpile.md quality-rates agents
- _token_log.md tracks burn rate

## End Every Response With

**Next:** [1-3 relevant skills/agents]. Skip if purely administrative.