"""D16.10 public GitHub fixture may never run original reserved science seed."""
from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

from research.d16_incremental_native_seed0_pilot_217 import (
    FIXTURE_SEED, FROZEN_V7, execute,
)
from research.d16_twojob_run_control_217 import D16BoundaryError


class OnlyExposedSeed0IntegrationGateTests(unittest.TestCase):
    def test_no_seed_flag_or_reserved_study_parameter(self):
        self.assertEqual(FIXTURE_SEED, 0)
        self.assertEqual(len(FROZEN_V7), 2)
        self.assertNotIn("seed", inspect.signature(execute).parameters)

    def test_first_job_refuses_external_carry_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(D16BoundaryError):
                execute(1, inbound=Path(tmp), out=Path(tmp))

    def test_second_job_refuses_absent_authenticated_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(D16BoundaryError):
                execute(2, inbound=None, out=Path(tmp))

    def test_third_hosted_job_rejected_before_physics(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(D16BoundaryError):
                execute(3, inbound=None, out=Path(tmp))


if __name__=="__main__":
    unittest.main()
