# Agent Orchestration

## Orchestrator: Opus Max

Claude Opus Max (claude-opus-4-7-20251120) is the orchestrator.
MiniMax 2.7 agents do all execution.
Sonnet is NOT used for orchestration.

## MiniMax Agent Discipline (ALWAYS)

These rules apply to EVERY MiniMax agent dispatch:

**RULE 1: Pre-read once, paste into prompts.**
Never let an agent re-read a file you've already read this session.

**RULE 2: One agent per file.**
Never spawn two agents on the same file simultaneously.

**RULE 3: Group by file, not by issue.**
1 agent handling 10 issues in 1 file > 10 agents handling 1 issue each.

**RULE 4: Pre-task checklist before every task.**
1. Read _learnings.md — apply learnings
2. Read _token_log.md — check budget
3. Read _stockpile.md — know active agents
4. Pre-read files — paste to agents

**RULE 5: Post-task loop after every task.**
1. token-budget-agent logs to _token_log.md
2. learning-agent extracts learnings → _learnings.md
3. agent-stockpile-manager benchmarks → _stockpile.md

## Specialist MiniMax Agents

| Agent | File | Role |
|-------|------|------|
| code-fix-agent | agents/code-fix-agent.md | Fix all issues in one file |
| code-review-agent | agents/code-review-agent.md | Rubric-scored review |
| learning-agent | agents/learning-agent.md | Session retrospectives |
| token-budget-agent | agents/token-budget-agent.md | Budget tracking |
| git-commit-agent | agents/git-commit-agent.md | Conventional commits |
| agent-stockpile-manager | agents/agent-stockpile-manager.md | Stockpile optimization |

## Task → Agent Mapping

| Task Type | Agent to Dispatch |
|-----------|-----------------|
| Code fixes | code-fix-agent |
| Code review | code-review-agent |
| Post-task learning | learning-agent |
| Budget tracking | token-budget-agent |
| Git commit | git-commit-agent |
| Stockpile update | agent-stockpile-manager |
| Building new agents | skill-builder skill |

## Never run independent agents sequentially — spawn in parallel.

## External Agents (use via metaswarm skills)

| Situation | Agent | When |
|-----------|-------|------|
| Complex multi-phase | metaswarm:orchestrated-execution | 4-phase loop |
| Planning | metaswarm:plan-review-gate | After planning |
| Design decisions | metaswarm:design-review-gate | After brainstorming |
| PR review needed | metaswarm:pr-shepherd | Before commit |
| Starting tracked work | metaswarm:start | Beginning any task |
| Codex review | /codex:review | On any codebase |

## End Every Response With

**Next:** [1-3 relevant skills/agents]. Skip if purely administrative.