"""D10 #195 accepted-native trace read thresholds, no teacher injection."""
import unittest

from core.physics import PhysicsConfig, create_universe, transmission_mask
from research import d10_trace_read_gates_195 as d10


class NativeReadGateTests(unittest.TestCase):
    def test_exact_frozen_native_physics_controls(self):
        result=d10.evaluate()
        controls=result["controls"]
        self.assertTrue(controls["same_shift_bucket_10_18"]["equal"])
        self.assertEqual(controls["same_shift_bucket_10_18"]["masks"][0],
                         controls["same_shift_bucket_10_18"]["masks"][1])
        threshold=controls["threshold_crossing_31_32"]
        self.assertEqual(threshold["widths"],[1,2])
        self.assertTrue(threshold["different"])
        self.assertEqual(threshold["masks"][0]&threshold["masks"][1],threshold["masks"][0])
        self.assertEqual(controls["saturated_bond_0_255"]["width"],16)
        self.assertEqual(controls["saturated_bond_0_255"]["masks"][0],
                         controls["saturated_bond_0_255"]["masks"][1])
        self.assertEqual(controls["inert_shift_0_255"]["masks"][0],
                         controls["inert_shift_0_255"]["masks"][1])

    def test_deterministic_replay_and_no_claim(self):
        a=d10.evaluate()
        b=d10.evaluate()
        self.assertEqual(a,b)
        self.assertEqual(a["digest"],b["digest"])
        self.assertFalse(any(a["limits"].values()))
        self.assertTrue(a["controls"]["generic_write_equal"]["same_without_teacher_label"])

    def test_native_trace_shift_8_deactivates_bonus_at_u8_max(self):
        cfg=PhysicsConfig(max_cells=8,trace_bonus_shift=8)
        state=create_universe(seed=7,config=cfg)
        a=transmission_mask(7,11,19,(0,1),0,participant=state,source_trace=0)
        b=transmission_mask(7,11,19,(0,1),0,participant=state,source_trace=255)
        self.assertEqual(a,b)

    def test_source_trace_boundaries_reject_non_u8(self):
        cfg=PhysicsConfig(max_cells=8,trace_bonus_shift=5)
        state=create_universe(seed=7,config=cfg)
        with self.assertRaises(ValueError):
            transmission_mask(7,11,19,(0,1),0,participant=state,source_trace=256)
        with self.assertRaises(ValueError):
            transmission_mask(7,11,19,(0,1),0,participant=state,source_trace=-1)


if __name__=="__main__":
    unittest.main()
