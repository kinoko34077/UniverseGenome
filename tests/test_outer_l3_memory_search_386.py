"""Source-only unit tests for original Outer-first L3 research search (#386)."""
import inspect
import unittest

from core.physics import PhysicsConfig
from search.evolution import SteadyStateOptimizer
from search.outer_search import build_default_search_registry, legacy_search_plan
from research.outer_l3_memory_search_386 import (
    _protocol, birth_mode, build_outer_l3_registry, build_outer_l3_search_plan,
    resolve_outer_l3_candidate, screen_real_outer_evidence,
)


def synthetic_case():
    p = _protocol()
    a = {k: True for k in p["objective"]["hard_validity"]}
    a.update(
        distinct_h0_qualified_search_seeds=4,
        real_post_h0_born_epoch_count=1, native_selected_contact_count=3,
        native_masked_source_contrast_count=1,
        distinct_living_epoch_causal_candidate_count=1,
        h1000_teacher_specific_contrast_count=1,
        cross_epoch_qualified_candidate_count=1,
        h100_teacher_specific_contrast_count=1,
        native_total_runtime_ms=10)
    return a


class OuterL3ResearchContract(unittest.TestCase):
    def test_source_only_domains_and_legacy_compatibility(self):
        p=_protocol()
        registry=build_outer_l3_registry()
        original=build_default_search_registry()
        plan=build_outer_l3_search_plan()
        self.assertEqual(set(p["search_domains"]),set(original.scalar_dimensions))
        self.assertEqual(set(p["rule_domains"]),set(original.rule_dimensions))
        self.assertEqual(set(plan.search),set(original.scalar_dimensions))
        self.assertEqual(tuple(plan.rules["latent_operator"].variants),
                         ("masked_copy","masked_xor","rotate_copy","masked_and"))
        self.assertEqual(registry.scalar_dimensions["fragmentation_base_probability"].physics_field,
                         "fragmentation_rate")
        self.assertFalse(plan.fixed)
        self.assertEqual(plan.population_size,128)
        self.assertIn(("phase5_legacy",1),registry.objective_profiles)
        self.assertEqual(legacy_search_plan().plan_id,"phase5_legacy")
        self.assertIn("optimizer currently supports the legacy-equivalent SearchPlan only",
                      inspect.getsource(SteadyStateOptimizer.__init__))
        self.assertFalse(p["winning_candidate_selected"])
        self.assertFalse(p["effectful_search_executed"])

    def test_all_scalar_domains_are_bidirectionally_mutation_reachable(self):
        from search.outer_search import CandidateValues, scalar_mutation_directions
        protocol=_protocol()
        plan=build_outer_l3_search_plan()
        registry=build_outer_l3_registry()
        scalars={k:v[0] for k,v in protocol["search_domains"].items()}
        rules={"latent_operator":"masked_copy"}
        for name,domain in protocol["search_domains"].items():
            with self.subTest(name=name):
                self.assertEqual(list(domain),sorted(set(domain)))
                for left,right in zip(domain,domain[1:]):
                    self.assertEqual(1 if left==0 else 2*left,right)
                    self.assertEqual(0 if right<=1 else right//2,left)
                    scalars[name]=left
                    up=scalar_mutation_directions(
                        plan=plan,registry=registry,
                        candidate=CandidateValues(scalars=dict(scalars),rules=rules),
                        dimension_id=name,
                        base_config=PhysicsConfig(fragmentation_enabled=True))
                    self.assertIn(1,up)
                    scalars[name]=right
                    down=scalar_mutation_directions(
                        plan=plan,registry=registry,
                        candidate=CandidateValues(scalars=dict(scalars),rules=rules),
                        dimension_id=name,
                        base_config=PhysicsConfig(fragmentation_enabled=True))
                    self.assertIn(-1,down)
                    scalars[name]=domain[0]

    def test_native_birth_modes_without_running_a_world(self):
        p=_protocol()
        v={k:a[0] for k,a in p["search_domains"].items()}
        r={"latent_operator":"masked_copy"}
        for n,f,name in [(0,0,"neither"),(256,0,"noise_only"),
                         (0,256,"fragmentation_only"),(256,256,"both")]:
            v["noise_rate"]=n;v["fragmentation_base_probability"]=f
            resolved,cfg=resolve_outer_l3_candidate(
                v,r,base_config=PhysicsConfig(fragmentation_enabled=True))
            self.assertEqual((cfg.noise_rate,cfg.fragmentation_rate),(n,f))
            self.assertEqual(birth_mode(cfg),name)
            self.assertTrue(resolved.candidate_identity)
        with self.assertRaises(ValueError):
            resolve_outer_l3_candidate({k:x for k,x in v.items() if k!="hp_gain"},
                                       r,base_config=PhysicsConfig(fragmentation_enabled=True))
        with self.assertRaises(ValueError):
            resolve_outer_l3_candidate({**v,"evidence_seed":42},r,
                                       base_config=PhysicsConfig(fragmentation_enabled=True))
        with self.assertRaises(ValueError):
            resolve_outer_l3_candidate(v,{"latent_operator":"invalid"},
                                       base_config=PhysicsConfig(fragmentation_enabled=True))
        with self.assertRaises(ValueError):
            resolve_outer_l3_candidate(v,r,base_config=PhysicsConfig(fragmentation_enabled=False))

    def test_cohorts_fixed_protocol_not_physics_winner(self):
        p=_protocol()
        self.assertEqual(p["cohorts"]["no_reserved_phase_h_seed_range"],[96,159])
        self.assertTrue(p["cohorts"]["absence_of_manifest_blocks_execution"])
        self.assertTrue(p["cohorts"]["exclude_previous_outcome_exposed_seeds"])
        self.assertTrue(p["cohorts"]["seed_never_evolves_as_candidate"])
        self.assertNotEqual(p["cohorts"]["search_role"],p["cohorts"]["validation_role"])
        self.assertTrue(p["backward_compatibility"]["preserve_legacy_optimizer_exact"])
        self.assertTrue(p["backward_compatibility"]["nonlegacy_search_requires_research_runner_adapter"])
        self.assertFalse(p["learning_claim"])
        self.assertFalse(p["heldout_used"])
        self.assertEqual(p["progressive_horizons"]["first"],[0,1,10])
        self.assertEqual(p["progressive_horizons"]["last"],[500,1000])
        self.assertTrue(p["progressive_horizons"]["shortlist_freeze_before_running"])

    def test_hard_controls_never_promote_invalid_evidence(self):
        good=synthetic_case()
        cfg=PhysicsConfig(noise_rate=256,fragmentation_enabled=True)
        ok=screen_real_outer_evidence(good,config=cfg)
        self.assertTrue(ok.rankable)
        self.assertFalse(ok.learning_proven)
        self.assertFalse(ok.independent_validation)
        for field in _protocol()["objective"]["hard_validity"]:
            x={**good,field:False}
            self.assertEqual(screen_real_outer_evidence(x,config=cfg).classification,
                             "INVALID_PROVENANCE_OR_NEGATIVE_CONTROL")
        with self.assertRaises(ValueError):
            screen_real_outer_evidence({**good,"replay_clean":1},config=cfg)
        with self.assertRaises(ValueError):
            screen_real_outer_evidence({**good,"native_total_runtime_ms":True},config=cfg)
        with self.assertRaises(ValueError):
            screen_real_outer_evidence({**good,"real_post_h0_born_epoch_count":-1},config=cfg)

    def test_birth_only_and_snapshots_do_not_win(self):
        good=synthetic_case()
        off=PhysicsConfig(noise_rate=0,fragmentation_rate=0,fragmentation_enabled=True)
        on=PhysicsConfig(noise_rate=1024)
        self.assertEqual(screen_real_outer_evidence(good,config=off).classification,
                         "BIRTH_DISABLED_BY_EFFECTIVE_PHYSICS")
        for key,label in [
            ("real_post_h0_born_epoch_count","BIRTH_CAPABLE_BUT_UNREACHED"),
            ("native_selected_contact_count","NO_AUTHENTIC_CROSS_EPOCH_CAUSAL_CANDIDATE"),
            ("native_masked_source_contrast_count","NO_AUTHENTIC_CROSS_EPOCH_CAUSAL_CANDIDATE"),
            ("distinct_living_epoch_causal_candidate_count","NO_AUTHENTIC_CROSS_EPOCH_CAUSAL_CANDIDATE"),
            ("h1000_teacher_specific_contrast_count","NO_LONG_HORIZON_TEACHER_SPECIFIC_CONTRAST"),
        ]:
            self.assertEqual(
                screen_real_outer_evidence({**good,key:0},config=on).classification,label)
        self.assertEqual(
            screen_real_outer_evidence({**good,"distinct_h0_qualified_search_seeds":3},
                                       config=on).classification,
            "INSUFFICIENT_MATCHED_H0_EVIDENCE")


if __name__=="__main__":
    unittest.main()
