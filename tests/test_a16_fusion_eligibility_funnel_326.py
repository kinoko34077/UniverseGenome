"""Source-only A1.6 fusion gate funnel: stage/negative fixtures."""
from dataclasses import replace
import unittest

from core.physics import _fusion_candidates, destination_footprint
from core.state import SHAPE_SINGLE
from research.a16_fusion_eligibility_funnel_326 import (
    STAGES, native_fusion_eligibility_funnel,
)
from tests.test_a16_native_latent_diversity_feasibility_326 import (
    NativeLatentDiversityFeasibility,
)


def occupancy_of(state):
    occupied = {}
    for slot in state.active_slots():
        for tile in destination_footprint(
            state.structure[slot], state.x[slot], state.y[slot]
        ):
            occupied.setdefault(tile, []).append(slot)
    return occupied


class FusionGateFunnelContract(unittest.TestCase):
    def test_exact_native_gate_positive_no_mutation_and_replay(self):
        a = NativeLatentDiversityFeasibility._four_single_cover(bonds=33)
        occ = occupancy_of(a)
        before = a.to_snapshot()
        x = native_fusion_eligibility_funnel(a, occ, a.config)
        y = native_fusion_eligibility_funnel(a, occ, a.config)
        self.assertEqual(x, y)
        self.assertEqual(a.to_snapshot(), before)
        self.assertEqual(x["gate_counts"]["compatible_velocity"], 1)
        self.assertEqual(x["original_native_candidate_count"], 1)
        self.assertEqual(len(_fusion_candidates(a,occ,a.config)), 1)
        self.assertTrue(x["fuse_flag_enabled"])
        self.assertFalse(x["is_natural_evolution_evidence"])
        self.assertFalse(x["learning_claim"])

    def test_each_relevant_source_native_gate_is_not_conflated(self):
        cases = {}
        cases["geometry"] = NativeLatentDiversityFeasibility._four_single_cover(
            missing=True
        )
        mixed = NativeLatentDiversityFeasibility._four_single_cover(bonds=33)
        mixed.structure[3] = SHAPE_SINGLE << 2
        cases["same_level"] = mixed
        cases["bond"] = NativeLatentDiversityFeasibility._four_single_cover(
            bonds=31
        )
        speed = NativeLatentDiversityFeasibility._four_single_cover(bonds=33)
        speed.speed_code[3] = 7
        speed.direction[3] = 4
        cases["velocity"] = speed
        cases["off"] = NativeLatentDiversityFeasibility._four_single_cover(
            fusion=False
        )
        for name, state in cases.items():
            with self.subTest(case=name):
                before = state.to_snapshot()
                f = native_fusion_eligibility_funnel(
                    state, occupancy_of(state), state.config
                )
                self.assertEqual(state.to_snapshot(),before)
                g=f["gate_counts"]
                self.assertEqual(tuple(g),STAGES)
                if name=="geometry":
                    self.assertEqual(g["exact_cover"],0)
                elif name=="same_level":
                    self.assertGreater(g["exact_cover"],0)
                    self.assertEqual(g["same_level"],0)
                elif name=="bond":
                    self.assertGreater(g["same_level"],0)
                    self.assertEqual(g["sufficient_bond"],0)
                elif name=="velocity":
                    self.assertGreater(g["sufficient_bond"],0)
                    self.assertEqual(g["compatible_velocity"],0)
                elif name=="off":
                    # Native _fusion_candidates does not check enable flag.
                    # Original step() controls actual activation.
                    self.assertEqual(g["compatible_velocity"],1)
                    self.assertFalse(f["candidate_processing_enabled"])

    def test_reject_config_drift(self):
        x=NativeLatentDiversityFeasibility._four_single_cover()
        inconsistent=replace(x.config, bond_gain=7)
        with self.assertRaises(ValueError):
            native_fusion_eligibility_funnel(
                x, occupancy_of(x), inconsistent
            )


if __name__=="__main__":
    unittest.main()
