"""D5 #181 unit physical receiver geometry and protected cohort tests."""
import unittest

from core.physics import PhysicsConfig
from core.state import Lifecycle, SHAPE_SINGLE, UniverseState
from research import d5_pending_free_viability_181 as d5


class RecipientViabilityTests(unittest.TestCase):
    def state(self, donor=20, recipient=250, adjacent=True, enabled=True):
        cfg=PhysicsConfig(max_cells=3,trace_discharge_cap=16)
        st=UniverseState(seed=1,max_cells=3,config=cfg)
        st.lifecycle=[Lifecycle.BLACK_HOLE,Lifecycle.ACTIVE if enabled else Lifecycle.FREE,Lifecycle.FREE]
        st.structure=[SHAPE_SINGLE,SHAPE_SINGLE,0]
        st.x=[0,0 if adjacent else 64,0]
        st.y=[0,0 if adjacent else 64,0]
        st.slow_trace=bytearray([donor,recipient,0])
        return st

    def test_exact_physical_overlap_and_uint8_headroom(self):
        st=self.state()
        before=st.to_snapshot()
        info=d5.eligible_recipients(st,0)
        self.assertEqual(info["local_active_count"],1)
        self.assertEqual(info["potential_units_total_at_most"],5)
        self.assertEqual(info["recipients"][0]["slot"],1)
        self.assertEqual(st.to_snapshot(),before)

    def test_no_recipient_no_headroom_no_donor(self):
        for st in [self.state(adjacent=False),
                   self.state(enabled=False),
                   self.state(recipient=255),
                   self.state(donor=0)]:
            self.assertEqual(d5.eligible_recipients(st,0)["potential_units_total_at_most"],0)

    def test_reject_non_black_hole_source(self):
        st=self.state()
        st.lifecycle[0]=Lifecycle.ACTIVE
        with self.assertRaisesRegex(ValueError,"BLACK_HOLE"):
            d5.eligible_recipients(st,0)

    def test_frozen_exposed_roster_only(self):
        f=d5.load_frozen()
        cohort=d5.authorized_seeds(f)
        self.assertEqual(len(cohort),24)
        self.assertEqual(len(set(cohort)),24)
        self.assertTrue(all(544<=s<1024 for s in cohort))
        self.assertEqual(set(d5.EXPOSED_LOSS_GENERATIONS),{555,556,560,563,575,582})
        self.assertFalse(set(cohort)&set(range(0,544)))
        with self.assertRaisesRegex(ValueError,"novel or reserved"):
            d5.observed_case(4096,f,validate=False)

    def test_no_promotion_and_exploratory_only(self):
        self.assertEqual(d5.PROTOCOL["issue"],181)
        self.assertIn("EXPLORATORY",d5.PROTOCOL["role"])
        self.assertEqual(d5.PROTOCOL["operator"],"R2 unit_add unchanged and physics native final pending_free")
        self.assertFalse(d5.PROTOCOL.get("learning_claim",True))
        self.assertEqual(d5.SHARDS*d5.CASES_PER_SHARD,24)


if __name__=="__main__":
    unittest.main()
