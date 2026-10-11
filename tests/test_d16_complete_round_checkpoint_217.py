"""D16 #217 authentic complete one-round fixture: benchmark seed0, no D16 study."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d16_complete_round_checkpoint_217 import (
    D16BoundaryError, one_authentic_selected_round,
    read_completed, write_completed_atomic,
)
from research.d16_twojob_run_control_217 import GlobalClock, utc_now_ms

SOURCE = "c"*40
SHORT_ORIGINAL_GOLDEN = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"


class CompletedNativeRoundTests(unittest.TestCase):
    def test_true_original_short_seed0_selected128_and_readonly_observer_checkpoint(self):
        start = time.monotonic()
        clock = GlobalClock(utc_now_ms() - 1000)
        actual = one_authentic_selected_round(
            source_sha=SOURCE, seed=0, ordinal=1, predecessor=None,
            experiment=ExperimentConfig(evaluation_timeout_generations=2),
            physics=PhysicsConfig(), clock=clock,
            job_started_monotonic=start, workers=1,
        )
        self.assertEqual(actual["selected_v7_sha256"], SHORT_ORIGINAL_GOLDEN)
        self.assertEqual(actual["d15_verified_observer"]["selected_post_v7_sha256"],
                         SHORT_ORIGINAL_GOLDEN)
        self.assertEqual(actual["d15_verified_observer"]["evaluated_native_worlds"], 128)
        self.assertEqual(actual["d15_verified_observer"]["actual_native_replacement_count"], 0)
        self.assertFalse(actual["learning_claim"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = write_completed_atomic(root, actual)
            original_bytes = dest.read_bytes()
            self.assertEqual(read_completed(dest, source_sha=SOURCE, seed=0, ordinal=1),
                             actual)
            self.assertEqual(dest.read_bytes(), original_bytes)
            with self.assertRaises(FileExistsError):
                write_completed_atomic(root, actual)
            with self.assertRaises(D16BoundaryError):
                read_completed(dest, source_sha="d"*40, seed=0, ordinal=1)
            tampered = json.loads(dest.read_bytes())
            tampered["payload"]["seed"] = 16384
            dest.write_text(json.dumps(tampered))
            with self.assertRaises(D16BoundaryError):
                read_completed(dest, source_sha=SOURCE, seed=0, ordinal=1)

    def test_expired_clock_fails_before_any_native_evaluation(self):
        with self.assertRaises(D16BoundaryError):
            one_authentic_selected_round(
                source_sha=SOURCE, seed=0, ordinal=1, predecessor=None,
                experiment=ExperimentConfig(evaluation_timeout_generations=2),
                physics=PhysicsConfig(),
                clock=GlobalClock(utc_now_ms() - 1900_000),
                job_started_monotonic=time.monotonic(),workers=1,
            )

    def test_nondefault_original_seed_protocol_rejected_before_evaluation(self):
        with self.assertRaises(D16BoundaryError):
            one_authentic_selected_round(
                source_sha=SOURCE, seed=16384, ordinal=1, predecessor=None,
                experiment=ExperimentConfig(evaluation_timeout_generations=2),
                physics=PhysicsConfig(),clock=GlobalClock(utc_now_ms()),
                job_started_monotonic=time.monotonic(),workers=1,
            )


if __name__ == "__main__":
    unittest.main()
