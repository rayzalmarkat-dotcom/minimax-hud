# Memory

- [user_role.md](memory/user_role.md) — Opus orchestrator / MiniMax demon architecture
- [feedback.md](memory/feedback.md) — Workflow anti-patterns from past sessions
- [reference.md](memory/reference.md) — External systems and resources

---

## Current Build Status (2026-04-13)

### Done
- **HUD v2 foundation** — hud.py + state_engine.py + events.py, rich.live.Live(screen=False, 0.2rps)
- **8 JSON state files** under ~/.claude/state/ (all pre-seeded)
- **State-producer integration** — state-producer-agent.md + minimax-workflow-optimizer.md wired
- **Post-task loop complete**: py_compile → state-producer-agent → state_engine calls → compute_system_health()
- **Git commit** 9575d07

### Next
- Push to remote (git push)
- Test HUD in a real session (verify 5s refresh works without flicker)
- Wire into minimax-dev-workflow.md (Step 6 updates)

### Locations
- HUD code: `C:\Users\Charlie\.claude\hud.py`
- State engine: `C:\Users\Charlie\.claude\state_engine.py`
- Events: `C:\Users\Charlie\.claude\events.py`
- State files: `C:\Users\Charlie\.claude\state\`
- Design spec: `C:\Users\Charlie\.claude\docs\superpowers\specs\2026-04-13-agent-hud-v2-design.md`
- Git repo: `C:\Users\Charlie\.claude\projects\C--Users-Charlie\` (commit 9575d07)
