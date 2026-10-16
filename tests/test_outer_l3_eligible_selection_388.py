"""O2-3 #388 synthetic-only eligible Outer selector; never run a Universe."""
from __future__ import annotations
import unittest
from dataclasses import replace
from unittest.mock import patch

from core.physics import PhysicsConfig
from search.outer_search import CandidateValues
from research.outer_l3_memory_search_386 import _protocol
from research.outer_l3_eligible_selection_388 import (
    ProposedOuterSlot, SYNTHETIC_ONLY, proposal_from_screened_cases,
    proposed_same_operator_parent, proposed_prune_indices,
    proposed_mutation_from_parent,
)

SEEDS = (700, 701, 702, 703)


def candidate(*, noise=1, op="masked_copy"):
    p = _protocol()
    scalars = {name: domain[0] for name, domain in p["search_domains"].items()}
    scalars.update(initial_density=8, noise_rate=noise)
    return CandidateValues(scalars=scalars, rules={"latent_operator": op})


def evidence(*, teacher1000=1, birth=1, valid=True):
    p = _protocol()
    values = {key: True for key in p["objective"]["hard_validity"]}
    values["baseline_sham_equal"] = valid
    values.update(
        distinct_h0_qualified_search_seeds=4,
        real_post_h0_born_epoch_count=birth,
        native_selected_contact_count=5,
        native_masked_source_contrast_count=3,
        distinct_living_epoch_causal_candidate_count=2,
        h1000_teacher_specific_contrast_count=teacher1000,
        cross_epoch_qualified_candidate_count=1,
        h100_teacher_specific_contrast_count=2,
        native_total_runtime_ms=20,
    )
    return values


def slot(index, *, noise, teacher=1, birth=1, op="masked_copy", valid=True):
    return ProposedOuterSlot(index=index, candidate=candidate(noise=noise, op=op),
                             case_seed_ids=SEEDS,
                             evidence=evidence(teacher1000=teacher,birth=birth,valid=valid))


CFG=PhysicsConfig(fragmentation_enabled=True)


class StrictResearchOuterSelection(unittest.TestCase):
    def test_only_valid_screened_candidates_feed_parent(self):
        slots=(slot(0, noise=1, teacher=1),
               slot(1, noise=2, teacher=3),
               slot(2, noise=4, teacher=10, birth=0),
               slot(3, noise=8, teacher=30, valid=False))
        with patch("core.physics.step", side_effect=AssertionError("native step forbidden")):
            ranking=proposal_from_screened_cases(slots,training_seed_manifest=SEEDS,
                                                 base_config=CFG)
            self.assertEqual([record.index for record in ranking.records],[0,1])
            self.assertEqual([n for n,_ in ranking.rejected],[2,3])
            self.assertEqual(proposed_same_operator_parent(ranking,target_index=2),1)
            self.assertEqual(proposed_same_operator_parent(ranking,target_index=0),1)
        self.assertEqual(ranking.status,SYNTHETIC_ONLY)
        self.assertFalse(ranking.actual_physics_executed)
        self.assertFalse(ranking.source_provenance_verified)
        self.assertFalse(ranking.independent_validation)
        self.assertFalse(ranking.winner_fixed)
        self.assertFalse(ranking.learning_claim)

    def test_parent_and_pruning_do_not_promote_invalid_or_different_operator(self):
        slots=(slot(0,noise=1),slot(1,noise=2,birth=0),
               slot(2,noise=4,op="masked_xor",teacher=12),
               slot(3,noise=8,op="masked_xor",birth=0))
        rank=proposal_from_screened_cases(slots,training_seed_manifest=SEEDS,
                                          base_config=CFG)
        self.assertEqual([r.index for r in rank.records],[0,2])
        self.assertEqual(proposed_same_operator_parent(rank,target_index=1),0)
        self.assertEqual(proposed_same_operator_parent(rank,target_index=3),2)
        self.assertNotIn(1,proposed_prune_indices(rank))
        self.assertNotIn(3,proposed_prune_indices(rank))
        with self.assertRaises(ValueError):
            proposed_same_operator_parent(rank,target_index=0)
        with self.assertRaises(ValueError):
            proposed_same_operator_parent(rank,target_index=128)

    def test_registered_mutation_uses_eligible_parent_and_approved_seed(self):
        slots=(slot(0,noise=1,teacher=3),slot(1,noise=2,birth=0))
        rank=proposal_from_screened_cases(slots,training_seed_manifest=SEEDS,
                                          base_config=CFG)
        with patch("core.physics.step",side_effect=AssertionError("cannot step")):
            change=proposed_mutation_from_parent(
                rank,target_index=1,dimension_id="noise_rate",direction=1,
                seed=700,base_config=CFG)
        self.assertEqual(change.parent_index,0)
        self.assertEqual(change.target_index,1)
        self.assertEqual(change.mutation_dimension,"noise_rate")
        self.assertEqual(change.candidate_values.scalars["noise_rate"],2)
        self.assertEqual(change.seed,700)
        self.assertNotIn("seed",change.candidate_values.scalars)
        self.assertNotIn("teacher",change.candidate_values.rules)
        for kwargs in [
            dict(dimension_id="unregistered",direction=1,seed=700),
            dict(dimension_id="noise_rate",direction=2,seed=700),
            dict(dimension_id="noise_rate",direction=1,seed=96),
            dict(dimension_id="noise_rate",direction=1,seed=544),
            dict(dimension_id="noise_rate",direction=1,seed=999),
        ]:
            with self.assertRaises(ValueError):
                proposed_mutation_from_parent(rank,target_index=1,
                                              base_config=CFG,**kwargs)

    def test_h0_training_seed_manifest_must_be_identical_and_safe(self):
        slots=(slot(0,noise=1),slot(1,noise=2))
        for bad in [(96,700,701,702),(544,700,701,702),
                    (545,700,701,702),(700,701,702,702),
                    (700,701,702),(701,700,702,703),
                    (700,701,702,True)]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                proposal_from_screened_cases(slots,training_seed_manifest=bad,
                                             base_config=CFG)
        wrong=replace(slots[1],case_seed_ids=(700,701,702,704))
        with self.assertRaises(ValueError):
            proposal_from_screened_cases((slots[0],wrong),
                                         training_seed_manifest=SEEDS,base_config=CFG)

    def test_duplicate_slots_malformed_source_flags_and_no_manually_picked_fitness(self):
        a=slot(0,noise=1)
        for bad in [
            (a,replace(a,candidate=candidate(noise=2))),
            (replace(a,index=128),),
            (replace(a,evidence_mature=1),),
            (replace(a,evidence={**evidence(), "distinct_h0_qualified_search_seeds":5}),),
            (replace(a,evidence={**evidence(), "negative_sentinels_clean":1}),),
            (replace(a,evidence={**evidence(), "native_selected_contact_count":-1}),),
        ]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                proposal_from_screened_cases(bad,training_seed_manifest=SEEDS,
                                             base_config=CFG)
        invalid=slot(0,noise=1,birth=0)
        rank=proposal_from_screened_cases((invalid,),
                                          training_seed_manifest=SEEDS,base_config=CFG)
        self.assertFalse(rank.records)
        self.assertEqual(len(rank.rejected),1)
        self.assertFalse(proposed_prune_indices(rank))
        with self.assertRaises(ValueError):
            proposed_same_operator_parent(rank,target_index=0)

    def test_synthetic_witness_can_never_be_independent_learning(self):
        rank=proposal_from_screened_cases((slot(0,noise=1),),
                                          training_seed_manifest=SEEDS,base_config=CFG)
        self.assertFalse(rank.source_provenance_verified)
        self.assertFalse(rank.actual_physics_executed)
        self.assertFalse(rank.independent_validation)
        self.assertFalse(rank.learning_claim)
        self.assertFalse(rank.winner_fixed)


if __name__=="__main__":
    unittest.main()
