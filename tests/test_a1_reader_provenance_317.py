"""A1 #317 source-native read-only selected-reader provenance contract."""
import copy
import unittest

import core.physics as physics
from core.state import Lifecycle
from research.a1_reader_provenance_317 import (
    ReadOnlyReaderProvenance, compare_branches, SCHEMA,
)


class A1ReaderProvenanceTests(unittest.TestCase):
    def fixture(self, trace):
        config = physics.PhysicsConfig(
            max_cells=8, initial_density=2, trace_bonus_shift=5,
        )
        state = physics.create_universe(seed=7, config=config)
        a, b = state.active_slots()[:2]
        state.slow_trace[a] = trace
        state.slow_trace[b] = 0
        state.bond_strength[a] = 0
        state.bond_strength[b] = 0
        state.latent[a] = 0xAAAA
        state.latent[b] = 0x5555
        return state, a, b

    def execute(self, trace):
        state, a, b = self.fixture(trace)
        reference = copy.deepcopy(state)
        source_trace = bytes(state.slow_trace)
        native_result = physics._transmit_latent(
            reference, reference.config, {(a, b)}, {(a, b): 19}, 11,
            bytes(reference.slow_trace),
        )
        original_mask = physics.transmission_mask
        original_transmit = physics._transmit_latent
        observer = ReadOnlyReaderProvenance(state)
        with observer.attach():
            selected_result = physics._transmit_latent(
                state, state.config, {(a, b)}, {(a, b): 19}, 11,
                source_trace,
            )
        self.assertIs(physics.transmission_mask, original_mask)
        self.assertIs(physics._transmit_latent, original_transmit)
        self.assertEqual(selected_result, native_result)
        self.assertEqual(state.to_snapshot(), reference.to_snapshot())
        self.assertEqual(len(observer.events), 2)
        for event in observer.events:
            self.assertEqual(event["recipient_latent_after"],
                             state.latent[event["recipient_slot"]])
            self.assertEqual(event["native_mask"].bit_count(),
                             event["effective_width"])
            self.assertEqual(event["source_epoch"], 0)
            self.assertEqual(event["recipient_epoch"], 0)
        source_event = next(x for x in observer.events if x["source_slot"] == a)
        self.assertEqual(source_event["source_trace_start"], trace)
        self.assertEqual(source_event["recipient_slot"], b)
        self.assertEqual(source_event["recipient_latent_before"], 0x5555)
        return observer.events

    def test_read_only_native_selected_pair_and_mask_direction(self):
        self.execute(31)

    def test_actual_native_quantization_width_opportunity_not_learning(self):
        b = self.execute(31)
        h = self.execute(32)
        report = compare_branches(b, h)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["counts"]["matched_selected_read_events"], 2)
        self.assertEqual(report["counts"]["matched_trace_different"], 1)
        self.assertEqual(report["counts"]["unconfounded_width_opportunity"], 1)
        self.assertEqual(report["counts"]["unconfounded_mask_opportunity"], 1)
        self.assertFalse(report["learning_claim"])
        self.assertFalse(report["independent_confirmation"])

    def test_epoch_changes_only_at_native_spawn_after_free(self):
        config = physics.PhysicsConfig(max_cells=8, initial_density=0)
        state = physics.create_universe(seed=7, config=config)
        recorder = ReadOnlyReaderProvenance(state)
        self.assertEqual(recorder.epochs[0], -1)
        with recorder.attach():
            slot = state.spawn(x=0, y=0)
            self.assertEqual((slot, recorder.epochs[slot]), (0, 0))
            state.free(slot)
            self.assertEqual(state.lifecycle[slot], Lifecycle.FREE)
            self.assertEqual(recorder.free_events[-1]["life_epoch"], 0)
            slot2 = state.spawn(x=0, y=0)
            self.assertEqual((slot2, recorder.epochs[slot2]), (0, 1))

    def test_no_fabricated_or_duplicate_physical_events(self):
        events = self.execute(31)
        with self.assertRaises(ValueError):
            compare_branches(events + [events[0]], events)
        with self.assertRaises(ValueError):
            compare_branches([{"native_generation": 11}], [])
        with self.assertRaises(ValueError):
            compare_branches([{**events[0], "recipient_latent_after": None}], [])
        with self.assertRaises(ValueError):
            ReadOnlyReaderProvenance(self.fixture(31)[0], event_limit=0)
        report = compare_branches(events, [], example_limit=0)
        self.assertEqual(report["counts"]["unmatched_topology"], 2)
        self.assertEqual(report["examples"], [])


if __name__ == "__main__":
    unittest.main()
