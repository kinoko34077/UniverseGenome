"""Repository-native compressed A1.5 provenance and negative result audit."""
import json
from pathlib import Path
import unittest

PATH=Path("research/artifacts/a1_317_selected_latent_diversity_2026-10-13.json")

class A15ArchiveContract(unittest.TestCase):
    def test_frozen_context_and_exposed_negative_are_complete(self):
        x=json.loads(PATH.read_text(encoding="utf-8"))
        self.assertEqual(x["schema"],"UG_A1_5_NATIVE_SELECTED_LATENT_DIVERSITY_COMPACT_V1")
        self.assertEqual(x["observer_sha"],"7666619a73b22eea0a8cf34dee1a6931629832dc")
        self.assertEqual(x["original_r2_manifest_digest"],
            "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543")
        self.assertEqual(x["conditions"]["original_checkpoints"],[1,10,100,250,500,1000])
        self.assertEqual(x["conditions"]["h0_state_generation"],13)
        self.assertFalse(x["conditions"]["learning_claim"])
        self.assertFalse(x["conditions"]["independent_confirmation"])
        self.assertEqual(set(x["experimental_observations"]),{"544","545"})
        for key,steps,pairs,ending in (("544",764,382,11),("545",966,483,13)):
            data=x["experimental_observations"][key]
            self.assertEqual(data["matched_directed_selected_reads"],steps)
            self.assertEqual(data["selected_source_word_hist"],{"1":steps})
            self.assertEqual(data["selected_destination_word_hist"],{"1":steps})
            self.assertEqual(data["selected_pair_transmissions"],pairs)
            for k in ("fusions","fragmentations","noise_spawns"):
                self.assertEqual(data[k],0)
            self.assertFalse(data["step_active_ever_not_one"])
            self.assertEqual(data["active_at_h0_and_checkpoints"]["1000"],ending)
            self.assertEqual(data["active_at_h0_and_checkpoints"]["0"],32)
        for j in x["hosted_runtime_original_artifact_sha"].values():
            self.assertEqual(len(j["zip"]),64)
            self.assertTrue(all(c in "0123456789abcdef" for c in j["zip"]))
        for seed in ("544","545"):
            self.assertEqual(set(x["original_native_event_hashes"][seed]),{"b","h"})
            for role in ("b","h"):
                self.assertEqual(len(x["original_native_event_hashes"][seed][role]["events"]),64)
                self.assertEqual(len(x["original_native_event_hashes"][seed][role]["h0"]),64)

if __name__=="__main__":unittest.main()
