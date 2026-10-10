"""PERF #219: original black-hole revival observer and accepted event parity."""
from dataclasses import asdict
from unittest.mock import patch
import unittest

import core.physics as physics
from core.physics import PhysicsConfig, create_universe, destination_footprint
from core.state import Lifecycle, UniverseState
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer
from core.experiment import ExperimentConfig


def original_revival_slots(state: UniverseState) -> set[int]:
    """Exact pre-PR old helper, kept as independent comparison oracle."""
    active = state.active_slots()
    black_holes = [
        slot for slot, lifecycle in enumerate(state.lifecycle)
        if lifecycle == Lifecycle.BLACK_HOLE
    ]
    revived: set[int] = set()
    for black_hole in black_holes:
        black_hole_footprint = destination_footprint(
            state.structure[black_hole], state.x[black_hole], state.y[black_hole]
        )
        for participant in active:
            if not (state.latent[participant] or state.bond_strength[participant]):
                continue
            participant_footprint = destination_footprint(
                state.structure[participant], state.x[participant], state.y[participant]
            )
            if black_hole_footprint.intersection(participant_footprint):
                revived.add(black_hole)
                break
    return revived


class RevivalOptimizedParityTests(unittest.TestCase):
    def test_direct_revival_cases_preserve_readonly_state(self):
        for density in (0, 1, 32, 128):
            for case in ("no_black_hole", "unreachable", "revivable", "multiple"):
                with self.subTest(density=density, case=case):
                    s = create_universe(seed=0, config=PhysicsConfig(initial_density=density))
                    if case != "no_black_hole":
                        bh1 = s.spawn(x=0, y=0, hp=1)
                        s.lifecycle[bh1] = int(Lifecycle.BLACK_HOLE)
                        if case == "multiple":
                            bh2 = s.spawn(x=128, y=128, hp=1)
                            s.lifecycle[bh2] = int(Lifecycle.BLACK_HOLE)
                        if case in ("revivable", "multiple"):
                            s.spawn(x=0, y=0, latent=1)
                    before = digest(s.to_snapshot())
                    self.assertEqual(
                        physics._local_revival_slots(s),
                        original_revival_slots(s),
                    )
                    self.assertEqual(digest(s.to_snapshot()), before)

    def test_physical_step_parity_with_black_hole_timeout_and_revival(self):
        for seed, density, decay in ((0, 4, 0), (2, 32, 1), (7, 128, 1)):
            with self.subTest(seed=seed, density=density, decay=decay):
                config = PhysicsConfig(initial_density=density, hp_decay=decay,
                                       black_hole_grace=3, recovery_hp=32)
                reference = create_universe(seed=seed, config=config)
                optimized = create_universe(seed=seed, config=config)
                for generation in range(25):
                    if generation in (0, 8):
                        for state in (reference, optimized):
                            bh = state.spawn(x=0, y=0, hp=1)
                            state.lifecycle[bh] = int(Lifecycle.BLACK_HOLE)
                            state.black_hole_timer[bh] = 3
                            state.spawn(x=0 if generation == 8 else 128,
                                        y=0 if generation == 8 else 128,
                                        latent=1, hp=200)
                    with patch.object(physics, "_local_revival_slots", original_revival_slots):
                        old_metrics = physics.step(reference)
                    fast_metrics = physics.step(optimized)
                    self.assertEqual(reference.to_snapshot(), optimized.to_snapshot())
                    old = asdict(old_metrics)
                    fast = asdict(fast_metrics)
                    old.pop("generations_per_second")
                    fast.pop("generations_per_second")
                    self.assertEqual(old, fast)

    def test_pre_d14_full_native_selected128_golden(self):
        opt = SteadyStateOptimizer.from_defaults(
            base_seed=0,
            experiment=ExperimentConfig(evaluation_timeout_generations=2),
        )
        step_result = opt.step()
        self.assertEqual(step_result["evaluated_slots"], 128)
        self.assertEqual(
            digest(opt.to_snapshot()),
            "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321",
        )


if __name__ == "__main__":
    unittest.main()
