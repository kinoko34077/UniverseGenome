"""#167 D1 observation-only guards, parity, provenance and counter accounting."""
from __future__ import annotations

import unittest

import core.physics as physics
from core.physics import PhysicsConfig
from research.phase_g_decay_axis_159 import case_once, load_frozen_contract
from research.trace_fate_diagnosis_167 import (
    CHECKPOINTS, MEASUREMENTS, RATES, EventObserver, contract_digest, observe_case,
)
from core.state import Lifecycle


class TraceFateDiagnosis167Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = load_frozen_contract()
        cls.seed = cls.frozen["search_cohort"][0]

    def test_contract_is_exact_and_heldout_excluded(self):
        self.assertEqual(RATES, (0, 256))
        self.assertEqual(CHECKPOINTS[-1], 1000)
        self.assertEqual(len(self.frozen["search_cohort"]), 16)
        self.assertEqual(len(self.frozen["search_negative_sentinels"]), 4)
        self.assertNotIn(self.frozen["heldout_validation_cohort"][0],
                         self.frozen["search_cohort"])
        self.assertEqual(contract_digest(self.frozen), contract_digest(load_frozen_contract()))

    def test_seeds_rates_and_horizons_fail_closed(self):
        for seed in (
            self.frozen["heldout_validation_cohort"][0],
            self.frozen["heldout_negative_sentinels"][0],
            self.frozen["old_140_primary_seeds_excluded"][0],
            -1,
        ):
            with self.subTest(seed=seed):
                with self.assertRaisesRegex(ValueError, "not in frozen adaptive"):
                    observe_case(seed=seed, role="search", decay_rate=256, max_horizon=1)
        with self.assertRaisesRegex(ValueError, "outside diagnostic"):
            observe_case(seed=self.seed, role="search", decay_rate=1, max_horizon=1)
        with self.assertRaisesRegex(ValueError, "outside diagnostic"):
            observe_case(seed=self.seed, role="search", decay_rate=256, max_horizon=11)

    def test_event_hook_delegates_once_without_perturbing_state(self):
        config = PhysicsConfig(
            initial_density=32, trace_write_cap=32, trace_transfer_cap=8, trace_discharge_cap=16,
            trace_decay_rate=256, trace_bonus_shift=5,
        )
        for seed in (7, 8):
            original = physics.create_universe(seed=seed, config=config)
            observed = physics.create_universe(seed=seed, config=config)
            watcher = EventObserver()
            watcher.begin(observed)
            physics.step(original)
            with watcher.attach():
                physics.step(observed)
            self.assertEqual(original.to_snapshot(), observed.to_snapshot())
            self.assertTrue(all(value >= 0 for value in watcher.events.values()))

    def test_write_clamp_is_counted_not_changed(self):
        config = PhysicsConfig(
            initial_density=32, trace_write_cap=32, trace_transfer_cap=8,
            trace_discharge_cap=16, trace_decay_rate=256, trace_bonus_shift=5,
        )
        state = physics.create_universe(seed=9, config=config)
        slot = state.active_slots()[0]
        state.slow_trace[slot] = 254
        observer = EventObserver()
        observer.begin(state)
        with observer.attach():
            physics._apply_slow_trace_writes(state, config, {slot: 100})
        self.assertEqual(state.slow_trace[slot], 255)
        self.assertEqual(observer.events["write_units"], 1)
        self.assertEqual(observer.events["write_clamp_loss"], 31)

    def test_smoke_matches_legacy_full_authoritative_snapshots(self):
        # Short deterministic replay/parity smoke for BOTH frozen diagnostic rates.
        for rate in RATES:
            with self.subTest(rate=rate):
                new = observe_case(seed=self.seed, role="search",
                                   decay_rate=rate, max_horizon=100)
                legacy = case_once(seed=self.seed, role="search",
                                   decay_rate=rate, frozen=self.frozen,
                                   instrumented=False, max_horizon=100)
                for horizon in ("0", "1", "100"):
                    self.assertEqual(
                        new["checkpoint_branch_digests"][horizon],
                        legacy["checkpoints"][horizon]["branch_digests"],
                    )
                    self.assertEqual(
                        new["checkpoints"][horizon],
                        legacy["checkpoints"][horizon]["comparisons"],
                    )
                self.assertTrue(all(
                    not x["control_vs_control_repeat"]["different"]
                    for x in new["checkpoints"].values()
                ))
                self.assertFalse(new["learning_claim"])
                self.assertEqual(new["heldout_max_horizon"], 0)
                for branch in ("control", "control_repeat", "b", "h"):
                    self.assertEqual(set(new["event_totals"][branch]), set(MEASUREMENTS))
                self.assertEqual(len(new["trace_timeline"]), 101)
                self.assertEqual(len(new["matched_read_timeline"]), 100)
                for branch in ("b", "h"):
                    self.assertEqual(len(new["event_timeline"][branch]), 100)
                    for key in MEASUREMENTS:
                        self.assertEqual(
                            new["event_totals"][branch][key],
                            sum(point["counters"].get(key, 0)
                                for point in new["event_timeline"][branch]),
                        )
                self.assertEqual(
                    new["trace_timeline"][-1]["differing_slots"],
                    new["checkpoints"]["100"]["b_vs_h"]["fields"]
                       ["slow_trace"]["changed_slots"],
                )

    def test_long_horizon_exact_g1_parity_both_diagnostic_controls(self):
        # D1 blocking +1000 validity gate, rather than a new Phase H run.
        for rate in RATES:
            with self.subTest(rate=rate):
                observed = observe_case(
                    seed=self.seed, role="search",
                    decay_rate=rate, max_horizon=1000,
                )
                baseline = case_once(
                    seed=self.seed, role="search", decay_rate=rate,
                    frozen=self.frozen, instrumented=False, max_horizon=1000,
                )
                for h in ("0", "1", "100", "1000"):
                    self.assertEqual(
                        observed["checkpoint_branch_digests"][h],
                        baseline["checkpoints"][h]["branch_digests"],
                    )
                    self.assertEqual(
                        observed["checkpoints"][h],
                        baseline["checkpoints"][h]["comparisons"],
                    )
                self.assertFalse(observed["checkpoints"]["1000"]["b_vs_h"]["different"])
                self.assertEqual(
                    set(observed["h0_teacher_window_events"]["b"]), set(MEASUREMENTS)
                )
                self.assertEqual(
                    set(observed["h0_teacher_window_events"]["h"]), set(MEASUREMENTS)
                )

    def test_replay_and_negative_sentinel(self):
        a = observe_case(seed=self.seed, role="search", decay_rate=256,
                         max_horizon=1)
        b = observe_case(seed=self.seed, role="search", decay_rate=256,
                         max_horizon=1)
        self.assertEqual(a, b)
        sent = observe_case(seed=self.frozen["search_negative_sentinels"][0],
                            role="sentinel", decay_rate=256, max_horizon=10)
        self.assertTrue(all(
            not point["b_vs_h"]["different"] for point in sent["checkpoints"].values()
        ))


if __name__ == "__main__":
    unittest.main()
