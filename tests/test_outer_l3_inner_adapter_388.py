"""#388 O2-1 adapter synthetic physics input tests; never construct/advance a world."""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from core.physics import PhysicsConfig
from research.outer_l3_memory_search_386 import _protocol
from research.outer_l3_inner_adapter_388 import (
    FORBIDDEN_INNER_KEYS, InnerPhysicsInput, resolve_inner_execution_input,
)


def _candidate():
    p = _protocol()
    values = {name: domain[0] for name, domain in p["search_domains"].items()}
    return values, {"latent_operator": "masked_copy"}


class OuterInnerAdapter388Tests(TestCase):
    def test_resolved_input_is_pure_native_physics_not_outer_metadata(self):
        scalars, rules = _candidate()
        scalars.update(initial_density=8, noise_rate=256,
                       fragmentation_base_probability=512, trace_write_cap=8)
        cfg = PhysicsConfig(fragmentation_enabled=True, max_cells=128)
        with patch("core.physics.step", side_effect=AssertionError("cannot step")):
            result = resolve_inner_execution_input(scalars, rules, base_config=cfg)
        actual = result.input.to_dict()
        self.assertEqual(set(actual), set(PhysicsConfig().to_dict()))
        self.assertFalse(set(actual) & FORBIDDEN_INNER_KEYS)
        self.assertEqual(actual["initial_density"], 8)
        self.assertEqual(actual["max_cells"], 128)
        self.assertEqual(actual["noise_rate"], 256)
        self.assertEqual(actual["fragmentation_rate"], 512)
        self.assertEqual(actual["latent_operator"], "masked_copy")
        self.assertEqual(result.input.to_physics_config().to_dict(), actual)
        self.assertNotIn("candidate_identity", actual)
        self.assertNotIn("seed", actual)
        self.assertNotIn("teacher", actual)
        self.assertNotIn("objective", actual)

    def test_deterministic_digest_and_physics_sensitive_changes(self):
        scalars, rules = _candidate()
        base = PhysicsConfig(fragmentation_enabled=True)
        a=resolve_inner_execution_input(scalars, rules, base_config=base)
        b=resolve_inner_execution_input(dict(scalars),dict(rules),base_config=base)
        self.assertEqual(a,b)
        self.assertEqual(len(a.input.physics_sha256),64)
        c=resolve_inner_execution_input(
            {**scalars,"noise_rate":1},rules,base_config=base)
        self.assertNotEqual(a.input.physics_sha256,c.input.physics_sha256)
        self.assertNotEqual(a.candidate_identity,c.candidate_identity)
        d=resolve_inner_execution_input(
            scalars,{"latent_operator":"masked_xor"},base_config=base)
        self.assertNotEqual(a.input.physics_sha256,d.input.physics_sha256)
        self.assertNotEqual(a.candidate_identity,d.candidate_identity)
        e=resolve_inner_execution_input(
            scalars,rules,base_config=PhysicsConfig(fragmentation_enabled=True,max_cells=128))
        self.assertNotEqual(a.input.physics_sha256,e.input.physics_sha256)

    def test_missing_or_invalid_candidate_fails_before_any_world(self):
        scalars,rules=_candidate()
        cfg=PhysicsConfig(fragmentation_enabled=True)
        with patch("core.physics.step", side_effect=AssertionError("native called")):
            with self.assertRaises(ValueError):
                resolve_inner_execution_input(
                    {k:v for k,v in scalars.items() if k!="hp_decay"},rules,base_config=cfg)
            with self.assertRaises(ValueError):
                resolve_inner_execution_input(
                    {**scalars,"seed":544},rules,base_config=cfg)
            with self.assertRaises(ValueError):
                resolve_inner_execution_input(
                    scalars,{"latent_operator":"unregistered"},base_config=cfg)
            with self.assertRaises(TypeError):
                resolve_inner_execution_input(scalars,rules,base_config=None)
        with self.assertRaises(ValueError):
            resolve_inner_execution_input(
                {**scalars,"fragmentation_base_probability":1},
                rules,base_config=PhysicsConfig(fragmentation_enabled=False))

    def test_inner_payload_forbids_missing_extra_or_changed_source(self):
        data=PhysicsConfig().to_dict()
        items=tuple(sorted(data.items()))
        with self.assertRaises(ValueError):
            InnerPhysicsInput(items,"0"*64)
        with self.assertRaises(ValueError):
            InnerPhysicsInput(items+(items[0],),"0"*64)
        with self.assertRaises(ValueError):
            InnerPhysicsInput(tuple(sorted({**data,"seed":544}.items())),"0"*64)
        with self.assertRaises(ValueError):
            InnerPhysicsInput(tuple(sorted({k:v for k,v in data.items()
                                            if k!="noise_rate"}.items())),"0"*64)
