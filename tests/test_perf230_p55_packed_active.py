"""P5.5 original C list.index ACTIVE slots vs packed native lifecycle parity."""
import unittest
from core.state import UniverseState, Lifecycle


def prior_source_active_slots(state):
    active=int(Lifecycle.ACTIVE)
    idx=[]
    start=0
    while True:
        try:slot=state.lifecycle.index(active,start)
        except ValueError:return idx
        idx.append(slot)
        start=slot+1


class PackedNativeActiveOracleTests(unittest.TestCase):
    def test_empty_blackhole_and_dense_sparse_positions_exact(self):
        for capacity in (1,2,16,64,1024,2048):
            for pattern in ((),(0,),(capacity-1,),
                            tuple(range(0,capacity,11)),
                            tuple(range(capacity))):
                state=UniverseState(seed=7,max_cells=capacity)
                state.lifecycle=[int(Lifecycle.BLACK_HOLE) if i%13==0
                                 else int(Lifecycle.FREE) for i in range(capacity)]
                for i in pattern:state.lifecycle[i]=int(Lifecycle.ACTIVE)
                before=list(state.lifecycle)
                self.assertEqual(state.active_slots(),prior_source_active_slots(state))
                self.assertEqual(state.lifecycle,before)

    def test_int_enum_and_interleaved_lifecycle_mutation_exact(self):
        state=UniverseState(seed=5,max_cells=64)
        state.lifecycle=[Lifecycle.FREE]*64
        for i in (0,3,17,30,63):state.lifecycle[i]=Lifecycle.ACTIVE
        for i in (2,4,20,55):state.lifecycle[i]=Lifecycle.BLACK_HOLE
        for new in (
            None,
            (3,Lifecycle.FREE),
            (14,Lifecycle.ACTIVE),
            (63,Lifecycle.BLACK_HOLE),
            (3,Lifecycle.ACTIVE),
            (0,Lifecycle.FREE),
        ):
            if new:
                i,value=new
                state.lifecycle[i]=value
            self.assertEqual(state.active_slots(),prior_source_active_slots(state))

    def test_nonbyte_lifecycle_fallback_original_behavior(self):
        for invalid in (-1,256,999,1.5,"inert"):
            state=UniverseState(seed=11,max_cells=8)
            state.lifecycle=[0,2,1,0,invalid,0,1,0]
            self.assertEqual(state.active_slots(),prior_source_active_slots(state))
        class EqualOneNoByte:
            def __eq__(self,other):return other==1
        state=UniverseState(seed=3,max_cells=4)
        state.lifecycle=[0,EqualOneNoByte(),2,1]
        self.assertEqual(state.active_slots(),prior_source_active_slots(state))


if __name__=="__main__":
    unittest.main()
