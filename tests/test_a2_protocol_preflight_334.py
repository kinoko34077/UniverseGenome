"""#334: policy/source-bound validator for NON-RUNNABLE rotate_copy protocol."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from core.physics import apply_latent_operator
from research.a2_protocol_preflight_334 import (
    MANIFEST, SCHEMA, validate_nonexecuting_draft, validate_saved_draft,
)
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import RATE, load_frozen


class A2DesignOnlyPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_actual_frozen_reference_and_one_factor_delta_without_native_step(self):
        r=validate_saved_draft()
        self.assertEqual(r["status"],"VALID_DRAFT_ONLY_NO_EXECUTION")
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["changed_fields"],["latent_operator"])
        self.assertEqual(r["previously_outcome_exposed_only"],[544,545])
        self.assertFalse(r["can_run_actions"])
        self.assertFalse(r["learning_claim"])
        original=profile(RATE)
        changed=replace(original, latent_operator="rotate_copy")
        self.assertEqual(original.latent_operator,"masked_copy")
        self.assertEqual(changed.rotate_amount,4)
        self.assertEqual(
            apply_latent_operator("rotate_copy",1,1,0x0010,rotate_amount=4),
            17,
        )
        frozen=load_frozen()
        self.assertEqual(frozen["h0_evidence"]["545"]["b_digest"],
                         frozen["h0_evidence"]["545"]["h_digest"])
        self.assertNotEqual(frozen["h0_evidence"]["544"]["b_digest"],
                            frozen["h0_evidence"]["544"]["h_digest"])
        defaults=json.loads(Path("config/default.json").read_text())["physics"]
        self.assertEqual(defaults["latent_operator"],"masked_copy")
        self.assertEqual(
            [defaults[k] for k in (
                "trace_write_cap","trace_transfer_cap",
                "trace_discharge_cap","trace_decay_rate","trace_bonus_shift",
            )],[0,0,0,0,8],
        )

    def test_unapproved_physics_or_heldout_usage_fail_closed(self):
        mutations=(
            lambda d:d["execution_permission"].update(can_run_actions=True),
            lambda d:d["execution_permission"].update(learning_claim=True),
            lambda d:d["execution_permission"].update(approval_state="ACCEPTED"),
            lambda d:d["candidate"].update(hypothetical_operator="masked_xor"),
            lambda d:d["candidate"].update(rotate_amount=5),
            lambda d:d["candidate"].update(production_default_change=True),
            lambda d:d["candidate"].update(only_permitted_post_h0_config_change="initial_density"),
            lambda d:d["seed_partition"].update(exploratory_this_draft=[96,544]),
            lambda d:d["seed_partition"].update(independent_R3_seeds_to_be_selected_by_this_draft=[1024]),
            lambda d:d["seed_partition"].update(heldout_consumed=True),
            lambda d:d["exposed_exploratory_only"].update(physical_steps=1001),
            lambda d:d["exposed_exploratory_only"].update(negative_BH_identical_required=False),
            lambda d:d["exposed_exploratory_only"].update(candidate_post_h0_old_baseline_checkpoint_parity_expected=True),
            lambda d:d["bounds"].update(max_rss_mib=1537),
            lambda d:d["bounds"].update(posthoc_tuning=True),
            lambda d:d.update(original_r2_frozen_manifest_digest="0"*64),
        )
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index):
                proposal=deepcopy(self.plan)
                mutate(proposal)
                with self.assertRaises(ValueError):
                    validate_nonexecuting_draft(proposal)

    def test_default_is_not_modified_by_read_only_check(self):
        original=json.dumps(self.plan,sort_keys=True)
        validate_nonexecuting_draft(self.plan)
        self.assertEqual(json.dumps(self.plan,sort_keys=True),original)


if __name__=="__main__":
    unittest.main()
