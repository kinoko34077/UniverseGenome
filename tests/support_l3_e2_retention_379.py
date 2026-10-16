"""E2 #379 pure source-only downstream retention and native life-epoch evidence rules.

No universe construction, no step, no native original 544/545 experiment.
A supplied contact record is NOT independently authenticated by this module.
The future E2 runner must source-lock E0/E1 and prove original native provenance.
"""
from __future__ import annotations

from research.a2_matched_recipient_contract_336 import (
    CONTACT_KEY, NONTRACE_CONTEXT,
)

ORIGINAL_PRESTEP_GENERATION = 49
ORIGINAL_POSTSTEP_GENERATION = 50
ORIGINAL_SELECTED_IDENTITY = (31, 0, 22, 0)
POST_H0_STEPS = (1, 10, 100, 250, 500, 1000)
POST_SELECTED_ADDITIONAL_STEPS = (0, 1, 10, 100, 250, 500, 1000)
# Mechanical context can diverge after an intervention. Such events are
# total downstream outcomes, never a new locally isolated reader effect.
MECHANICAL_CONTEXT = tuple(
    field for field in NONTRACE_CONTEXT
    if field not in ("source_latent_before", "recipient_latent_before")
)


def horizon_plan(h0_snapshot_generation: int) -> dict:
    """Bind BOTH absolute and relative clocks before examining outcomes.

    A native step starting at generation 49 produces snapshot generation 50.
    H0 post-step 1000 is distinct from 1000 ADDITIONAL steps after E1.
    """
    if (type(h0_snapshot_generation) is not int
            or not 0 <= h0_snapshot_generation < ORIGINAL_PRESTEP_GENERATION):
        raise ValueError("require authentic H0 generation before E1 contact")
    return {
        "h0_snapshot_generation": h0_snapshot_generation,
        "original_contact_pre_generation": ORIGINAL_PRESTEP_GENERATION,
        "original_contact_post_generation": ORIGINAL_POSTSTEP_GENERATION,
        "post_h0": [
            {"post_h0_steps": x, "absolute_snapshot_generation": h0_snapshot_generation + x}
            for x in POST_H0_STEPS
        ],
        "post_selected": [
            {"additional_steps_after_selected": x,
             "absolute_snapshot_generation": ORIGINAL_POSTSTEP_GENERATION + x}
            for x in POST_SELECTED_ADDITIONAL_STEPS
        ],
        "required_last_generation": max(
            h0_snapshot_generation + POST_H0_STEPS[-1],
            ORIGINAL_POSTSTEP_GENERATION + POST_SELECTED_ADDITIONAL_STEPS[-1],
        ),
    }


def _identity(event: dict, prefix: str) -> tuple[int, int]:
    slot, epoch = event[prefix + "_slot"], event[prefix + "_life_epoch"]
    if (type(slot) is not int or slot < 0
            or type(epoch) is not int or epoch < 0):
        raise ValueError("invalid original native slot/life epoch")
    return slot, epoch


def classify_paired_native_edge(
    baseline: dict, intervention: dict, *,
    affected_source_epochs: frozenset[tuple[int, int]],
    living_recipient_epochs: frozenset[tuple[int, int]],
) -> dict:
    """Assess evidence eligibility, NEVER assert an inherited memory.

    Input requires separately authenticated SAME native selected contact in
    both arms. XOR identity is a necessary check, NOT causal provenance by
    itself, especially after post-treatment mechanical divergence.
    """
    if not isinstance(baseline, dict) or not isinstance(intervention, dict):
        raise ValueError("missing two actual selected-event records")
    required = set(CONTACT_KEY) | set(NONTRACE_CONTEXT) | {
        "native_mask", "recipient_latent_after",
    }
    if not required.issubset(baseline) or not required.issubset(intervention):
        raise ValueError("incomplete source-native selected contact")
    if (type(affected_source_epochs) is not frozenset
            or type(living_recipient_epochs) is not frozenset
            or any(type(z) is not tuple or len(z) != 2
                   or any(type(v) is not int or v < 0 for v in z)
                   for z in affected_source_epochs | living_recipient_epochs)):
        raise ValueError("missing vetted physical epoch witnesses")

    for e in (baseline, intervention):
        for field in CONTACT_KEY:
            if type(e[field]) is not int or e[field] < 0:
                raise ValueError("invalid original native selected key")
        for field in ("source_latent_before", "recipient_latent_before",
                      "recipient_latent_after", "native_mask"):
            if type(e[field]) is not int or not 0 <= e[field] <= 65535:
                raise ValueError("invalid native uint16 read/witness")
    key = tuple(baseline[name] for name in CONTACT_KEY)
    if key != tuple(intervention[name] for name in CONTACT_KEY):
        return {"classification": "NOT_COMPARABLE_DIFFERENT_NATIVE_SELECTED_CONTACT"}
    src = _identity(baseline, "source")
    recipient = _identity(baseline, "recipient")
    if src == recipient:
        raise ValueError("source and recipient share the same physical epoch")
    if any(baseline[f] != intervention[f] for f in MECHANICAL_CONTEXT):
        return {"classification": "POST_TREATMENT_MECHANICAL_CONTEXT_DIVERGENCE",
                "source_epoch": list(src), "recipient_epoch": list(recipient)}
    # Native masked_xor actual transmission stage, with potentially different
    # recipient/source pre-latent; do NOT require those values to be equal.
    before_xor = (baseline["recipient_latent_before"]
                  ^ intervention["recipient_latent_before"])
    contribution = ((baseline["source_latent_before"] & baseline["native_mask"])
                    ^ (intervention["source_latent_before"] & intervention["native_mask"]))
    after_xor = (baseline["recipient_latent_after"]
                 ^ intervention["recipient_latent_after"])
    if (before_xor ^ contribution) != after_xor:
        raise ValueError("native selected directed masked_xor identity failed")
    if src not in affected_source_epochs:
        classification = "SOURCE_NOT_IN_VERIFIED_PERTURBATION_PATH"
    elif not contribution:
        classification = "NO_NEW_NATIVE_MASKED_SOURCE_BIT_DELTA"
    elif recipient not in living_recipient_epochs:
        classification = "RECIPIENT_EPOCH_NOT_VERIFIED_LIVING"
    else:
        classification = "CANDIDATE_NATIVE_EDGE_REQUIRES_CHAIN_AND_TURNOVER_PROOF"
    return {
        "classification": classification,
        "native_key": dict(zip(CONTACT_KEY, key)),
        "source_epoch": list(src), "recipient_epoch": list(recipient),
        "native_source_masked_contribution_xor": contribution,
        "recipient_before_xor": before_xor,
        "recipient_after_xor": after_xor,
        "event_provenance_verified_here": False,
        "physical_turnover_or_retention_proven_here": False,
        "independent_confirmation": False,
        "learning_claim": False,
    }
