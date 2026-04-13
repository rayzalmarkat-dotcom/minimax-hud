param(
    [string]$MirrorPath = "$HOME/.claude/projects/C--Users-Charlie"
)

$liveRoot = Join-Path $HOME '.claude'

$copyMap = @(
    'CLAUDE.md',
    '.gitignore',
    'settings.json',
    'hud.py',
    'state_engine.py',
    'events.py',
    'self_improve_daemon.py',
    'scripts/sync-minimax-mirror.ps1',
    'README.md',
    'tests/test_state_engine_smoke.py',
    'skills/minimax-delegation/SKILL.md',
    'skills/minimax-dev-workflow/SKILL.md',
    'skills/minimax-workflow-optimizer/SKILL.md',
    'skills/_learnings.md',
    'skills/_token_log.md',
    'agents/_stockpile.md',
    'agents/token-budget-agent.md',
    'agents/state-producer-agent.md',
    'scripts/hooks/minimax-post-task-loop.py',
    'state/agent_registry.json',
    'state/benchmark_state.json',
    'state/changelog.json',
    'state/learning_pipeline.json',
    'state/routing_state.json',
    'state/system_health.json'
)

foreach ($rel in $copyMap) {
    $src = Join-Path $liveRoot $rel
    $dst = Join-Path $MirrorPath $rel
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Output "synced $rel"
    }
}
