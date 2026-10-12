"""PERF268 P6.6: independent exhaustive 16-bit structure hierarchy oracle."""
import unittest

from core.state import (
    structure_level, structure_shape, degrade_structure,
    SHAPE_EMPTY, SHAPE_HORIZONTAL, SHAPE_VERTICAL, SHAPE_SINGLE,
)
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer


def original_level(structure):
    value = int(structure) & 0xFFFF
    for level in range(7, -1, -1):
        if ((value >> (level * 2)) & 0b11) != SHAPE_EMPTY:
            return level
    return 0


def original_shape(structure):
    level = original_level(structure)
    return (int(structure) >> (level * 2)) & 0b11


def original_degrade(structure):
    value = int(structure) & 0xFFFF
    level = original_level(value)
    shape = original_shape(value)
    if level == 0:
        if shape in (SHAPE_HORIZONTAL, SHAPE_VERTICAL):
            return SHAPE_SINGLE
        return SHAPE_EMPTY
    return SHAPE_SINGLE << ((level - 1) * 2)


class ExactLevelBitLengthOracle(unittest.TestCase):
    def test_all_65536_native_structures_exact(self):
        for structure in range(65536):
            self.assertEqual(structure_level(structure), original_level(structure))
            self.assertEqual(structure_shape(structure), original_shape(structure))
            self.assertEqual(degrade_structure(structure), original_degrade(structure))

    def test_masking_and_input_conversion_unchanged(self):
        values = [-65537, -65536, -256, -1, 0, 1, 2, 3, 4, 255, 65535,
                  65536, 65537, 131071, 2**40, True, False, "65535"]
        for structure in values:
            with self.subTest(structure=structure):
                self.assertEqual(structure_level(structure), original_level(structure))
                self.assertEqual(structure_shape(structure), original_shape(structure))
                self.assertEqual(degrade_structure(structure), original_degrade(structure))

    def test_full_source_native_default1024_optimizer_v7_original_slot0(self):
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        opt._evaluate_slot(opt.slots[0])
        self.assertEqual(
            digest(opt.to_snapshot()),
            "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1",
        )


if __name__ == "__main__":
    unittest.main()
