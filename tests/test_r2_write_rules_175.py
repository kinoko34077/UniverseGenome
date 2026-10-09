"""R2 #175 pre-outcome local operator & qualification integrity tests."""
from __future__ import annotations

from contextlib import ExitStack
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import core.physics as physics
from core.state import Lifecycle
from research import r2_write_rules_175 as r2
from research.slow_trace_persistence_140 import AUTHORITATIVE_FIELDS


class R2WriteRuleTests(unittest.TestCase):
    def _apply(self, name: str, start: int, amount: int, *, active: bool = True):
        cfg = SimpleNamespace(trace_write_cap=8)
        state = SimpleNamespace(
            slow_trace=bytearray([start]),
            lifecycle=[Lifecycle.ACTIVE if active else Lifecycle.FREE],
        )
        with r2.LocalWriteRule(name, set()).attach():
            physics._apply_slow_trace_writes(state, cfg, {0: amount})
        return int(state.slow_trace[0])

    def test_candidates_are_distinct_and_bounded(self):
        self.assertEqual(self._apply("baseline", 10, 40), 18)
        self.assertEqual(self._apply("unit_add", 10, 40), 11)
        self.assertEqual(self._apply("empty_site", 10, 40), 10)
        self.assertEqual(self._apply("empty_site", 0, 40), 8)
        self.assertEqual(self._apply("half_ceiling", 120, 40), 127)
        self.assertEqual(self._apply("half_ceiling", 127, 40), 127)
        self.assertEqual(self._apply("half_ceiling", 220, 40), 220)
        self.assertEqual(self._apply("unit_add", 255, 8), 255)

    def test_zero_amount_and_free_are_inert(self):
        for candidate in r2.PROFILES:
            self.assertEqual(self._apply(candidate, 10, 0), 10)
            self.assertEqual(self._apply(candidate, 10, 40, active=False), 10)

    def test_no_hidden_fifth_research_candidate(self):
        self.assertEqual(len(r2.PROFILES), 4)
        self.assertEqual(r2.PROFILES[0], "baseline")
        with self.assertRaises(ValueError):
            r2.LocalWriteRule("post_h0_write_off", set())

    def test_h0_scan_does_not_execute_continuation(self):
        def mock_h0(seed):
            arrays = {field: [0] for field in AUTHORITATIVE_FIELDS}
            b = {"arrays": {k: list(v) for k,v in arrays.items()}}
            h = {"arrays": {k: list(v) for k,v in arrays.items()}}
            control = {"arrays": {k: list(v) for k,v in arrays.items()}}
            if seed < 560:
                b["arrays"]["slow_trace"] = [1]
                h["arrays"]["slow_trace"] = [2]
            return {"b":b,"h":h,"control":control}
        with ExitStack() as stack:
            stack.enter_context(patch.object(r2, "h0_branches", side_effect=mock_h0))
            stack.enter_context(patch.object(r2, "canonical_digest", side_effect=lambda value: str(value)))
            stack.enter_context(patch("core.experiment.IOExperiment._advance", side_effect=AssertionError("read post-h0")))
            selected=r2.qualify()
        self.assertEqual(selected["positive_seeds"], list(range(544,560)))
        self.assertEqual(selected["negative_seeds"], list(range(560,568)))
        self.assertEqual(selected["max_qualification_horizon"], 0)
        self.assertTrue(set(selected["positive_seeds"]).isdisjoint(range(0,544)))
        self.assertNotIn("post_h0_write_off", selected["profiles"])

    def test_engine_drift_rejected(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from research.phase_g_memory_search_159 import _digest
        with TemporaryDirectory() as folder:
            wrong={"issue":175,"base_main":r2.BASE_MAIN,"engine_sha256":"0"*64}
            wrong["digest"]=_digest(wrong)
            file=Path(folder)/"frozen.json"
            file.write_text(json.dumps(wrong),encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "engine has changed"):
                r2.load_frozen(file)


if __name__ == "__main__":
    unittest.main()
