"""PERF230 P4.4 artifact trust-boundary RED/GREEN validation contract."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from benchmarks.perf230_cross_job_handoff_244 import (
    EXPOSED_PERF_SEED, EXPECTED_FULL_SELECTED, TRANSFER_SCHEMA,
    canonical_bytes, hash_bytes, validate_transfer,
)
from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig


class CrossJobHandoffContractTests(unittest.TestCase):
    def test_rejects_source_seed_generation_digest_and_config_drift(self) -> None:
        source = "a" * 40
        snapshot = {"sample": "a completed original selected v7 snapshot digest contract"}
        valid = {
            "schema": TRANSFER_SCHEMA,
            "source_sha": source,
            "seed": EXPOSED_PERF_SEED,
            "selected_generation": 1,
            "last_selected_v7_sha256": EXPECTED_FULL_SELECTED[0],
            "selected_snapshot_sha256": hash_bytes(canonical_bytes(snapshot)),
            "experiment": ExperimentConfig().to_dict(),
            "physics": PhysicsConfig().to_dict(),
        }
        # The real expensive native snapshot validity is checked separately
        # in both actual original selected128 Action stages; here isolate
        # transfer metadata rejection.
        with patch("benchmarks.perf230_cross_job_handoff_244.checked_state") as check:
            validate_transfer(snapshot, valid, actual_source=source)
            check.assert_called_once()
            for field, bad in (
                ("schema", "other"),
                ("source_sha", "b" * 40),
                ("seed", 16384),
                ("selected_generation", 0),
                ("last_selected_v7_sha256", "0" * 64),
                ("selected_snapshot_sha256", "0" * 64),
                ("experiment", {}),
                ("physics", {}),
            ):
                with self.subTest(field=field):
                    rejected = copy.deepcopy(valid)
                    rejected[field] = bad
                    with self.assertRaises(AssertionError):
                        validate_transfer(snapshot, rejected, actual_source=source)
            modified = {"sample": "tampered"}
            with self.assertRaises(AssertionError):
                validate_transfer(modified, valid, actual_source=source)


if __name__ == "__main__":
    unittest.main()
