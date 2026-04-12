# C--Users-Charlie — Session History & System State

## What This Project Is
MiniMax agent orchestration system — Claude Opus Max orchestrates, MiniMax agents execute.
Built over sessions on 2026-04-12/13. System is self-improving via the learnings loop.

## Critical System Files

| File | Purpose |
|------|---------|
| `C:\Users\Charlie\.claude\skills\_learnings.md` | All session learnings — READ BEFORE EVERY TASK |
| `C:\Users\Charlie\.claude\skills\_token_log.md` | Token burn tracking per session |
| `C:\Users\Charlie\.claude\agents\_stockpile.md` | Active specialist agents inventory |
| `C:\Users\Charlie\.claude\skills\minimax-workflow-optimizer.md` | The self-improving loop skill |
| `C:\Users\Charlie\.claude\skills\minimax-dev-workflow.md` | Development workflow with pre-read-once |
| `C:\Users\Charlie\.claude\skills\minimax-delegation\SKILL.md` | How to spawn MiniMax agents |
| `C:\Users\Charlie\.claude\skills\skill-builder.md` | How to create/improve skills |
| `C:\Users\Charlie\.claude\plans\inherited-cuddling-blanket.md` | The full plan for the self-improving system |

## Active Specialist Agents (in `C:\Users\Charlie\.claude\agents\`)
- `code-fix-agent` — fix all issues in one file
- `code-review-agent` — rubric-scored code review
- `learning-agent` — session retrospectives → _learnings.md
- `token-budget-agent` — budget tracking → _token_log.md
- `git-commit-agent` — conventional commits + push
- `agent-stockpile-manager` — benchmark + optimize stockpile

## Token Budget
- Daily: 15,000 tokens / 5 hours
- Target: 50-90% per session
- Warn at: 50%, 75%, 90%

## Session Log (from .jsonl history)

### Session 1 (c4e918, ~35 lines) — 2026-04-12
- User tested MiniMax injection, model availability questions

### Session 2 (7c4f8fd, ~19 lines) — 2026-04-12
- Plugin reload, metaswarm marketplace added

### Session 3 (fe56838c, 789 lines) — 2026-04-12 — THE BIG SESSION
- Code review of Hypatia + Emi bots using ONLY MiniMax agents
- 22+ agents spawned, ~839k tokens (82% waste from re-reading)
- Created: minimax-dev-workflow.md, skill-builder.md, minimax-workflow-optimizer.md
- Created: code-fix-agent.md, code-review-agent.md, learning-agent.md, token-budget-agent.md, git-commit-agent.md, agent-stockpile-manager.md
- Created: inherited-cuddling-blanket.md plan
- User explained vision: Opus Max orchestrates, MiniMax executes, skills automate workflows

### Session 4 (63d63301, 627 lines) — 2026-04-12
- Minimax 2.7 injection attempt, Opus Max setup, skills improvement
- Created: minimax-delegation SKILL.md
- User explained: MiniMax is embedded in Claude Code like haiku/sonnet/opus
- User wanted: Opus Max as advisor, MiniMax agents do everything

### Session 5 (27b4ae12, 80 lines) — 2026-04-13
- Jitter issue investigation, Minimax 2.5 env var cleanup

### Session 6 (ea6306a8, 144 lines) — 2026-04-13 (current/last)
- User lost chat, recovered. Session history preserved in .jsonl files.

## UNRESOLVED: The Terminal/HUD Project

In sessions 3/4 (fe56838c), user discussed building:
1. **Side terminal HUD** — checklist overlay while working
2. **Opus Max orchestrator** — not Sonnet (saves tokens)
3. **Self-improving agent system** using metaswarm + MiniMax
4. **Specialist roles** — MiniMax agents embody specific personas

**Problem**: The terminal/HUD was PLANNED but not confirmed as CREATED in any session.
User entry 698: "RU USING MINIMAX AGENTS FOR THIS BTW... we need to make sure u always use them"
The terminal was described but no mkdir/file creation for it appears in the logs.
**LIKELY it was started in a session that wasn't saved or it was in a different location.**

Need from user: the directory path for the terminal/HUD project.

## Learnings Summary (from _learnings.md)

1. Never spawn more than 5 simultaneous agents
2. 1 agent per file — never 2 agents on same file
3. Pre-read files once, paste into prompts — no re-reads
4. Target 2-5 agents per project regardless of issue count
5. Always log session metrics post-task
6. Always extract learnings after every session
7. Verify file syntax (py_compile) after agent edits
8. Never skip post-task loop (budget → learnings → benchmark)

## What Was Lost
- Project memory was empty (wiped 2026-04-13 00:06)
- Session 6 (ea6306a8) is the current session after chat deletion