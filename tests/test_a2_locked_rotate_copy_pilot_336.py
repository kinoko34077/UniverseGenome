"""A2 E1b #336: source-only DENIAL and original control planning tests.

DOES NOT invoke original R2 h0, create_universe, step or new seed.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from unittest import TestCase, mock

from research.a2_locked_rotate_copy_pilot_336 import (
    SCHEMA, candidate_config, execution_gate,
    run_accepted_research_only,
)
from research.a2_protocol_preflight_334 import MANIFEST


SHA="0"*40


class SourceLockedResearchNoExecution(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_original_operator_only_one_research_field(self):
        original,candidate=candidate_config()
        a,b=asdict(original),asdict(candidate)
        self.assertEqual([k for k in a if a[k]!=b[k]],["latent_operator"])
        self.assertEqual(a["latent_operator"],"masked_copy")
        self.assertEqual(b["latent_operator"],"rotate_copy")
        self.assertEqual(b["rotate_amount"],4)
        self.assertEqual(self.plan["execution_permission"]["approval_state"],"HOLD")
        self.assertFalse(self.plan["execution_permission"]["can_run_actions"])
        self.assertEqual(SCHEMA,"UG_A2_RESEARCH_ONLY_ROTATE_COPY_EXPOSED_PILOT_V1")
        self.assertEqual(self.plan["seed_partition"]["exploratory_this_draft"],[544,545])
        self.assertEqual(self.plan["seed_partition"]["independent_R3_seeds_to_be_selected_by_this_draft"],[])

    def test_explicit_source_gate_denies_before_any_original_native_seed(self):
        with mock.patch("research.a2_locked_rotate_copy_pilot_336.load_frozen",
                        side_effect=AssertionError("must not read when HOLD")), \
             mock.patch("research.a2_locked_rotate_copy_pilot_336.h0_branches",
                        side_effect=AssertionError("must not qualify/run R2 h0")), \
             mock.patch("research.a2_locked_rotate_copy_pilot_336.old_masked_copy_reference",
                        side_effect=AssertionError("must not call native R2")):
            for consent in (False, True):
                with self.subTest(consent=consent),self.assertRaises(PermissionError):
                    run_accepted_research_only(
                        plan=deepcopy(self.plan),
                        named_approval=consent,
                        source_sha=SHA,
                    )

    def test_command_flag_alone_cannot_override_original_HOLD(self):
        for change in (
            lambda p:p["execution_permission"].update(can_run_actions=True),
            lambda p:p["execution_permission"].update(approval_state="ACCEPTED"),
            lambda p:p.update(state="ACCEPTED_EXACT_RUNNABLE"),
            lambda p:p["candidate"].update(rotate_amount=2),
            lambda p:p["seed_partition"].update(exploratory_this_draft=[544,1024]),
            lambda p:p["execution_permission"].update(can_consume_heldout=True),
        ):
            altered=deepcopy(self.plan)
            change(altered)
            with self.assertRaises((ValueError,PermissionError)):
                run_accepted_research_only(
                    plan=altered,named_approval=True,source_sha=SHA,
                )
        with self.assertRaises(PermissionError):
            execution_gate(plan=self.plan,named_approval=True,source_sha="invalid")
        self.assertFalse(self.plan["execution_permission"]["learning_claim"])

    def test_current_default_is_unchanged_and_no_science_workflow_exists_here(self):
        p=json.loads(Path("config/default.json").read_text(encoding="utf-8"))
        self.assertEqual(p["physics"]["latent_operator"],"masked_copy")
        self.assertEqual([
            p["physics"][k] for k in (
                "trace_write_cap","trace_transfer_cap","trace_discharge_cap",
                "trace_decay_rate","trace_bonus_shift",
            )
        ],[0,0,0,0,8])
