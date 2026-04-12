# Agent Stockpile Inventory

Single source of truth for all specialist MiniMax agents.
Updated: 2026-04-13
Managed by: agent-stockpile-manager

## Last Benchmark Session: 2026-04-12 (big code review)

## Active Agents

| Agent | File | Purpose | Last Used | Sessions Used | Quality Rating |
|-------|------|---------|-----------|-------------|---------------|
| code-fix-agent | code-fix-agent.md | Fix issues in files | 2026-04-12 | 1 | medium |
| code-review-agent | code-review-agent.md | Review code, rubric-scored | 2026-04-12 | 1 | medium |
| learning-agent | learning-agent.md | Extract learnings from sessions | 2026-04-12 | 1 | medium |
| token-budget-agent | token-budget-agent.md | Track token burn rate | 2026-04-12 | 1 | medium |
| git-commit-agent | git-commit-agent.md | Write conventional commits | 2026-04-12 | 1 | medium |
| agent-stockpile-manager | agent-stockpile-manager.md | Auto-manage the stockpile | 2026-04-12 | 1 | medium |
| state-producer-agent | state-producer-agent.md | Emit events + state updates after tasks | 2026-04-13 | 0 | new |

## Candidate Agents

| Agent | File | Purpose | Status |
|-------|------|---------|--------|
| code-fix-agent-v2 | pending | Rewrite with pre-read-once baked in | Draft after session recovery |
| session-recovery-agent | pending | Auto-recover from .jsonl logs on crash | Identified after 2026-04-13 data loss |

## Retired Agents

None yet.

## Dispatch Rules

1. Always dispatch from Active Agents table only
2. Never dispatch a Candidate agent without noting it in the workflow
3. Retired agents stay retired unless quality improves
4. Max 10 active agents — retire before adding new ones

## Known Gaps (from session analysis)

- No agent for auto-MEMORY.md backup → identified, candidate for creation
- No agent for session recovery from .jsonl → identified, candidate for creation
- No pre-read-once enforcement in agent prompts → learning from big session

## Post-Session Benchmark (2026-04-13 recovery)

All agents were used in the 2026-04-12 session but spawned without pre-read-once.
The skills (minimax-dev-workflow, minimax-workflow-optimizer) were CREATED as a result
of that session's waste. The agents themselves are functional but the workflow around them was missing.

**Action**: agents are MEDIUM quality because the workflow (pre-read-once) needs to be
BUILT INTO the agent prompts, not just in the skill. Rewrite code-fix-agent.md to include pre-read-once.