# MiniMax Workflow Learnings

A growing knowledge base of lessons learned from every MiniMax agent session.
READ THIS FILE BEFORE EVERY TASK. New learnings are appended after each session.

## How to Use
- Before every task: read this file, apply relevant learnings
- After every task: spawn a MiniMax agent to extract 3-5 new learnings, append to this file
- Learnings should be specific and actionable (not vague)

## Format
```
## Session: YYYY-MM-DD — [Task Name]

### What worked
- [Specific technique or approach that improved efficiency]

### What failed
- [Specific mistake that wasted tokens or produced poor results]
- [The better alternative]

### Token analysis
- Task: [description]
- Issues fixed: [count]
- Tokens used: [approximate from agent notification]
- Waste estimate: [what % could have been saved]

### Actionable improvement
- [One specific change to make next time]
```

---

## Session: 2026-04-13 — Test session: events.py review + fix via MiniMax agents

### What worked
- Full loop working end-to-end: MiniMax review → MiniMax fix → events emitted → state engine updated → HUD live
- code-review-agent found all 9 real issues in events.py (2 HIGH, 3 MEDIUM, 4 LOW)
- code-fix-agent applied all fixes correctly (py_compile passed)
- overall_state computed correctly: "benchmark-confirmed", delta: 0.75

### What failed
- code-fix-agent introduced typo: os.O_CREATE instead of os.O_CREAT — missed by py_compile (valid Python, wrong constant name)
- Always verify the actual constant names used in the standard library when agents generate platform-specific code

### Actionable improvement
- When agents generate platform-specific code (msvcrt, fcntl, os.O_*), always verify constants exist before trusting py_compile alone
- Add a second quick review pass for OS-level code before running

---

## Session: 2026-04-13 — HUD v2 Windows launch debugging

### What worked
- Debugging agent found all 3 bugs correctly and fixed them
- Token burn was justified — 3 non-obvious Windows-specific Rich bugs that would have taken hours to find manually
- `timeout` bash tool useful for testing long-running processes

### What failed
- Jumped to agents too fast — should have tested `start "" python hud.py` manually first with stderr capture
- `async: true` on SessionStart + `start` command = infinite loop (SessionStart fires → start launches window → that triggers SessionStart again)
- Rich Live generator pattern silently broken on Windows pipe detection

### Token analysis
- Task: fix hud.py crash on Windows
- Agents used: 1 (debugger agent, ~98k tokens)
- Could have been: 0 tokens if basic test first (`python hud.py 2>&1`)
- Lesson: always run manual smoke test BEFORE spawning debugging agents

### Actionable improvement
- ALWAYS test the actual failing command manually with stderr capture before spawning agents
- Windows hooks using `start` MUST use `async: false` to avoid SessionStart loops
- Rich on Windows: always use `force_terminal=True` + `legacy_windows=False` when stdout is piped

---

## Session: 2026-04-12 — Code Review (Hypatia bot + Emi bot)

### What worked
- Parallel dispatch by file: Emi's anki/gcal submodules dispatched to separate agents, avoided merge conflicts
- Creating config.py to centralize MODEL constant across 6 files avoided duplication
- Skills system (minimax-dev-workflow, skill-builder) created mid-session — good automation

### What failed
- Spawned 18 agents for 22 fixes on 2 files. Should have been 2 agents (1 per project file set). Each agent read the same files from scratch — massive redundant I/O
- Pre-read-once was NOT used despite being planned — the workflow was written AFTER the session, not during
- bare-except: fixes were split across 6 agents — should have been 1 agent doing all exception handling in one pass
- No post-task session logging: token counts and durations from agent notifications were not recorded in real time
- Emi confirmation timeout bug: agent reported "already fixed" — line numbers in task description were outdated. Always verify current file state before fixing

### Token analysis
- Task: 22 fixes across Hypatia + Emi bots
- Agents spawned: ~22 (way too many)
- Estimated optimal with pre-read-once + 1 agent per file: ~150k tokens
- Actual: ~839k tokens
- Waste: ~689k tokens (82% waste)

### Actionable improvement
- GROUP all fixes for the same file into ONE agent. Never spawn multiple agents on the same file.
- READ each file ONCE, paste content directly into the agent prompt. Never let agents re-read.
- Target: 2-5 agents per project regardless of issue count
- Write the workflow skill BEFORE the session, not after

---

## Session: 2026-04-13 — Session recovery + system re-initialization

### What worked
- .jsonl session logs preserved everything — chat recoverable after accidental deletion
- Memory system (MEMORY.md) can be reconstructed from .jsonl logs
- Skills and agents were in separate files (.claude/skills, .claude/agents) — survived the memory wipe

### What failed
- Project memory directory was empty — MEMORY.md had no entries
- System state (last session context, current project status) was lost
- No backup of the in-progress terminal/HUD project — directory path not recorded in memory before crash

### Token analysis
- Recovery: ~55k tokens (read .jsonl logs, reconstruct MEMORY.md)
- Could have been 0 if memory was backed up before session

### Actionable improvement
- ALWAYS update MEMORY.md at end of every session with: what was built, next steps, directory paths
- Before doing any big build: confirm memory is saved
- The terminal/HUD project directory path MUST be in MEMORY.md going forward

---

## Session: 2026-04-13 — System hardening

### What worked
- Wrote comprehensive MEMORY.md capturing all session history from .jsonl
- Token log updated with historical data from session logs
- MEMORY.md now has: file locations, agent specs, learnings, token budget, session history, unresolved items

### What failed
- Critical project (terminal/HUD) was planned but not yet in memory when session crashed
- Metaswarm was installed but project not configured with metaswarm setup

### Actionable improvement
- Run `/metaswarm:setup` on this project immediately to prevent future loss
- After building anything new: add path + status to MEMORY.md before ending session
- Consider: auto-save MEMORY.md every 10 minutes during big builds

---

## Anti-Patterns to Never Repeat

1. ❌ Never let agents re-read files already read (pre-read-once is MANDATORY)
2. ❌ Never skip post-task logging to _token_log.md
3. ❌ Never skip learning extraction after session
4. ❌ Never build without updating MEMORY.md with directory paths
5. ❌ Never skip py_compile verification after agent edits
6. ❌ Never skip agent-stockpile-manager benchmark after session
7. ❌ Never propose a fix before root cause is found (from systematic-debugging)
8. ❌ Never claim "fixed" or "passes" without running the verification command first (from verification-before-completion)
9. ❌ Never trust agent "success" reports without fresh evidence

## Updated Rules (supersede anti-patterns 1-2 above)

The parallelism rules were updated 2026-04-13:
- Parallelism is AGGRESSIVE by default — use as many MiniMax workers as improve throughput
- Multiple agents on the same file are ALLOWED when decomposed clearly (audit/patch/verify or logic/tests/docs patterns)
- Bad patterns: duplicate blind edits, conflicting writes, workers re-discovering context Opus already has
- Good patterns: one agent per logical concern, Opus owns merge/integration
- Limiting factor is overlap + merge friction + wasted context — not agent count

## Token Efficiency Targets

| Metric | Terrible | Bad | Target | Great |
|--------|----------|-----|--------|-------|
| Agents per task | 18+ wasteful | 10-17 redundant | aggressive parallelism | as needed |
| File re-reads | Many | Some | Zero | Zero |
| Session prompts (small task) | >5000 | 2000-5000 | <2000 | <500 |
| Session prompts (big task) | >15000 | 5000-15000 | 1000-5000 | <1000 |
| Post-task learning | None | Sometimes | Always | Always + refine |
| MEMORY.md updated | Never | Sometimes | Every session | After every milestone |

## The Complete Self-Improving Loop (must run after EVERY session)

```
Task completes
    ↓
[1] token-budget-agent logs to _token_log.md
    ↓
[2] learning-agent extracts 3-5 new learnings → _learnings.md
    ↓
[3] agent-stockpile-manager benchmarks agents → _stockpile.md
    ↓
[4] Update MEMORY.md with: what was built, next steps, directory paths
    ↓
Next task → smarter
```

## Unresolved Items (need user input)

1. **Terminal/HUD directory path** — was planned in sessions 3/4 but not confirmed as created
   - User wanted: side terminal HUD with checklist, Opus Max orchestrator, self-improving agents
   - Need: the actual directory path where this was built (or confirmation to rebuild)

<!-- minimax-loop:dfa89efab069dcbd49ecf607619fa8ba3ea45c9c -->
## Session: 2026-04-13 17:14 — Auto loop: MiniMax-routed task

### What worked
- Opus kept the execution path on MiniMax using: minimax-delegation +2.

### What failed
- Claude Code hooks do not expose raw MiniMax worker request totals, so tracked requests are a conservative lower bound.

### Actionable improvement
- Keep worker dispatch pinned to `MiniMax-M2.7` and prefer internal MiniMax skills before any plugin fallback.

<!-- minimax-loop:63286be8b7648d5e156c56d0e22bb076503875f6 -->
## Session: 2026-04-13 17:44 — Auto loop: MiniMax-routed task

### What worked
- Task category: `orchestration`.
- Delegatable: `False`.
- Routing outcome: `MiniMax execution`.

### What failed
- Claude Code hooks do not expose raw MiniMax worker request totals, so tracked requests are a conservative lower bound.

### Actionable improvement
- Keep worker dispatch pinned to `MiniMax-M2.7`, prefer internal MiniMax skills, and treat Claude execution of delegatable work as a routing penalty.

<!-- minimax-loop:65efc5841f01af3b77349cb52264d82ce6706ccd -->
## Session: 2026-04-13 17:44 — Auto loop: implementation task

### What worked
- Task category: `implementation`.
- Delegatable: `True`.
- Routing outcome: `MiniMax execution`.

### What failed
- Claude Code hooks do not expose raw MiniMax worker request totals, so tracked requests are a conservative lower bound.

### Actionable improvement
- Keep worker dispatch pinned to `MiniMax-M2.7`, prefer internal MiniMax skills, and treat Claude execution of delegatable work as a routing penalty.
