# Token Usage Log

**MiniMax M2.7 Meters:** Actual limit is 800 REQUESTS / 5 hours (10x Starter plan).
This log tracks estimated tokens for internal efficiency analysis — NOT the budget.
MiniMax throughput: ~50 TPS normal, ~100 TPS off-peak.

Target: log every session for efficiency tracking, not budget enforcement.

<!-- Sessions logged below -->

## Session: 2026-04-12 — Code Review (Hypatia + Emi bots)

| Agent | Tokens | Duration (ms) |
|-------|--------|---------------|
| code-review-study-web | ~120k | estimated |
| code-review-emi-bot | ~120k | estimated |
| code-review-hypatia-bot2 | ~120k | estimated |
| emi-fix-DATA_DIR | ~80k | estimated |
| emi-fix-handle_occlusion_sync | ~80k | estimated |
| emi-fix-shared-MODEL-constant | ~80k | estimated |
| hypatia-fix-print-logging | ~80k | estimated |
| hypatia-fix-news_cache-dynamic-key | ~80k | estimated |
| hypatia-fix-duplicate-nutrition-tracking | ~80k | estimated |
| (plus ~13 more agents) | | |

**Total: ~839k tokens (all sessions this day)**
**Waste estimate: ~689k (82%)** — re-reading files, too many agents
**Session count: ~22 agents for 2 files**

### Root cause of waste
- Pre-read-once was NOT used — each agent read files from scratch
- 18 agents for 22 fixes on 2 files — should have been 2 agents
- No session logging during work — metrics not tracked in real time

---

## Session: 2026-04-12 — Skills + Plans build

| Agent | Tokens | Duration |
|-------|--------|----------|
| minimax-delegation-SKILL creation | ~40k | ~2min |
| skill-builder improvement | ~40k | ~2min |
| plan write (inherited-cuddling-blanket) | ~60k | ~3min |
| agent specs (6 files) | ~80k | ~4min |

**Total: ~220k tokens**

---

## Session: 2026-04-13 — Session recovery

| Context | Tokens |
|---------|--------|
| Recovery from .jsonl logs | ~50k |
| MEMORY.md reconstruction | ~5k |

**Total: ~55k tokens**

---

## Running Total (2026-04-12 cycle)

| Date | Sessions | Tokens | Notes |
|------|----------|--------|-------|
| 2026-04-12 | 3 main | ~1,059k | Big session heavy |
| 2026-04-13 | 1 (recovery) | ~55k | Minor |

**Token efficiency target for next session: <200k** (pre-read-once + 2-5 agents max)