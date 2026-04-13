# Live `.claude` Operator Note

This folder is the live Claude control environment.
It is not just a source repo and it should not be treated like a conventional app layout.

## Current Source Of Truth

The live operational entrypoints are:
- `CLAUDE.md` — controller policy and routing behavior
- `settings.json` — active hook/config path
- `skills/` — live skills and workflow prompts
- `agents/` — live agent specs and stockpile
- `scripts/hooks/minimax-post-task-loop.py` — active post-task loop
- `hud.py` + `state_engine.py` + `events.py` — live runtime/HUD/state core
- `state/` — live derived runtime state

Legacy reference surfaces that are **not** current source of truth:
- `hooks/` — older ECC-era hook config/docs
- portions of `scripts/hooks/` — legacy JS hook implementations retained for rollback/reference

## Important Distinctions

- `projects/` contains mirror/tracking repos for this environment. It is not the live runtime itself.
- `hooks/` is a legacy ECC-era hook surface and is not the current active source of truth.
- `scripts/hooks/` contains the runtime hook implementations that matter for the current system.
- `debug/diagnostics/` contains old diagnostics, path tests, encoding tests, and temporary artifacts that are not core runtime entrypoints.

## Cleanup Principle

Preserve behavior first.
If something looks unusual, assume it may be operationally important until references are checked.

---

## Plugin Manifest Gotchas

If you plan to edit `.claude-plugin/plugin.json`, be aware that the Claude plugin validator enforces several **undocumented but strict constraints** that can cause installs to fail with vague errors (for example, `agents: Invalid input`). In particular, component fields must be arrays, `agents` must use explicit file paths rather than directories, and a `version` field is required for reliable validation and installation.

These constraints are not obvious from public examples and have caused repeated installation failures in the past. They are documented in detail in `.claude-plugin/PLUGIN_SCHEMA_NOTES.md`, which should be reviewed before making any changes to the plugin manifest.

## Custom Endpoints and Gateways

ECC does not override Claude Code transport settings. If Claude Code is configured to run through an official LLM gateway or a compatible custom endpoint, the plugin continues to work because hooks, commands, and skills execute locally after the CLI starts successfully.

Use Claude Code's own environment/configuration for transport selection, for example:

```bash
export ANTHROPIC_BASE_URL=https://your-gateway.example.com
export ANTHROPIC_AUTH_TOKEN=your-token
claude
```
