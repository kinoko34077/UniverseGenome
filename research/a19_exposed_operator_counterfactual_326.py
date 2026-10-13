"""A1.9: contact-local counterfactuals on the 36 ORIGINAL A1.4 selected masks.

This is NOT a new native step, dynamic trajectory, learned output or new seed.
It holds both original prelatents and original physically selected B/H masks fixed
and substitutes existing latent operators for exactly ONE hypothetical contact.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from core.physics import apply_latent_operator

ARCHIVE = Path("research/artifacts/a1_317_bit_support_native_2026-10-13.json")
OPERATORS = ("masked_copy", "masked_and", "masked_xor", "rotate_copy")
EXPECTED_FIELD_NAMES = (
    "relative_generation","native_generation","physical_address",
    "source_slot","recipient_slot","source_life_epoch_from_h0",
    "recipient_life_epoch_from_h0","trace_B","trace_H",
    "native_mask_B","native_mask_H","source_latent_before",
    "recipient_latent_before","recipient_after_B","recipient_after_H",
)


def original_contact_counterfactual() -> dict:
    source=json.loads(ARCHIVE.read_text(encoding="utf-8"))
    if (source["schema"] != "UG_A1_317_FROZEN_BIT_SUPPORT_COMPACT_V1"
            or source["original_changed_mask_rows_fields"] != list(EXPECTED_FIELD_NAMES)
            or len(source["original_changed_mask_rows"]) != 36
            or source["conditions"]["seed_roles"] != {
                "544":"previously_exposed_h0_positive",
                "545":"previously_exposed_h0_negative",
            }
            or source["observation"]["545"]["changed_mask"] != 0):
        raise ValueError("A1.4 source-frozen exposed case selection/schema changed")
    totals=Counter({key:0 for key in OPERATORS})
    rows_by_operator={key:[] for key in OPERATORS}
    mask_bit0=mask_bit4=joint=0
    for values in source["original_changed_mask_rows"]:
        if len(values)!=15:
            raise ValueError("invalid original native event fields")
        (rel,native,address,source_slot,recipient_slot,
         source_epoch,recipient_epoch,trace_b,trace_h,
         mask_b,mask_h,original_src,original_dst,old_b,old_h)=values
        if not (1<=rel<=1000 and native-rel==12 and
                trace_b!=trace_h and mask_b!=mask_h and
                original_src==original_dst==old_b==old_h==1):
            raise ValueError("original real physical masked_copy event drift")
        mask_xor=mask_b^mask_h
        mask_bit0+=bool(mask_xor&1)
        mask_bit4+=bool(mask_xor&16)
        joint+=bool((mask_xor&17)==17)
        for operator in OPERATORS:
            hypo_b=apply_latent_operator(operator,original_src,original_dst,
                                          mask_b,rotate_amount=4)
            hypo_h=apply_latent_operator(operator,original_src,original_dst,
                                          mask_h,rotate_amount=4)
            if hypo_b!=hypo_h:
                totals[operator]+=1
                rows_by_operator[operator].append([
                    rel,native,address,source_slot,recipient_slot,
                    source_epoch,recipient_epoch,mask_b,mask_h,hypo_b,hypo_h,
                ])
    if (totals["masked_copy"],totals["masked_and"],totals["masked_xor"],
        totals["rotate_copy"],mask_bit0,mask_bit4,joint)!=(0,0,4,8,4,4,0):
        raise ValueError("retrospective operator witness frozen invariants changed")
    return {
        "schema":"UG_A19_EXPOSED_CONTACT_SINGLE_STEP_COUNTERFACTUAL_V1",
        "source_original_a14_event_rows_sha":source["source_pr_head_sha"],
        "original_r2_source_sha":source["old_r2_source_sha"],
        "positive_outcome_exposed_seed":544,
        "negative_exposed_seed":545,
        "positive_original_changed_mask_contacts":36,
        "negative_original_changed_mask_contacts":0,
        "original_actual_operator":"masked_copy",
        "original_actual_BH_recipient_contrast":0,
        "hypothetical_one_contact_BH_different_outputs":dict(totals),
        "changed_mask_difference_bit0":mask_bit0,
        "changed_mask_difference_bit4":mask_bit4,
        "changed_mask_difference_both_bits":joint,
        "hypothetical_event_rows_fields":[
            "relative_generation","native_generation","physical_address",
            "source_slot","recipient_slot","source_life_epoch",
            "recipient_life_epoch","native_mask_B","native_mask_H",
            "hypothetical_recipient_B","hypothetical_recipient_H",
        ],
        "hypothetical_distinguishing_rows":rows_by_operator,
        "heldout_consumed":False,
        "new_physics_executed":False,
        "independent_confirmation":False,
        "learning_claim":False,
        "interpretation":"One-event algebra only; trajectories diverge after any real operator switch. Never count these as real alternative-physics outcomes.",
    }


if __name__ == "__main__":
    print(json.dumps(original_contact_counterfactual(),sort_keys=True,
                     separators=(",",":")))
