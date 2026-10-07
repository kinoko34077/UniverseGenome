from __future__ import annotations

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from core.physics import (
    PhysicsConfig,
    apply_latent_operator,
    create_universe,
    step,
    transmission_mask,
)
from core.state import (
    Lifecycle,
    SHAPE_HORIZONTAL,
    SHAPE_SINGLE,
    SHAPE_VERTICAL,
    UniverseState,
)
from persistence.snapshot import load_snapshot, save_snapshot
from search.evolution import SteadyStateOptimizer
from search.genome import UNIVERSE_GENOME_FIELDS


TRACE_DEFAULTS = {
    "trace_write_cap": 0,
    "trace_transfer_cap": 0,
    "trace_discharge_cap": 0,
    "trace_decay_rate": 0,
    "trace_bonus_shift": 8,
}


def trace_config(**overrides: int | bool | str) -> PhysicsConfig:
    values = PhysicsConfig().to_dict()
    values.update(TRACE_DEFAULTS)
    values.update(overrides)
    return PhysicsConfig(**values)


def legacy_state_payload(state: UniverseState) -> dict:
    payload = copy.deepcopy(state.to_snapshot())
    payload["format_version"] = 1
    payload["arrays"].pop("slow_trace", None)
    if isinstance(payload.get("config"), dict):
        for key in TRACE_DEFAULTS:
            payload["config"].pop(key, None)
    return payload


class SlowTraceContractTests(unittest.TestCase):
    def test_st_001_authoritative_lifecycle_and_slot_reuse(self):
        config = trace_config(
            max_cells=2,
            hp_decay=1,
            black_hole_grace=2,
        )
        state = create_universe(seed=201, config=config)
        self.assertEqual(len(state.slow_trace), 2)
        self.assertEqual(list(state.slow_trace), [0, 0])

        slot = state.spawn(x=0, y=0, hp=1)
        self.assertEqual(state.slow_trace[slot], 0)
        state.slow_trace[slot] = 17

        step(state)
        self.assertEqual(state.lifecycle[slot], Lifecycle.BLACK_HOLE)
        self.assertEqual(state.slow_trace[slot], 17)

        step(state)
        self.assertEqual(state.lifecycle[slot], Lifecycle.BLACK_HOLE)
        self.assertEqual(state.slow_trace[slot], 17)

        step(state)
        self.assertEqual(state.lifecycle[slot], Lifecycle.FREE)
        self.assertEqual(state.slow_trace[slot], 0)

        reused = state.spawn(x=32, y=32, hp=10)
        self.assertEqual(reused, slot)
        self.assertEqual(state.slow_trace[reused], 0)

    def test_st_002_generic_activity_write_and_single_application(self):
        config = trace_config(
            max_cells=4,
            hp_decay=0,
            recovery_hp=7,
            bond_gain=0,
            bond_decay=0,
            collision_threshold=100,
            trace_write_cap=5,
        )

        external = create_universe(seed=202, config=config)
        ext = external.spawn(x=0, y=0, hp=255)
        step(external, stimulus_slots=(ext,))
        self.assertEqual(external.slow_trace[ext], 5)

        latent = create_universe(seed=203, config=config)
        source = latent.spawn(x=0, y=0, hp=20, latent=0xFFFF)
        target = latent.spawn(x=1, y=0, hp=20, latent=0)
        metrics = step(latent)
        self.assertEqual(metrics.latent_transmission_count, 1)
        self.assertEqual(latent.slow_trace[source], 5)
        self.assertEqual(latent.slow_trace[target], 5)

        simultaneous = create_universe(seed=204, config=config)
        source = simultaneous.spawn(x=0, y=0, hp=20, latent=0xFFFF)
        target = simultaneous.spawn(x=1, y=0, hp=20, latent=0)
        step(simultaneous, stimulus_slots=(source,))
        self.assertEqual(simultaneous.slow_trace[source], 5)
        self.assertEqual(simultaneous.slow_trace[target], 5)

        revived = create_universe(seed=205, config=config)
        carrier = revived.spawn(x=0, y=0, hp=10)
        revived.lifecycle[carrier] = int(Lifecycle.BLACK_HOLE)
        revived.hp[carrier] = 0
        revived.black_hole_timer[carrier] = 2
        step(revived, stimulus_slots=(carrier,))
        self.assertEqual(revived.lifecycle[carrier], Lifecycle.ACTIVE)
        self.assertEqual(revived.slow_trace[carrier], 5)

    def test_st_003_transfer_reuses_selected_latent_pair_and_is_conservative(self):
        config = trace_config(
            max_cells=4,
            hp_decay=0,
            recovery_hp=0,
            bond_gain=0,
            bond_decay=0,
            collision_threshold=100,
            trace_transfer_cap=4,
        )
        state = create_universe(seed=206, config=config)
        first = state.spawn(x=0, y=0, hp=50, latent=0xFFFF)
        second = state.spawn(x=1, y=0, hp=50, latent=0x0000)
        remote = state.spawn(x=80, y=80, hp=50, latent=0xAAAA)
        state.slow_trace[first] = 30
        state.slow_trace[second] = 10
        state.slow_trace[remote] = 20
        latent_before = list(state.latent)
        trace_before = list(state.slow_trace)

        metrics = step(state)

        changed_latent = {
            slot for slot in (first, second, remote)
            if state.latent[slot] != latent_before[slot]
        }
        changed_trace = {
            slot for slot in (first, second, remote)
            if state.slow_trace[slot] != trace_before[slot]
        }
        self.assertEqual(metrics.latent_transmission_count, 1)
        self.assertEqual(changed_latent, {first, second})
        self.assertEqual(changed_trace, {first, second})
        self.assertEqual(state.slow_trace[remote], trace_before[remote])
        self.assertEqual(
            sum(state.slow_trace[slot] for slot in (first, second, remote)),
            sum(trace_before[slot] for slot in (first, second, remote)),
        )
        self.assertTrue(
            all(0 <= state.slow_trace[slot] <= 255 for slot in (first, second, remote))
        )

    def test_st_003_transfer_formula_cases_are_exact(self):
        cases = (
            (30, 10, 4, (26, 14)),
            (10, 30, 4, (14, 26)),
            (20, 20, 4, (20, 20)),
            (30, 0, 3, (27, 3)),
        )
        for first_trace, second_trace, cap, expected in cases:
            with self.subTest(
                first_trace=first_trace,
                second_trace=second_trace,
                cap=cap,
            ):
                state = create_universe(
                    seed=220,
                    config=trace_config(
                        max_cells=2,
                        hp_decay=0,
                        recovery_hp=0,
                        bond_gain=0,
                        bond_decay=0,
                        collision_threshold=100,
                        trace_transfer_cap=cap,
                    ),
                )
                first = state.spawn(x=0, y=0, hp=50, latent=0xFFFF)
                second = state.spawn(x=1, y=0, hp=50, latent=0)
                state.slow_trace[first] = first_trace
                state.slow_trace[second] = second_trace
                step(state)
                self.assertEqual(
                    (state.slow_trace[first], state.slow_trace[second]),
                    expected,
                )

    def test_st_004_generation_start_trace_only_widens_latent_mask(self):
        config = trace_config(
            max_cells=4,
            hp_decay=0,
            recovery_hp=5,
            bond_gain=0,
            bond_decay=0,
            collision_threshold=100,
            latent_operator="masked_copy",
            trace_write_cap=5,
            trace_bonus_shift=4,
        )
        state = create_universe(seed=207, config=config)
        source = state.spawn(x=0, y=0, hp=50, latent=0xFFFF)
        target = state.spawn(x=1, y=0, hp=50, latent=0)
        state.slow_trace[source] = 0
        narrow = transmission_mask(
            state.seed,
            state.generation,
            0,
            (source, target),
            bond_strength=0,
            participant=state,
        )
        state.slow_trace[source] = 16
        wide = transmission_mask(
            state.seed,
            state.generation,
            0,
            (source, target),
            bond_strength=0,
            participant=state,
        )
        self.assertEqual(narrow.bit_count(), 1)
        self.assertEqual(wide.bit_count(), 2)

        for operator in ("masked_copy", "masked_xor", "rotate_copy", "masked_and"):
            expected = apply_latent_operator(
                operator,
                0x1234,
                0xA5A5,
                0x0F0F,
                rotate_amount=4,
            )
            self.assertEqual(
                apply_latent_operator(
                    operator,
                    0x1234,
                    0xA5A5,
                    0x0F0F,
                    rotate_amount=4,
                ),
                expected,
            )

        same_generation = create_universe(
            seed=208,
            config=trace_config(
                max_cells=2,
                hp_decay=0,
                recovery_hp=5,
                bond_gain=0,
                bond_decay=0,
                collision_threshold=100,
                latent_operator="masked_copy",
                trace_write_cap=5,
                trace_bonus_shift=0,
            ),
        )
        src = same_generation.spawn(x=0, y=0, hp=50, latent=0xFFFF)
        dst = same_generation.spawn(x=1, y=0, hp=50, latent=0)
        step(same_generation, stimulus_slots=(src,))
        self.assertEqual(same_generation.latent[dst].bit_count(), 1)
        self.assertEqual(same_generation.slow_trace[src], 5)

    def test_st_005_black_hole_discharge_revival_and_free(self):
        config = trace_config(
            max_cells=4,
            hp_decay=0,
            recovery_hp=7,
            black_hole_grace=2,
            trace_discharge_cap=3,
        )
        state = create_universe(seed=209, config=config)
        carrier = state.spawn(x=0, y=0, hp=10)
        recipient = state.spawn(x=1, y=0, hp=10)
        state.lifecycle[carrier] = int(Lifecycle.BLACK_HOLE)
        state.hp[carrier] = 0
        state.black_hole_timer[carrier] = 2
        state.slow_trace[carrier] = 10
        step(state)
        self.assertEqual(state.slow_trace[carrier], 7)
        self.assertEqual(state.slow_trace[recipient], 3)

        revived = create_universe(seed=210, config=config)
        carrier = revived.spawn(x=0, y=0, hp=10)
        revived.lifecycle[carrier] = int(Lifecycle.BLACK_HOLE)
        revived.hp[carrier] = 0
        revived.black_hole_timer[carrier] = 1
        revived.slow_trace[carrier] = 9
        step(revived, stimulus_slots=(carrier,))
        self.assertEqual(revived.lifecycle[carrier], Lifecycle.ACTIVE)
        self.assertEqual(revived.slow_trace[carrier], 9)

        expiring = create_universe(seed=211, config=config)
        carrier = expiring.spawn(x=0, y=0, hp=10)
        recipient = expiring.spawn(x=1, y=0, hp=10)
        expiring.lifecycle[carrier] = int(Lifecycle.BLACK_HOLE)
        expiring.hp[carrier] = 0
        expiring.black_hole_timer[carrier] = 1
        expiring.slow_trace[carrier] = 4
        step(expiring)
        self.assertEqual(expiring.lifecycle[carrier], Lifecycle.FREE)
        self.assertEqual(expiring.slow_trace[carrier], 0)
        self.assertEqual(expiring.slow_trace[recipient], 3)

        same_generation = create_universe(
            seed=212,
            config=trace_config(
                max_cells=4,
                hp_decay=1,
                recovery_hp=0,
                bond_velocity_threshold=0,
                collision_threshold=100,
                black_hole_grace=2,
                trace_discharge_cap=3,
            ),
        )
        carrier = same_generation.spawn(
            x=0, y=0, hp=1, direction=2, speed_code=1
        )
        recipient = same_generation.spawn(x=1, y=0, hp=20, speed_code=0)
        same_generation.slow_trace[carrier] = 6
        step(same_generation)
        self.assertEqual(same_generation.lifecycle[carrier], Lifecycle.BLACK_HOLE)
        self.assertEqual(same_generation.slow_trace[carrier], 3)
        self.assertEqual(same_generation.slow_trace[recipient], 3)

    def test_st_005_discharge_order_zero_multiple_and_competing_carriers(self):
        config = trace_config(
            max_cells=5,
            hp_decay=0,
            recovery_hp=0,
            black_hole_grace=2,
            trace_discharge_cap=4,
        )

        no_recipient = create_universe(seed=221, config=config)
        carrier = no_recipient.spawn(x=0, y=0, hp=10)
        no_recipient.lifecycle[carrier] = int(Lifecycle.BLACK_HOLE)
        no_recipient.hp[carrier] = 0
        no_recipient.black_hole_timer[carrier] = 2
        no_recipient.slow_trace[carrier] = 7
        step(no_recipient)
        self.assertEqual(no_recipient.lifecycle[carrier], Lifecycle.BLACK_HOLE)
        self.assertEqual(no_recipient.slow_trace[carrier], 7)

        multiple = create_universe(seed=222, config=config)
        carrier = multiple.spawn(x=0, y=0, hp=10)
        first = multiple.spawn(x=1, y=0, hp=10)
        second = multiple.spawn(x=2, y=0, hp=10)
        multiple.lifecycle[carrier] = int(Lifecycle.BLACK_HOLE)
        multiple.hp[carrier] = 0
        multiple.black_hole_timer[carrier] = 2
        multiple.slow_trace[carrier] = 4
        multiple.slow_trace[first] = 254
        multiple.slow_trace[second] = 253
        step(multiple)
        self.assertEqual(multiple.slow_trace[first], 255)
        self.assertEqual(multiple.slow_trace[second], 255)
        self.assertEqual(multiple.slow_trace[carrier], 1)

        competing = create_universe(seed=223, config=config)
        early = competing.spawn(x=0, y=0, hp=10)
        late = competing.spawn(x=0, y=0, hp=10)
        recipient = competing.spawn(x=1, y=0, hp=10)
        for slot in (early, late):
            competing.lifecycle[slot] = int(Lifecycle.BLACK_HOLE)
            competing.hp[slot] = 0
            competing.black_hole_timer[slot] = 2
            competing.slow_trace[slot] = 4
        competing.slow_trace[recipient] = 253
        before_total = sum(competing.slow_trace)
        step(competing)
        self.assertEqual(competing.slow_trace[recipient], 255)
        self.assertEqual(competing.slow_trace[early], 2)
        self.assertEqual(competing.slow_trace[late], 4)
        self.assertEqual(sum(competing.slow_trace), before_total)

    def test_st_006_decay_is_deterministic_and_not_slot_addressed(self):
        config = trace_config(
            max_cells=4,
            hp_decay=0,
            trace_decay_rate=65535,
        )
        observed_decay = False
        for seed in range(16):
            first = create_universe(seed=seed, config=config)
            first_slot = first.spawn(x=24, y=40, hp=20)
            first.slow_trace[first_slot] = 10

            second = create_universe(seed=seed, config=config)
            dummy = second.spawn(x=200, y=200, hp=20)
            second_slot = second.spawn(x=24, y=40, hp=20)
            second.free(dummy)
            second.slow_trace[second_slot] = 10

            step(first)
            step(second)
            self.assertEqual(
                first.slow_trace[first_slot],
                second.slow_trace[second_slot],
            )
            observed_decay |= first.slow_trace[first_slot] == 9
        self.assertTrue(observed_decay)

    def test_st_007_fusion_and_fragmentation_trace_material_semantics(self):
        fusion = create_universe(
            seed=213,
            config=trace_config(
                max_cells=8,
                hp_decay=0,
                fusion_enabled=True,
                fusion_bond_threshold=0,
                fusion_velocity_threshold=8,
            ),
        )
        slots = [
            fusion.spawn(x=x, y=y, hp=20)
            for x, y in ((0, 0), (8, 0), (0, 8), (8, 8))
        ]
        for slot, value in zip(slots, (100, 80, 60, 40)):
            fusion.slow_trace[slot] = value
        metrics = step(fusion)
        self.assertEqual(metrics.fusion_count, 1)
        result = min(slots)
        self.assertEqual(fusion.slow_trace[result], 255)
        for slot in slots:
            if slot != result:
                self.assertEqual(fusion.lifecycle[slot], Lifecycle.FREE)
                self.assertEqual(fusion.slow_trace[slot], 0)

        fragmented = False
        for seed in range(16):
            state = create_universe(
                seed=seed,
                config=trace_config(
                    max_cells=4,
                    hp_decay=0,
                    fragmentation_enabled=True,
                    fragmentation_rate=65535,
                    aging_enabled=False,
                ),
            )
            core = state.spawn(
                x=64,
                y=64,
                structure=SHAPE_SINGLE << 2,
                hp=20,
                direction=0,
                speed_code=0,
            )
            state.slow_trace[core] = 9
            metrics = step(state)
            if metrics.fragmentation_count:
                traces = sorted(
                    state.slow_trace[slot]
                    for slot in state.active_slots()
                )
                self.assertEqual(traces, [4, 5])
                fragmented = True
                break
        self.assertTrue(fragmented)

    def test_st_007_fragmentation_edge_values_and_level_zero_paths(self):
        for trace_value in (0, 1, 254, 255):
            with self.subTest(trace_value=trace_value):
                state = create_universe(
                    seed=224,
                    config=trace_config(
                        max_cells=2,
                        hp_decay=0,
                        fragmentation_enabled=True,
                        fragmentation_rate=65535,
                        aging_enabled=False,
                    ),
                )
                core = state.spawn(
                    x=64,
                    y=64,
                    structure=SHAPE_SINGLE << 2,
                    hp=20,
                    speed_code=0,
                )
                state.slow_trace[core] = trace_value
                metrics = step(state)
                self.assertEqual(metrics.fragmentation_count, 1)
                traces = sorted(state.slow_trace[slot] for slot in state.active_slots())
                self.assertEqual(
                    traces,
                    sorted((trace_value // 2, trace_value - (trace_value // 2))),
                )
                self.assertEqual(sum(traces), trace_value)

        for structure in (SHAPE_HORIZONTAL, SHAPE_VERTICAL):
            with self.subTest(structure=structure):
                state = create_universe(
                    seed=225,
                    config=trace_config(
                        max_cells=2,
                        hp_decay=0,
                        fragmentation_enabled=True,
                        fragmentation_rate=65535,
                        aging_enabled=False,
                    ),
                )
                slot = state.spawn(x=64, y=64, structure=structure, hp=20, speed_code=0)
                state.slow_trace[slot] = 255
                metrics = step(state)
                self.assertEqual(metrics.fragmentation_count, 1)
                self.assertEqual(state.lifecycle[slot], Lifecycle.ACTIVE)
                self.assertEqual(state.structure[slot], SHAPE_SINGLE)
                self.assertEqual(state.slow_trace[slot], 255)

        direct_free = create_universe(
            seed=226,
            config=trace_config(
                max_cells=2,
                hp_decay=0,
                fragmentation_enabled=True,
                fragmentation_rate=65535,
                aging_enabled=False,
            ),
        )
        slot = direct_free.spawn(x=64, y=64, structure=SHAPE_SINGLE, hp=20, speed_code=0)
        direct_free.slow_trace[slot] = 255
        metrics = step(direct_free)
        self.assertEqual(metrics.fragmentation_count, 1)
        self.assertEqual(direct_free.lifecycle[slot], Lifecycle.FREE)
        self.assertEqual(direct_free.slow_trace[slot], 0)

        full = create_universe(
            seed=227,
            config=trace_config(
                max_cells=1,
                hp_decay=0,
                fragmentation_enabled=True,
                fragmentation_rate=65535,
                aging_enabled=False,
            ),
        )
        core = full.spawn(
            x=64,
            y=64,
            structure=SHAPE_SINGLE << 2,
            hp=20,
            speed_code=0,
        )
        full.slow_trace[core] = 255
        metrics = step(full)
        self.assertEqual(metrics.fragmentation_count, 0)
        self.assertEqual(full.slow_trace[core], 255)

    def test_st_008_snapshot_versions_migration_and_rejection(self):
        config = trace_config(max_cells=4)
        state = create_universe(seed=214, config=config)
        slot = state.spawn(x=0, y=0, hp=20)
        state.slow_trace[slot] = 23

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slow-trace.json"
            save_snapshot(path, state)
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["format_version"], 2)
            self.assertEqual(raw["arrays"]["slow_trace"][slot], 23)
            restored = load_snapshot(path)
        self.assertEqual(restored.to_snapshot(), state.to_snapshot())
        step(state, stimulus_slots=(slot,))
        step(restored, stimulus_slots=(slot,))
        self.assertEqual(restored.to_snapshot(), state.to_snapshot())

        legacy = legacy_state_payload(state)
        legacy_config = PhysicsConfig.from_mapping(legacy["config"])
        migrated = UniverseState.from_snapshot(legacy, config=legacy_config)
        self.assertEqual(list(migrated.slow_trace), [0] * migrated.max_cells)
        self.assertEqual(
            {key: getattr(migrated.config, key) for key in TRACE_DEFAULTS},
            TRACE_DEFAULTS,
        )

        malformed = copy.deepcopy(state.to_snapshot())
        malformed["arrays"].pop("slow_trace")
        with self.assertRaises(ValueError):
            UniverseState.from_snapshot(malformed, config=config)

    def test_st_008_malformed_v2_and_legacy_config_boundaries(self):
        active = trace_config(
            max_cells=2,
            trace_write_cap=7,
            trace_transfer_cap=6,
            trace_discharge_cap=5,
            trace_decay_rate=4,
            trace_bonus_shift=3,
        )
        state = create_universe(seed=228, config=active)
        occupied = state.spawn(x=0, y=0, hp=20)
        state.slow_trace[occupied] = 9
        payload = state.to_snapshot()

        missing = copy.deepcopy(payload)
        missing["arrays"].pop("slow_trace")
        with self.assertRaises(ValueError):
            UniverseState.from_snapshot(missing, config=active)

        wrong_length = copy.deepcopy(payload)
        wrong_length["arrays"]["slow_trace"].append(0)
        with self.assertRaises(ValueError):
            UniverseState.from_snapshot(wrong_length, config=active)

        out_of_range = copy.deepcopy(payload)
        out_of_range["arrays"]["slow_trace"][occupied] = 256
        with self.assertRaises(ValueError):
            UniverseState.from_snapshot(out_of_range, config=active)

        free_nonzero = copy.deepcopy(payload)
        free_slot = 1
        self.assertEqual(free_nonzero["arrays"]["lifecycle"][free_slot], Lifecycle.FREE)
        free_nonzero["arrays"]["slow_trace"][free_slot] = 1
        with self.assertRaises(ValueError):
            UniverseState.from_snapshot(free_nonzero, config=active)

        legacy = legacy_state_payload(state)
        migrated = UniverseState.from_snapshot(legacy, config=active)
        self.assertEqual(
            {key: getattr(migrated.config, key) for key in TRACE_DEFAULTS},
            TRACE_DEFAULTS,
        )
        self.assertFalse(any(migrated.slow_trace))

        malformed_v6 = SteadyStateOptimizer.from_defaults(
            base_seed=229,
            base_config=trace_config(max_cells=4),
        ).to_snapshot()
        malformed_v6["base_config"].pop("trace_write_cap")
        with self.assertRaises(ValueError):
            SteadyStateOptimizer.from_snapshot(malformed_v6)

        nested_v1 = SteadyStateOptimizer.from_defaults(
            base_seed=230,
            base_config=trace_config(max_cells=4),
        ).to_snapshot()
        nested_v1["slots"][0]["state"]["format_version"] = 1
        nested_v1["slots"][0]["state"]["arrays"].pop("slow_trace")
        with self.assertRaises(ValueError):
            SteadyStateOptimizer.from_snapshot(nested_v1)

    def test_st_009_optimizer_v6_roundtrip_and_clone_isolation(self):
        base = trace_config(max_cells=8)
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=215,
            base_config=base,
        )
        slot = optimizer.slots[0]
        carrier = slot.state.active_slots()[0]
        slot.state.slow_trace[carrier] = 31

        payload = optimizer.to_snapshot()
        self.assertEqual(payload["format_version"], 6)
        self.assertTrue(
            all(record["state"]["format_version"] == 2 for record in payload["slots"])
        )
        restored = SteadyStateOptimizer.from_snapshot(payload)
        self.assertEqual(restored.to_snapshot(), payload)
        self.assertEqual(restored.slots[0].state.slow_trace[carrier], 31)

        clone = UniverseState.from_snapshot(
            slot.state.to_snapshot(),
            config=slot.state.config,
        )
        clone.slow_trace[carrier] = 99
        self.assertEqual(slot.state.slow_trace[carrier], 31)
        self.assertEqual(clone.slow_trace[carrier], 99)

        legacy = copy.deepcopy(payload)
        legacy["format_version"] = 5
        for key in TRACE_DEFAULTS:
            legacy["base_config"].pop(key, None)
        for record in legacy["slots"]:
            record["state"]["format_version"] = 1
            record["state"]["arrays"].pop("slow_trace", None)
            if isinstance(record["state"].get("config"), dict):
                for key in TRACE_DEFAULTS:
                    record["state"]["config"].pop(key, None)
        migrated = SteadyStateOptimizer.from_snapshot(legacy)
        self.assertEqual(migrated.to_snapshot()["format_version"], 6)
        self.assertTrue(
            all(
                not any(record.state.slow_trace)
                for record in migrated.slots
            )
        )

    def test_st_009_all_128_authoritative_slots_roundtrip_trace(self):
        optimizer = SteadyStateOptimizer.from_defaults(
            base_seed=231,
            base_config=trace_config(max_cells=8),
        )
        expected = []
        for index, record in enumerate(optimizer.slots):
            carrier = record.state.active_slots()[0]
            value = (index % 255) + 1
            record.state.slow_trace[carrier] = value
            expected.append((carrier, value))

        restored = SteadyStateOptimizer.from_snapshot(optimizer.to_snapshot())
        self.assertEqual(len(restored.slots), 128)
        for record, (carrier, value) in zip(restored.slots, expected):
            self.assertEqual(record.state.slow_trace[carrier], value)

    def test_st_011_positive_behavior_is_semantically_anonymous(self):
        config = trace_config(
            max_cells=2,
            hp_decay=0,
            recovery_hp=6,
            trace_write_cap=6,
            trace_bonus_shift=4,
        )
        left = create_universe(seed=216, config=config)
        right = create_universe(seed=216, config=config)
        left_slot = left.spawn(x=0, y=0, hp=20)
        right_slot = right.spawn(x=0, y=0, hp=20)

        step(left, stimulus_slots=(left_slot,))
        step(right, stimulus_slots=(right_slot,))
        self.assertEqual(left.to_snapshot(), right.to_snapshot())
        self.assertEqual(left.slow_trace[left_slot], 6)

        forbidden = {
            "teacher_byte",
            "input_byte",
            "organ_identity",
            "target_label",
            "tokenizer",
            "vocabulary",
            "matched_control",
        }
        self.assertTrue(forbidden.isdisjoint(inspect.signature(step).parameters))
        self.assertTrue(forbidden.isdisjoint(PhysicsConfig.__dataclass_fields__))
        self.assertTrue(
            {
                "trace_write_cap",
                "trace_transfer_cap",
                "trace_discharge_cap",
                "trace_decay_rate",
                "trace_bonus_shift",
            }.isdisjoint(UNIVERSE_GENOME_FIELDS)
        )


if __name__ == "__main__":
    unittest.main()
