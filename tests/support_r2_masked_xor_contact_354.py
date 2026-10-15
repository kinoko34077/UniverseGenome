"""#354 reference-only masked_xor directed-contact contract.

Takes purported native event dictionaries; validates internal physical/mask arithmetic.
Cannot independently prove that an event came from a genuine source-native run.
No universe construction, h0 qualification, physics stepping, or external I/O.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from core.physics import apply_latent_operator
from research.a2_matched_recipient_contract_336 import (
    CONTACT_KEY, NONTRACE_CONTEXT, FIELDS, MAX_NATIVE_EVENTS,
)

SCHEMA = "UG_R2_MASKED_XOR_SOURCE_ONLY_CONTACT_WITNESS_V0_354"
OPERATOR = "masked_xor"


def _native_key(event: dict[str, Any]) -> tuple[int, ...]:
    if not isinstance(event, dict) or set(event) != set(FIELDS):
        raise ValueError("invalid source-native witness schema")
    for name in CONTACT_KEY:
        if type(event[name]) is not int or event[name] < 0:
            raise ValueError("invalid native directed-contact identity")
    if event["source_slot"] == event["recipient_slot"]:
        raise ValueError("self-transfer cannot represent a selected native pair")
    for name in NONTRACE_CONTEXT:
        value = event[name]
        if name.endswith("_xy"):
            if (not isinstance(value, (list, tuple)) or len(value) != 2
                    or any(type(v) is not int or v < 0 for v in value)):
                raise ValueError("invalid native coordinates")
        elif type(value) is not int or value < 0:
            raise ValueError("invalid native precontact context")
    for name in ("source_latent_before", "recipient_latent_before",
                 "recipient_latent_after", "native_mask"):
        if type(event[name]) is not int or not 0 <= event[name] <= 65535:
            raise ValueError("invalid 16-bit value")
    for name in ("source_bond_strength", "recipient_bond_strength",
                 "source_trace_start"):
        if type(event[name]) is not int or not 0 <= event[name] <= 255:
            raise ValueError("invalid 8-bit native value")
    if (type(event["trace_bonus_shift"]) is not int
            or not 0 <= event["trace_bonus_shift"] <= 8):
        raise ValueError("invalid trace width-shift")
    if (event["native_operator"] != OPERATOR
            or type(event["rotate_amount"]) is not int
            or event["rotate_amount"] != 4):
        raise ValueError("wrong physical operator/rotate amount")
    width = min(16, 1 + (event["source_bond_strength"] >> 4)
                + (event["source_trace_start"] >> event["trace_bonus_shift"]))
    if event["native_mask"].bit_count() != width:
        raise ValueError("native-selected mask width invalid")
    expected = apply_latent_operator(
        OPERATOR,
        event["source_latent_before"],
        event["recipient_latent_before"],
        event["native_mask"],
        rotate_amount=4,
    )
    if event["recipient_latent_after"] != expected:
        raise ValueError("recipient-after contradicts native masked_xor semantics")
    return tuple(event[k] for k in CONTACT_KEY)


def classify_purported_native_contacts(
    b_events: list[dict[str, Any]], h_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Conservative, pure comparison of supplied records, NOT proof of origin."""

    def indexed(events: list[dict[str, Any]]) -> dict[tuple[int, ...], dict]:
        if not isinstance(events, list) or len(events) > MAX_NATIVE_EVENTS:
            raise ValueError("native contact event bound exceeded")
        indexed_events: dict[tuple[int, ...], dict] = {}
        for event in events:
            key = _native_key(event)
            if key in indexed_events:
                raise ValueError("duplicate native life-epoch contact key")
            indexed_events[key] = event
        return indexed_events

    b_map, h_map = indexed(b_events), indexed(h_events)
    counters = Counter({
        "matched_contacts": 0,
        "unmatched_contacts": 0,
        "confounded_precontact": 0,
        "comparable_precontact": 0,
        "source_trace_different": 0,
        "native_mask_different": 0,
        "mask_xor_source_support_nonzero": 0,
        "recipient_after_different": 0,
    })
    for key in sorted(set(b_map) | set(h_map)):
        if key not in b_map or key not in h_map:
            counters["unmatched_contacts"] += 1
            continue
        counters["matched_contacts"] += 1
        b, h = b_map[key], h_map[key]
        if any(b[f] != h[f] for f in NONTRACE_CONTEXT):
            counters["confounded_precontact"] += 1
            continue
        counters["comparable_precontact"] += 1
        trace_diff = b["source_trace_start"] != h["source_trace_start"]
        mask_diff = b["native_mask"] != h["native_mask"]
        delta = b["source_latent_before"] & (b["native_mask"] ^ h["native_mask"])
        observed = b["recipient_latent_after"] ^ h["recipient_latent_after"]
        if mask_diff and not trace_diff:
            raise ValueError("same trace and context yielded unequal native masks")
        if observed != delta:
            raise ValueError("native B/H receiver difference contradicts effect support")
        counters["source_trace_different"] += int(trace_diff)
        counters["native_mask_different"] += int(mask_diff)
        counters["mask_xor_source_support_nonzero"] += int(delta != 0)
        counters["recipient_after_different"] += int(observed != 0)
    if counters["comparable_precontact"] == 0:
        classification = "NOT_EVALUABLE_NO_SEED_REPLACEMENT"
    elif counters["recipient_after_different"]:
        classification = "LOCAL_RECEIVER_EFFECT_RETENTION_UNRESOLVED"
    else:
        classification = "NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT"
    return {
        "schema": SCHEMA,
        "classification": classification,
        "b_count": len(b_map),
        "h_count": len(h_map),
        "counts": dict(sorted(counters.items())),
        "synthetic_or_supplied_events_only": True,
        "native_source_provenance_verified_here": False,
        "scientific_study_accepted_here": False,
        "actual_native_experiment_executed_here": False,
        "long_term_retention": "NOT_ESTABLISHED",
        "independent_confirmation": False,
        "learning_claim": False,
    }
