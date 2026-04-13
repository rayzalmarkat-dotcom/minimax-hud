from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import state_engine


class StateEngineSmokeTest(unittest.TestCase):
    def test_benchmark_and_health_persist_verified_ratio(self) -> None:
        original_state_dir = state_engine.STATE_DIR
        with tempfile.TemporaryDirectory() as tmpdir:
            state_engine.STATE_DIR = Path(tmpdir)
            try:
                state_engine.log_benchmark(
                    score=0.9,
                    task_name="smoke test",
                    benchmark_confirmed=True,
                    domain="tests",
                    evidence={"source": "unit-test"},
                )
                state_engine.log_verification(
                    coverage=1.0,
                    error_catch=1.0,
                    hallucination_catch=1.0,
                    contradiction_catch=1.0,
                    adversarial_review=True,
                )
                health = state_engine.compute_system_health(
                    prompt_health="stable",
                    memory_quality=1.0,
                    routing_confidence=1.0,
                    token_budget_pct=10,
                    session_count_today=1,
                )

                benchmark = state_engine.read_state("benchmark_state.json")
                self.assertEqual(benchmark["verified_runs"], 1)
                self.assertEqual(benchmark["speculative_runs"], 0)
                self.assertEqual(
                    benchmark["benchmark_confirmed_vs_speculative_ratio"], 1.0
                )
                self.assertEqual(
                    benchmark["benchmark_evidence"]["source"], "unit-test"
                )
                self.assertEqual(
                    health["benchmark_confirmed_vs_speculative_ratio"], 1.0
                )
                self.assertEqual(health["overall_state"], "benchmark-confirmed")
            finally:
                state_engine.STATE_DIR = original_state_dir


if __name__ == "__main__":
    unittest.main()
