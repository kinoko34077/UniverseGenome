"""D6 #184 physical transfer conservation, slot-life epoch and role guards."""
import unittest

import core.physics as physics
from core.state import Lifecycle, SHAPE_SINGLE, UniverseState
from research import d6_preterminal_contact_184 as d6


class D6ContactTests(unittest.TestCase):
    def test_actual_conservative_transfer_is_native_physics(self):
        cfg=physics.PhysicsConfig(max_cells=3,trace_transfer_cap=8)
        st=UniverseState(seed=4,max_cells=3,config=cfg)
        st.lifecycle=[Lifecycle.ACTIVE,Lifecycle.ACTIVE,Lifecycle.FREE]
        st.structure=[SHAPE_SINGLE,SHAPE_SINGLE,0]
        st.slow_trace=bytearray([31,1,0])
        physics._transfer_slow_trace(st,cfg,((0,1),))
        self.assertEqual(sum(st.slow_trace),32)
        self.assertLess(st.slow_trace[0],31)
        self.assertGreater(st.slow_trace[1],1)

    def test_slot_reuse_is_not_original_lifetime(self):
        ep=d6.epoch_for_slot([Lifecycle.ACTIVE,Lifecycle.FREE,Lifecycle.BLACK_HOLE])
        self.assertEqual(ep,[0,-1,0])
        item={"slot_a":1,"slot_b":2,"epoch_a":0,"epoch_b":0,
              "before_a":10,"before_b":3,"after_a":6,"after_b":7}
        self.assertTrue(d6.same_epoch_contact(item,slot=1,epoch=0))
        self.assertFalse(d6.same_epoch_contact(item,slot=1,epoch=1))
        self.assertEqual(d6.outbound_units(item,slot=1),4)
        self.assertEqual(d6.outbound_units(item,slot=2),0)
        self.assertEqual(d6.recipient_pair(item,donor_slot=1),(2,0))

    def test_no_nonphysical_pair_reference(self):
        event={"slot_a":1,"slot_b":2,"before_a":0,"before_b":0,"after_a":0,"after_b":0}
        with self.assertRaises(ValueError):
            d6.outbound_units(event,slot=3)
        with self.assertRaises(ValueError):
            d6.recipient_pair(event,donor_slot=3)

    def test_r2_only_outcome_exposed_no_future_seeds(self):
        frozen=d6.load_frozen()
        selected=d6.roster(frozen)
        self.assertEqual(len(selected),24)
        self.assertEqual(len(set(selected)),24)
        self.assertTrue(all(544<=s<1024 for s in selected))
        self.assertFalse(set(selected)&set(range(0,544)))
        self.assertEqual(set(d6.EXPOSED_TERMINAL_LOSS),{555,556,560,563,575,582})
        with self.assertRaises(ValueError):
            d6.case_once(4096,frozen)

    def test_protocol_forbids_causal_or_learning_inference(self):
        self.assertEqual(d6.PROTOCOL["learning_claim"],False)
        self.assertIn("not proof",d6.PROTOCOL["inference"])
        self.assertEqual(d6.SHARDS*d6.SHARD_SIZE,24)
        self.assertIn("observational",d6.PROTOCOL["mode"])


if __name__=="__main__":
    unittest.main()
