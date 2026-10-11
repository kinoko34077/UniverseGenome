"""D16.6 source-evidence and stage1 manifest fault tests (no original physics run)."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from research.d16_two_stage_seed0_pilot_217 import (
    FROZEN_NATIVE_V7, check_stage1_evidence, main, source_sha,
)
from research.d16_twojob_run_control_217 import D16BoundaryError, hash_of

SRC = "a"*40


class D16Seed0StageIntegrationGuards(TestCase):
    def test_observer_byte_digest_is_not_accepted_from_manifest_shape_alone(self):
        ledger = {
            "selected_post_v7_sha256": FROZEN_NATIVE_V7[0],
            "evaluated_native_worlds": 128, "selected_native_worlds": 128,
            "d15_journal_chain_verified": True,
            "original_selected_once_proven_by_D15_final": True,
        }
        complete = {
            "ordinal":1, "seed":0, "source_sha":SRC,
            "selected_v7_sha256":FROZEN_NATIVE_V7[0],
            "d15_verified_observer":ledger, "global_wall_ms":1000,
        }
        manifest={"observer_ledger_sha256":hash_of(ledger),"elapsed_global_ms":1001}
        check_stage1_evidence(complete,manifest,source=SRC)
        for broken in (
            {**manifest,"observer_ledger_sha256":"b"*64},
            {**manifest,"elapsed_global_ms":999},
        ):
            with self.assertRaises(D16BoundaryError):
                check_stage1_evidence(complete,broken,source=SRC)
        wrong={**complete,"d15_verified_observer":{
            **ledger,"d15_journal_chain_verified":False,
        }}
        with self.assertRaises(D16BoundaryError):
            check_stage1_evidence(wrong,manifest,source=SRC)

    def test_stage2_missing_inbound_cannot_create_original_selected_round(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("research.d16_two_stage_seed0_pilot_217.source_sha", return_value=SRC):
                from research.d16_two_stage_seed0_pilot_217 import run_second
                with self.assertRaises(FileNotFoundError):
                    run_second(Path(folder)/"absent",Path(folder)/"out")
            self.assertFalse((Path(folder)/"out").exists())

    def test_no_cli_option_can_set_original_science_seed(self):
        with patch("sys.argv", ["d16_test", "--stage","first","--out","unused",
                                 "--seed","16384"]):
            with self.assertRaises(SystemExit) as raised:
                main()
        self.assertEqual(raised.exception.code,2)
