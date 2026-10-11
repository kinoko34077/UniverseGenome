"""P5.1 original read_output_signal zero-ACTIVE source parity with full occupied-set oracle."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from core.io_bus import FixedOrgans, OutputSignal, read_output_signal
from core.physics import destination_footprint
from core.state import Lifecycle, UniverseState


def original_reader(state: UniverseState) -> OutputSignal:
    coordinates=FixedOrgans.coordinates()
    occupied=set()
    for slot in state.active_slots():
        occupied.update(destination_footprint(
            state.structure[slot],state.x[slot],state.y[slot]
        ))
    return OutputSignal(
        value=sum(1<<bit for bit in range(8) if coordinates[f"OUT{bit}"] in occupied),
        valid=coordinates[FixedOrgans.output_valid] in occupied,
        null=coordinates[FixedOrgans.output_null] in occupied,
    )


class P51ZeroActiveReadTests(unittest.TestCase):
    def test_zero_active_free_and_blackhole_cannot_emit(self):
        for stage in ("free","blackhole"):
            state=UniverseState(seed=8,max_cells=64)
            if stage=="blackhole":
                state.spawn(x=192,y=96,structure=0xFFFF)
                state.lifecycle[0]=int(Lifecycle.BLACK_HOLE)
            snap=state.to_snapshot()
            self.assertEqual(original_reader(state),OutputSignal())
            with patch.object(FixedOrgans,"coordinates",
                              side_effect=AssertionError("unneeded organs on empty state")):
                self.assertEqual(read_output_signal(state),OutputSignal())
            self.assertEqual(state.to_snapshot(),snap)

    def test_nonempty_sparse_dense_shape_bh_and_aliased_organs(self):
        for count in (1,2,7,18,40):
            state=UniverseState(seed=5,max_cells=96)
            shapes=(0,1,2,3,4,15,255,0x5555,0xFFFF)
            for index in range(count):
                state.spawn(x=(index*13+192)%256,
                            y=(index*29+96)%256,
                            structure=shapes[index%len(shapes)])
            for i in range(1,count,9):
                state.lifecycle[i]=int(Lifecycle.BLACK_HOLE)
            before=state.to_snapshot()
            self.assertEqual(read_output_signal(state),original_reader(state))
            original=FixedOrgans.coordinates()
            original["OUT0"]=original["OUT1"]
            original[FixedOrgans.output_null]=original[FixedOrgans.output_valid]
            with patch.object(FixedOrgans,"coordinates",return_value=original):
                self.assertEqual(read_output_signal(state),original_reader(state))
            self.assertEqual(state.to_snapshot(),before)


if __name__=="__main__":
    unittest.main()
