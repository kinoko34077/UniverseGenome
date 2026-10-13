"""#326 A1.6: bounded synthetic ORIGINAL-native feasibility only.

Not original R2 seed replay, not naturally selected fusion, and not learned behavior.
No physical source, defaults, production or future science cohort modification.
"""
import json
from pathlib import Path
import unittest

from core.physics import (
    PhysicsConfig,
    apply_latent_operator,
    create_universe,
    mix_fusion_latent,
    step,
)
from core.state import SHAPE_SINGLE, structure_level


class NativeLatentDiversityFeasibility(unittest.TestCase):
    @staticmethod
    def _four_single_cover(*, bonds=33, missing=False, fusion=True):
        # Deterministic synthetic pre-loaded state: these bonds are NOT
        # claimed to have arisen naturally in old R2 physics.
        config = PhysicsConfig(
            max_cells=8,
            initial_density=0,
            initial_latent=1,
            hp_decay=0,
            noise_rate=0,
            bond_decay=1,
            fusion_enabled=fusion,
            fusion_bond_threshold=32,
            fusion_velocity_threshold=8,
            fragmentation_enabled=False,
            latent_operator="masked_copy",
        )
        state = create_universe(seed=0, config=config)
        tiles = [(0, 0), (1, 0), (0, 1), (1, 1)]
        if missing:
            tiles = tiles[:-1]
        for tx, ty in tiles:
            slot = state.spawn(
                x=tx * 8, y=ty * 8, structure=SHAPE_SINGLE,
                latent=1, hp=200, direction=0, speed_code=0,
            )
            state.bond_strength[slot] = bonds
        return state

    def test_source_operator_algebra_not_selected_contact(self):
        self.assertEqual(
            apply_latent_operator("masked_copy", 1, 1, 0xFFFF), 1,
        )
        self.assertEqual(
            apply_latent_operator("masked_copy", 1, 1, 0x0010), 1,
        )
        self.assertEqual(
            apply_latent_operator("masked_xor", 1, 1, 0x0001), 0,
        )
        self.assertEqual(
            apply_latent_operator(
                "rotate_copy", 1, 1, 0x0010, rotate_amount=4,
            ), 17,
        )
        self.assertEqual(mix_fusion_latent((1, 1, 1, 1)), 0x1111)
        self.assertEqual(mix_fusion_latent((1, 1)), 17)

    def test_native_fusion_exact_cover_from_homogeneous_four_single_cells(self):
        a = self._four_single_cover()
        b = self._four_single_cover()
        self.assertEqual(a.to_snapshot(), b.to_snapshot())
        ma, mb = step(a), step(b)
        self.assertEqual(a.to_snapshot(), b.to_snapshot())
        self.assertEqual(ma.fusion_count, mb.fusion_count)
        self.assertEqual(ma.fusion_count, 1)
        self.assertEqual(ma.collision_count, 0)
        self.assertEqual(ma.latent_transmission_count, 0)
        active = a.active_slots()
        self.assertEqual(len(active), 1)
        self.assertEqual(a.latent[active[0]], 0x1111)
        self.assertEqual(structure_level(a.structure[active[0]]), 1)

    def test_native_fusion_requires_bonds_and_exact_cover_and_flag(self):
        # Bond 32 decays to 31 before fusion; baseline 33 survives as 32.
        for kwargs in (
            {"bonds": 32},
            {"missing": True},
            {"fusion": False},
        ):
            with self.subTest(kwargs=kwargs):
                a = self._four_single_cover(**kwargs)
                result = step(a)
                self.assertEqual(result.fusion_count, 0)
                self.assertTrue(
                    all(a.latent[slot] == 1 for slot in a.active_slots())
                )

    def test_original_project_default_not_migrated(self):
        defaults = json.loads(Path("config/default.json").read_text())["physics"]
        self.assertEqual(defaults["latent_operator"], "masked_copy")
        self.assertEqual(defaults["initial_latent"], 1)
        self.assertEqual(defaults["noise_rate"], 0)
        self.assertEqual(defaults["fragmentation_rate"], 0)
        self.assertEqual(defaults["fusion_bond_threshold"], 32)


if __name__ == "__main__":
    unittest.main()
