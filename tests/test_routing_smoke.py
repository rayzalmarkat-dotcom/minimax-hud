"""Smoke tests for MiniMax routing delegation and post-task loop."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Bootstrap — state_engine lives at ~/.claude/
sys.path.insert(0, str(Path.home()))
import state_engine


class RoutingSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_dir = state_engine.STATE_DIR
        self.tmp = tempfile.TemporaryDirectory()
        state_engine.STATE_DIR = Path(self.tmp.name)
        state_engine.STATE_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        state_engine.STATE_DIR = self.original_dir
        self.tmp.cleanup()

    # ------------------------------------------------------------------
    # 1. log_routing_decision updates routing_state.json correctly
    # ------------------------------------------------------------------
    def test_routing_decision_updates_state(self) -> None:
        state_engine.log_routing_decision(
            claude_calls_delta=1,
            minimax_calls_delta=2,
        )
        routing = state_engine.read_state("routing_state.json")
        self.assertEqual(routing["claude_calls"], 1)
        self.assertEqual(routing["minimax_calls"], 2)
        # Workload split: 1 claude / 3 total, 2 minimax / 3 total
        split = routing["workload_split_pct"]
        self.assertAlmostEqual(split["claude"], 1 / 3)
        self.assertAlmostEqual(split["minimax"], 2 / 3)

    # ------------------------------------------------------------------
    # 2. Delegation miss detection (claude_executed_delegatable flag)
    # ------------------------------------------------------------------
    def test_delegation_miss_flagged(self) -> None:
        state_engine.log_routing_decision(
            claude_calls_delta=1,
            minimax_calls_delta=0,
            bad_routing=True,
            category="implementation",
            claude_executed_delegatable=True,
        )
        routing = state_engine.read_state("routing_state.json")
        self.assertGreater(routing["delegation_miss_count"], 0)
        self.assertGreater(routing["claude_execution_leak"], 0)

    # ------------------------------------------------------------------
    # 3. Category split tracking for every ROUTING_CATEGORIES
    # ------------------------------------------------------------------
    def test_category_split_tracked(self) -> None:
        state_engine.log_routing_decision(
            claude_calls_delta=0,
            minimax_calls_delta=1,
            category="implementation",
        )
        routing = state_engine.read_state("routing_state.json")
        for cat in state_engine.ROUTING_CATEGORIES:
            self.assertIn(cat, routing["category_counts"])
            self.assertIn(cat, routing["category_split_pct"])
        # "implementation" bucket should have a computed minimax fraction
        impl = routing["category_split_pct"]["implementation"]
        self.assertAlmostEqual(impl["minimax"], 1.0)
        self.assertAlmostEqual(impl["claude"], 0.0)

    # ------------------------------------------------------------------
    # 4. Post-task loop imports cleanly and main() survives empty input
    # ------------------------------------------------------------------
    def test_post_task_loop_imports_clean(self) -> None:
        import importlib.util

        hook_path = (
            Path.home() / ".claude" / "scripts" / "hooks" / "minimax-post-task-loop.py"
        )
        spec = importlib.util.spec_from_file_location(
            "minimax_post_task_loop", hook_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)

        module = importlib.util.module_from_spec(spec)
        module.__name__ = "minimax_post_task_loop"
        # Register BEFORE exec_module so @dataclass decorator resolves cls.__module__
        with patch.object(sys, "path", list(sys.path)):
            sys.modules["minimax_post_task_loop"] = module
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            sys.modules.pop("minimax_post_task_loop", None)

        self.assertTrue(hasattr(module, "main"))
        self.assertTrue(callable(module.main))

    # ------------------------------------------------------------------
    # 5. Accumulation: multiple calls accumulate correctly
    # ------------------------------------------------------------------
    def test_accumulation(self) -> None:
        state_engine.log_routing_decision(claude_calls_delta=1, minimax_calls_delta=2)
        state_engine.log_routing_decision(claude_calls_delta=1, minimax_calls_delta=3)
        routing = state_engine.read_state("routing_state.json")
        self.assertEqual(routing["claude_calls"], 2)
        self.assertEqual(routing["minimax_calls"], 5)
        # Workload split: 2 claude / 7 total, 5 minimax / 7 total
        split = routing["workload_split_pct"]
        self.assertAlmostEqual(split["claude"], 2 / 7)
        self.assertAlmostEqual(split["minimax"], 5 / 7)


if __name__ == "__main__":
    unittest.main()
