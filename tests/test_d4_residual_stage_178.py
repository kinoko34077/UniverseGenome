"""D4 #178 synthetic operator-stage classifier and prior-manifest safety gates."""
import unittest
from research import d4_residual_stage_178 as d4


class StageTests(unittest.TestCase):
    def test_stage_window_order(self):
        self.assertEqual(d4.STAGES, (
            "before_write", "after_write", "after_transfer",
            "before_decay", "after_decay", "end",
        ))
        self.assertEqual(d4.stage_pair_changes(True, [True,False,False,False,False,False]), ["after_write"])
        self.assertEqual(d4.stage_pair_changes(True, [False,False,False,False,False,False]), ["before_write"])
        self.assertEqual(d4.stage_pair_changes(True, [True,True,True,False,False,False]), ["before_decay"])

    def test_temporary_collapse_and_return_not_lost_forever(self):
        stage=[True, False, True, True, True, True]
        self.assertEqual(d4.stage_pair_changes(True, stage), ["after_write"])
        self.assertEqual(d4.stage_pair_changes(False, [False,True,False,False,False,False]), ["after_transfer"])

    def test_bad_stage_count_and_sha_rejected(self):
        with self.assertRaises(ValueError):
            d4.stage_pair_changes(True,[False])
        with self.assertRaises(ValueError):
            d4.validate_source_sha("bad")

    def test_protocol_excludes_independent_confirmation(self):
        self.assertIn("OUTCOME", d4.PROTOCOL["source_r2"].upper())
        self.assertIn("not unique cause", d4.PROTOCOL["interpretation"])
        self.assertEqual(d4.R2_DIGEST,"3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543")
        self.assertEqual(d4.SHARDS*d4.SHARD_SIZE,24)
        self.assertEqual(d4.PROTOCOL["operator"],"unit_add")

    def test_roster_matches_frozen_result_and_excludes_reserved(self):
        manifest=d4.load_frozen()
        seeds=d4.roster(manifest)
        self.assertEqual(len(seeds),24)
        self.assertEqual(len(set(seeds)),24)
        self.assertTrue(all(544<=s<1024 for s in seeds))
        self.assertFalse(set(seeds)&set(range(0,544)))
        self.assertEqual(manifest["engine_sha256"],
            "b7cdaee56a2c1fdfa750790f53463abdb706ddb41660447bf69cb0a73048f8b9")


if __name__=="__main__":
    unittest.main()
