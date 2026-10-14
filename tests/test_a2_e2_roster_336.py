"""E2 #336 protocol roster checks only; never executes an original seed."""
import json
from unittest import TestCase
from research.a2_e2_outcome_scoring_336 import UNRESOLVED, NEGATIVE, INVALID
from research.a2_e2_exposed_activation_336 import (
    PROTOCOL, verify_source_locked_protocol,
)


class ExposedOnlyRosterContract(TestCase):
    def test_frozen_original_roster_and_horizon(self):
        plan = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        proof = verify_source_locked_protocol(plan)
        self.assertTrue(proof["valid_source_only"])
        self.assertEqual(plan["cohorts"]["positive_exposed_seed"], 544)
        self.assertEqual(plan["cohorts"]["negative_exposed_seed"], 545)
        self.assertEqual(plan["treatment"]["steps_per_branch"], 1000)
        self.assertEqual(plan["treatment"]["candidate_operator"], "rotate_copy")
        self.assertFalse(plan["cohorts"]["new_heldout_consumed"])
        self.assertFalse(plan["decision"]["independent_learning_claim_allowed"])
        self.assertEqual(plan["decision"]["valid_local_retention_unresolved"],UNRESOLVED)
        self.assertEqual(plan["decision"]["valid_zero"],NEGATIVE)
        self.assertEqual(plan["decision"]["invalid"],INVALID)
        self.assertTrue(plan["decision"]["long_term_retention_requires_life_epoch_carrier_evidence"])
        self.assertEqual(plan["decision"]["valid_transient"],"TRANSIENT_PHYSICAL_EFFECT_NOT_L3")
        self.assertEqual(plan["decision"]["valid_persistent"],"OUTCOME_EXPOSED_RETENTION_CANDIDATE_NOT_INDEPENDENT_L3")
