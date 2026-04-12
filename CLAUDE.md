# C--Users-Charlie — MiniMax Agent Orchestration System

## Core Architecture

**Opus Max** (claude-opus-4-7-20251120) is the orchestrator.
**MiniMax 2.7** agents do all execution.
Sonnet is NOT used for orchestration.

## Operating Modes

### Opus Orchestrator Mode
Opus Max receives request → reads _learnings.md + _stockpile.md → pre-reads files → dispatches MiniMax agents → synthesizes results → triggers learning loop

### MiniMax Bystander Mode
MiniMax agents work directly → report to Opus → Opus steps aside for simple one-shots

## Pre-Task Checklist (MUST RUN EVERY TIME)

1. Read `C:\Users\Charlie\.claude\skills\_learnings.md` — apply learnings, never repeat mistakes
2. Read `C:\Users\Charlie\.claude\skills\_token_log.md` — check budget, warn at 50/75/90%
3. Read `C:\Users\Charlie\.claude\agents\_stockpile.md` — know who your agents are
4. Pre-read files ONCE — paste to agents, never let them re-read

## Post-Task Loop (MUST RUN AFTER EVERY TASK)

1. token-budget-agent logs session to _token_log.md
2. learning-agent extracts 3-5 new learnings → _learnings.md
3. agent-stockpile-manager benchmarks agents → _stockpile.md
4. Update MEMORY.md with: what was built, directory paths, next steps

## Core Rules

| Rule | Why |
|------|-----|
| Pre-read once, paste to agents | 20k file × 12 re-reads = 240k wasted tokens |
| 1 agent per file, never 2 on same file | Prevents merge conflicts |
| Max 5 simultaneous agents | Beyond this, overhead exceeds benefit |
| Always log session metrics | Enables self-improvement |
| Always extract learnings | Every session makes next smarter |

## Token Budget

- Daily: 15,000 tokens / 5 hours
- Target: 50-90% per session
- Warn at: 50%, 75%, 90%

## Active Specialist Agents

| Agent | File | Role |
|-------|------|------|
| code-fix-agent | .claude/agents/code-fix-agent.md | Fix all issues in one file |
| code-review-agent | .claude/agents/code-review-agent.md | Rubric-scored review |
| learning-agent | .claude/agents/learning-agent.md | Session retrospectives |
| token-budget-agent | .claude/agents/token-budget-agent.md | Budget tracking |
| git-commit-agent | .claude/agents/git-commit-agent.md | Conventional commits |
| agent-stockpile-manager | .claude/agents/agent-stockpile-manager.md | Stockpile optimization |

## Critical File Locations

| File | Purpose | Location |
|------|---------|----------|
| _learnings.md | All session learnings | `C:\Users\Charlie\.claude\skills\_learnings.md` |
| _token_log.md | Token burn tracking | `C:\Users\Charlie\.claude\skills\_token_log.md` |
| _stockpile.md | Agent inventory | `C:\Users\Charlie\.claude\agents\_stockpile.md` |
| MEMORY.md | Project state | `.claude/projects/C--Users-Charlie/memory/MEMORY.md` |
| minimax-workflow-optimizer | Self-improving loop skill | `C:\Users\Charlie\.claude\skills\minimax-workflow-optimizer.md` |
| inherited-cuddling-blanket.md | Full system plan | `C:\Users\Charlie\.claude\plans\inherited-cuddling-blanket.md` |

## Anti-Patterns (NEVER DO)

- ❌ Never spawn more than 5 simultaneous agents
- ❌ Never have 2 agents edit the same file
- ❌ Never let agents re-read files already read (pre-read-once is MANDATORY)
- ❌ Never skip post-task logging to _token_log.md
- ❌ Never skip learning extraction after session
- ❌ Never build without updating MEMORY.md with directory paths
- ❌ Never skip py_compile verification after agent edits

## Git Workflow

Commit format: `<type>: <description>`
Types: feat, fix, refactor, docs, test, chore, perf, ci

Commit after every significant task. Push regularly.

## Metaswarm Integration

This project is metaswarm-enabled. Use:
- `/metaswarm:start` — beginning any tracked task
- `/metaswarm:setup` — (done) configure project
- `/metaswarm:status` — check current state
- `/metaswarm:plan-review-gate` — after planning
- `/metaswarm:design-review-gate` — after design decisions
- `/metaswarm:pr-shepherd` — before commit

## Session Recovery

If session crashes: all conversations saved in `.jsonl` files in project root.
Recover by reading the most recent `.jsonl` file.
Git repo: `C:\Users\Charlie\.claude\projects\C--Users-Charlie\.git`