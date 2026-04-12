---
name: feedback
description: Workflow anti-patterns never to repeat
type: feedback
---

Rule: Never spawn more than 5 simultaneous agents.
**Why:** 18 agents for 22 fixes caused 82% token waste in 2026-04-12 session.
**How to apply:** Group by file, never by issue. Target 2-5 agents per task.

Rule: Pre-read-once is MANDATORY — paste file content into prompts, never let agents re-read.
**Why:** Re-reads waste tokens and agents can't see what you've already read.
**How to apply:** Read each file once, paste full content into agent prompts.

Rule: Never skip the post-task loop — token-log → learnings → stockpile update.
**Why:** Without it the system doesn't improve, and MEMORY.md goes stale.
**How to apply:** After every task: token-budget-agent → learning-agent → agent-stockpile-manager.

Rule: Always update MEMORY.md before ending a session with: what was built, next steps, directory paths.
**Why:** Session crash in 2026-04-13 destroyed all context; had to reconstruct from .jsonl logs.
**How to apply:** Before any break/crash, append current milestone and paths to C:\Users\Charlie\.claude\MEMORY.md.
