"""D16.10 public GitHub fixture may never run original reserved science seed."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest

from research.d16_incremental_native_seed0_pilot_217 import (
    FIXTURE_SEED, FROZEN_V7, execute, isolated_handoff_folder,
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

    def test_second_host_copies_complete_prefix_without_mutating_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbound = Path(tmp) / "inbound"
            out = Path(tmp) / "out"
            inbound.mkdir()
            (inbound / "stage1-manifest.json").write_text('{"first_job_start_unix_ms":1700000000000}')
            (inbound / "selected-round-01.json").write_bytes(b"immutable-original-v7")
            before = {p.name: p.read_bytes() for p in inbound.iterdir()}
            working = isolated_handoff_folder(inbound, out)
            self.assertEqual(working, out)
            self.assertEqual({p.name: p.read_bytes() for p in inbound.iterdir()}, before)
            self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)
            (out / "selected-round-02.json").write_bytes(b"second-host")
            self.assertNotIn("selected-round-02.json", [p.name for p in inbound.iterdir()])

    def test_second_host_rejects_reusing_input_or_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbound = Path(tmp) / "inbound"
            inbound.mkdir()
            (inbound / "stage1-manifest.json").write_text("{}")
            with self.assertRaises(D16BoundaryError):
                isolated_handoff_folder(inbound, inbound)
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "existing.json").write_text("{}")
            with self.assertRaises(D16BoundaryError):
                isolated_handoff_folder(inbound, out)

    def test_third_hosted_job_rejected_before_physics(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(D16BoundaryError):
                execute(3, inbound=None, out=Path(tmp))


if __name__=="__main__":
    unittest.main()
