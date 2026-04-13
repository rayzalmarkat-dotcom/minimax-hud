# MiniMax Agent Orchestration System

**Opus Max** (claude-opus-4-7-20251120) orchestrates. **MiniMax-M2.7** workers execute.
Every session makes the next one smarter.

---

## What This Is

A self-improving agent system where:
- A strong orchestrator (Opus Max) holds full context — stockpile, learnings, routing policy, agent specs, project state — and makes all decisions
- Fast, cheap workers (MiniMax M2.7) do the execution: code, fixes, reviews, research
- The system learns from every session and improves automatically
- A live HUD dashboard tracks everything in real time
- A background daemon runs improvement cycles every 30 minutes, even when you're not using Claude Code

---

## The Core Loop

```
Task arrives
    ↓
[1] Opus reads learnings + stockpile → applies past lessons
    ↓
[2] Opus checks request budget → warns if near limit
    ↓
[3] Opus pre-reads all files ONCE → no redundant I/O
    ↓
[4] MiniMax workers dispatched (1 per file, max 5 simultaneous)
    ↓
[5] Workers execute → py_compile verifies → state updated
    ↓
[6] Post-task loop: log session → extract learnings → benchmark agents
    ↓
Next task → smarter system
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    OPUS MAX                          │
│  claude-opus-4-7-20251120                          │
│  Holds full context simultaneously                  │
│  Makes all routing + orchestration decisions         │
└──────────────────────┬──────────────────────────────┘
                       │ dispatches
                       ▼
┌─────────────────────────────────────────────────────┐
│              MiniMax M2.7 Workers                   │
│  specialist agents execute code, fixes, reviews    │
│  model: MiniMax-M2.7 (pinned explicitly)          │
└──────────────────────┬──────────────────────────────┘
                       │ write state
                       ▼
┌─────────────────────────────────────────────────────┐
│  state_engine.py  →  JSON files in ~/.claude/state/│
│  events.py        →  event_log.jsonl               │
└──────────────────────┬──────────────────────────────┘
                       │ reads
                       ▼
┌─────────────────────────────────────────────────────┐
│                   hud.py                            │
│  Live terminal dashboard — refreshes every 5s      │
│  Shows: benchmark score, agent registry, routing,  │
│  memory, verification, learning pipeline, health    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│            self_improve_daemon.py                   │
│  Background process (pythonw, PID 36240)            │
│  Runs every 30 minutes, independent of Claude Code │
│  Audits files round-robin, fixes CRITICAL/HIGH     │
│  Updates state → HUD stays live                    │
└─────────────────────────────────────────────────────┘
```

---

## Specialist Agents (`agents/`)

| Agent | Role |
|-------|------|
| `code-fix-agent` | Fixes all issues in one file (grouped, not one agent per issue) |
| `code-review-agent` | Rubric-scored review: CRITICAL → HIGH → MEDIUM → LOW |
| `learning-agent` | Session retrospectives → `_learnings.md` |
| `token-budget-agent` | Tracks request usage, warns at 50/75/90% of 15,000/5h |
| `git-commit-agent` | Conventional commits + push to GitHub |
| `agent-stockpile-manager` | Benchmarks agents, retires old ones, auto-creates new ones |
| `state-producer-agent` | Emits HUD state events after every session |

---

## Skills (`skills/`)

| Skill | Purpose |
|-------|---------|
| `minimax-workflow-optimizer` | The self-improving loop meta-skill |
| `minimax-dev-workflow` | How to dispatch MiniMax workers (pre-read-once, group by file) |
| `minimax-delegation` | How to spawn MiniMax workers |
| `skill-builder` | How to create new skills |
| `_learnings.md` | Growing knowledge base — mistakes + techniques from every session |
| `_token_log.md` | Request burn tracking per session |
| `_stockpile.md` | Active agents inventory with quality ratings |

---

## Rules (`rules/`)

Per-language coding standards, security guidelines, testing requirements, patterns, and hooks. Currently covers: Python, TypeScript, Go, Kotlin, Swift, C++, PHP, Perl.

---

## Capabilities

### Self-Improvement
- Every session logged → learnings extracted → applied to next session
- Agent quality tracked → weak agents retired, strong ones promoted
- Stockpile auto-creates new specialist agents when recurring tasks emerge without one
- 11 sessions of learnings already captured and applied

### Live HUD (`hud.py`)
- Benchmark score + rolling average + delta
- Agent registry (top 8 by contribution score, flagged for noise/regression)
- Claude vs MiniMax workload split bar
- Memory retrieval stats (hit rate, usefulness, noise)
- Verification coverage (error catch, hallucination catch)
- Learning pipeline: GEN → VAL → PRO → REJ → DIS → PEN
- System health overall state
- Changelog (last 4 entries)
- Token budget bar
- Windows-safe: PID lock prevents multi-terminal infinite spawn loops

### Background Daemon (`self_improve_daemon.py`)
- Runs as `pythonw` background process
- Every 30 minutes: audits 3 files round-robin, fixes CRITICAL/HIGH issues
- Calls state engine → HUD updates live
- Stops gracefully when `~/.claude/state/SELF_IMPROVE_STOP` exists
- Self-improves the system while you sleep

### Token/Request Budget
- MiniMax M2.7 10x Starter: **15,000 model requests / 5 hours**
- Warnings at 50% (7,500), 75% (11,250), 90% (13,500)
- HUD strip shows sessions logged + efficiency token estimates
- Daemon checks budget before each cycle

### Post-Task Hook (auto-runs after every response)
`~/.claude/scripts/hooks/minimax-post-task-loop.py`:
1. Logs MiniMax request activity → `_token_log.md`
2. Extracts routing/loop learning → `_learnings.md`
3. Updates agent session counts → `_stockpile.md`
4. Fires state events → HUD reflects live activity

---

## What We're Building Toward

### Phase 1 — Done ✅
- [x] Opus orchestrates, MiniMax executes
- [x] Pre-read-once + group-by-file dispatch (eliminates 80%+ token waste)
- [x] Live HUD with all system state
- [x] Background self-improvement daemon
- [x] 6 specialist agents
- [x] Learnings loop (11 sessions captured)
- [x] Stockpile with quality ratings
- [x] Post-task hook for automatic state updates

### Phase 2 — In Progress 🔨
- [ ] Stockpile auto-creation: daemon detects recurring tasks without agents → drafts new agent specs → proposes to add to stockpile
- [ ] Benchmark scoring: quantitative quality scores per agent per session
- [ ] Routing intelligence: learned Claude vs MiniMax split based on task type
- [ ] Memory signal: track what gets retrieved from memory, flag low-usefulness entries for pruning

### Phase 3 — Planned 📋
- [ ] Multi-project support: share agents/learnings across repos
- [ ] Agent communication: MiniMax workers hand off context to each other mid-task
- [ ] Self-authored agents: system analyses its own bottlenecks → writes new agents without human prompting
- [ ] Distributed daemon: run self-improvement on multiple machines, merge learnings

### Anti-Patterns Never Repeated
1. Never spawn >5 simultaneous agents
2. Never 2 agents on the same file
3. Never let agents re-read files already read
4. Never skip learnings extraction after session
5. Never skip py_compile after agent edits
6. Never propose fix before root cause
7. Never claim "fixed" without fresh verification
8. Never trust agent success without evidence

---

## Key Files

| Path | Purpose |
|------|---------|
| `~/.claude/hud.py` | Live HUD dashboard |
| `~/.claude/state_engine.py` | JSON state + health computation |
| `~/.claude/events.py` | Thread-safe event log |
| `~/.claude/self_improve_daemon.py` | Background self-improvement loop |
| `~/.claude/settings.json` | SessionStart hook, permissions |
| `~/.claude/CLAUDE.md` | Orchestration instructions |
| `~/.claude/skills/_learnings.md` | Session learnings |
| `~/.claude/agents/_stockpile.md` | Agent inventory |
| `~/.claude/state/` | JSON state files (HUD reads here) |
| `~/.claude/state/hud_running.lock` | PID lock for single HUD instance |

---

## Setup

The system is configured and running. On a fresh machine:
1. Clone `https://github.com/rayzalmarkat-dotcom/minimax-hud`
2. Run `python hud.py` to start the live dashboard
3. Start the daemon: `pythonw self_improve_daemon.py` (Windows GUI mode)
4. Claude Code will auto-launch HUD on every terminal session via SessionStart hook

---

## Token Efficiency

| Metric | Before (bad) | After (good) |
|--------|-------------|--------------|
| Agents per task | 18+ | 2-5 |
| File re-reads | Many | Zero |
| Token waste | ~82% | ~10% |
| Post-task learning | None | Always |

The pre-read-once + group-by-file discipline alone cuts token burn by ~80%.
