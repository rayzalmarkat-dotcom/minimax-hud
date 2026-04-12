---
name: user_role
description: Opus Max orchestrates, MiniMax demons own end-to-end tasks
type: user
---

Opus Max (claude-opus-4-7-20251120) is orchestrator/architect. MiniMax agents are task owners, not sub-task executors. The system uses:
- Pre-read-once pattern (never re-read files passed to agents)
- 2-5 agents per task, grouped by file
- 10 event types, 8 JSON state files under ~/.claude/state/
- HUD v2: rich.live.Live(screen=False, refresh_per_second=0.2) — 5s refresh cycle, no terminal jitter
- state_engine.py + events.py live at C:\Users\Charlie\.claude\
- All files in git at C:\Users\Charlie\.claude\projects\C--Users-Charlie\
