"""PERF230 P4.3: original output-signal oracle and bounded early-exit RED test."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from core.io_bus import FixedOrgans, OutputSignal, read_output_signal
from core.physics import destination_footprint
from core.state import Lifecycle, SHAPE_SINGLE, UniverseState


def original_reference(state: UniverseState) -> OutputSignal:
    # Original accepted main implementation, independent of trial masks.
    coordinates = FixedOrgans.coordinates()
    occupied: set[tuple[int, int]] = set()
    for slot in state.active_slots():
        occupied.update(destination_footprint(
            state.structure[slot], state.x[slot], state.y[slot],
        ))
    value = sum(1 << bit for bit in range(8)
                if coordinates[f"OUT{bit}"] in occupied)
    return OutputSignal(
        value=value,
        valid=coordinates[FixedOrgans.output_valid] in occupied,
        null=coordinates[FixedOrgans.output_null] in occupied,
    )


class OutputObservationP43Tests(unittest.TestCase):
    def test_reference_parity_sparse_dense_wrap_and_lifecycle(self) -> None:
        samples = (0, 1, 2, 3, 4, 7, 15, 16, 63, 255, 256,
                   0x3333, 0x5555, 0xAAAA, 0xFFFF)
        positions = ((0, 0), (248, 248), (192, 96), (200, 248),
                     (192, 248), (191, 95), (8, 16), (192, 136))
        for shape in samples:
            for x, y in positions:
                with self.subTest(shape=shape, x=x, y=y):
                    state = UniverseState(seed=0, max_cells=32)
                    state.spawn(x=x, y=y, structure=shape)
                    state.spawn(x=192, y=136, structure=3)
                    state.spawn(x=192, y=144, structure=1)
                    state.lifecycle[1] = int(Lifecycle.BLACK_HOLE)
                    state.lifecycle[2] = int(Lifecycle.FREE)
                    before = state.to_snapshot()
                    self.assertEqual(read_output_signal(state), original_reference(state))
                    self.assertEqual(state.to_snapshot(), before)

        dense = UniverseState(seed=0, max_cells=96)
        for i in range(64):
            dense.spawn(x=(i * 13) & 255, y=(i * 37) & 255,
                        structure=samples[i % len(samples)])
        for i in range(0, 64, 9):
            dense.lifecycle[i] = int(Lifecycle.BLACK_HOLE)
        self.assertEqual(read_output_signal(dense), original_reference(dense))
        self.assertEqual(read_output_signal(UniverseState(seed=0)),
                         OutputSignal())

    def test_coordinate_override_and_duplicate_output_tiles(self) -> None:
        state = UniverseState(seed=0, max_cells=16)
        state.spawn(x=192, y=96, structure=SHAPE_SINGLE)
        coordinates = FixedOrgans.coordinates()
        coordinates["OUT0"] = coordinates["OUT1"]
        coordinates[FixedOrgans.output_null] = coordinates[FixedOrgans.output_valid]
        with patch.object(FixedOrgans, "coordinates", return_value=coordinates):
            self.assertEqual(read_output_signal(state), original_reference(state))

    def test_all_output_lines_allow_bounded_early_exit(self) -> None:
        coordinates = FixedOrgans.coordinates()
        state = UniverseState(seed=0, max_cells=64)
        for name in (*FixedOrgans.output_data, FixedOrgans.output_valid,
                     FixedOrgans.output_null):
            x, y = coordinates[name]
            state.spawn(x=x * 8, y=y * 8, structure=SHAPE_SINGLE)
        for index in range(30):
            state.spawn(x=(index * 8) % 256, y=0, structure=SHAPE_SINGLE)
        self.assertEqual(read_output_signal(state), original_reference(state))
        with patch("core.physics.destination_footprint", wraps=destination_footprint) as used:
            result = read_output_signal(state)
        self.assertEqual(result, OutputSignal(value=255, valid=True, null=True))
        # This intentionally RED-fails the accepted full-world-occupancy reader.
        self.assertEqual(used.call_count, 10)


if __name__ == "__main__":
    unittest.main()
