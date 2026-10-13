"""A1.5 source-native selected read and population support contract fixtures."""
import unittest

from core.physics import apply_latent_operator
from core.state import UniverseState
from research import a1_selected_latent_diversity_317 as a15
from research.r2_write_rules_175 import load_frozen

class SelectedLatentSupportTests(unittest.TestCase):
    def evt(self,src=1,dst=1,mask=1,generation=13):
        return {
            "source_latent_before":src, "recipient_latent_before":dst,
            "native_mask":mask,
            "recipient_latent_after":apply_latent_operator("masked_copy",src,dst,mask),
            "native_generation":generation,"address":19,
            "source_slot":1,"recipient_slot":2,"source_epoch":0,"recipient_epoch":0,
            "source_xy":[1,2],"bond_strength":0,"shift":5,"source_trace_start":0,
        }

    def test_original_native_selected_inert_and_effectful_masks(self):
        result=a15.selected_event_distribution([self.evt(1,1),
                                                  self.evt(3,1,mask=2,generation=25)])
        self.assertEqual(result["counts"]["selected_source_events"],2)
        self.assertEqual(result["counts"]["different_prelatent"],1)
        self.assertEqual(result["counts"]["native_nonzero_copy_delta"],1)
        self.assertEqual(result["counts"]["source_not_one"],1)
        self.assertEqual(result["source_words"],{"1":1,"3":1})
        self.assertEqual(len(result["all_nonidentical_original_selected_event_rows"]),1)
        self.assertEqual(result["by_original_period"]["1-100"]["selected_source_events"],2)
        bad=self.evt(3,1,mask=2)
        bad["recipient_latent_after"]=1
        with self.assertRaises(ValueError):a15.selected_event_distribution([bad])
        with self.assertRaises(ValueError):a15.selected_event_distribution([self.evt(generation=12)])

    def test_population_active_all_and_partial_latent_support(self):
        state=UniverseState(seed=2,max_cells=4)
        self.assertEqual(a15.active_latent_support(state)["distinct_words"],0)
        state.spawn(x=0,y=0,latent=1)
        state.spawn(x=1,y=1,latent=3)
        state.spawn(x=2,y=2,latent=1)
        current=a15.active_latent_support(state)
        self.assertEqual(current["active"],3)
        self.assertEqual(current["distinct_words"],2)
        self.assertEqual(current["not_one"],1)
        self.assertEqual(current["words"],{"1":2,"3":1})
        self.assertEqual(current,a15._snapshot_active_latent(state.to_snapshot()))

    def test_frozen_original_seed_and_r2_bounds(self):
        f=load_frozen()
        self.assertEqual(f["digest"],a15.pilot.R2_FROZEN_DIGEST)
        self.assertEqual(a15.ALLOWED,(544,545))
        self.assertEqual(a15.EXPECTED_COUNTS,{544:(764,95,36),545:(966,0,0)})
        self.assertEqual(a15.METRIC_FIELDS,("fusion_count","fragmentation_count",
                                            "collision_count","latent_transmission_count",
                                            "noise_spawn_count"))
        with self.assertRaises(ValueError):a15.run_observed_branch(1024,"b",f,0)
        with self.assertRaises(ValueError):a15.run_observed_branch(544,"control",f,0)
        with self.assertRaises(ValueError):a15.report(source_sha="short")

if __name__=="__main__":unittest.main()
