"""#363 source-only classification of *supplied* genuine selected contact records.

Authenticity is NOT established by this pure function. Original physics observer,
source lock and observed/unobserved parity must separately establish provenance.
"""
from __future__ import annotations
from collections import Counter
from typing import Any

from research.a2_matched_recipient_contract_336 import CONTACT_KEY, NONTRACE_CONTEXT, MAX_NATIVE_EVENTS
from tests.support_r2_masked_xor_contact_354 import _native_key

SCHEMA = "UG_L3_NATIVE_TRACE_CONTACT_ROUTE_363_V1"
REASONS = ("source_latent", "recipient_latent", "other_precontact")
FIRST_FIELDS = (
    "first_matched", "first_confounded", "first_trace_delta",
    "first_mask_delta", "first_after_delta", "first_comparable_trace_delta",
)


def classify_route(
    b_events: list[dict[str, Any]],
    h_events: list[dict[str, Any]],
    *,
    initial_trace_carrier_slots: set[int],
) -> dict[str, Any]:
    if not isinstance(initial_trace_carrier_slots, set) or any(
        type(z) is not int or z < 0 for z in initial_trace_carrier_slots
    ):
        raise ValueError("invalid frozen h0 carrier slot set")

    def index(events):
        if type(events) is not list or len(events) > MAX_NATIVE_EVENTS:
            raise ValueError("real source selected contact budget exceeded")
        result = {}
        for item in events:
            key = _native_key(item)
            if key in result:
                raise ValueError("duplicate life-epoch selected contact key")
            result[key] = item
        return result

    B, H = index(b_events), index(h_events)
    c = Counter()
    first = {k: None for k in FIRST_FIELDS}
    for side, index_ in (("B", B), ("H", H)):
        c[f"{side}_selected_directed"] = len(index_)
        c[f"{side}_h0_trace_carrier_source_events"] = sum(
            e["source_slot"] in initial_trace_carrier_slots
            and e["source_life_epoch"] == 0
            for e in index_.values()
        )
    for key in sorted(set(B) | set(H)):
        if key not in B or key not in H:
            c["unmatched_contact_keys"] += 1
            continue
        b, h = B[key], H[key]
        gen = key[0]
        c["matched_contact_keys"] += 1
        if first["first_matched"] is None:
            first["first_matched"] = gen
        diffs = [f for f in NONTRACE_CONTEXT if b[f] != h[f]]
        source_diff = b["source_latent_before"] != h["source_latent_before"]
        recipient_diff = b["recipient_latent_before"] != h["recipient_latent_before"]
        other_diff = any(
            f not in ("source_latent_before", "recipient_latent_before") for f in diffs
        )
        # 3-bit mutually exclusive partition; every matched key contributes once.
        group = ("S" if source_diff else "-") + (
            "R" if recipient_diff else "-"
        ) + ("O" if other_diff else "-")
        c["partition_"+group] += 1
        comparable = not diffs
        c["equal_nontrace_precontact" if comparable else "confounded_nontrace_precontact"] += 1
        if not comparable and first["first_confounded"] is None:
            first["first_confounded"] = gen
        for field in diffs:
            c["field_diff_"+field] += 1
        trace_delta = b["source_trace_start"] != h["source_trace_start"]
        mask_delta = b["native_mask"] != h["native_mask"]
        after_delta = b["recipient_latent_after"] != h["recipient_latent_after"]
        if trace_delta:
            c["source_trace_delta_all_matched"] += 1
            if first["first_trace_delta"] is None:
                first["first_trace_delta"] = gen
        if mask_delta:
            c["native_mask_delta_all_matched"] += 1
            if first["first_mask_delta"] is None:
                first["first_mask_delta"] = gen
        if after_delta:
            c["recipient_after_delta_all_matched"] += 1
            if first["first_after_delta"] is None:
                first["first_after_delta"] = gen
        if trace_delta and not comparable:
            c["source_trace_delta_confounded"] += 1
        if mask_delta and not comparable:
            c["native_mask_delta_confounded"] += 1
        if after_delta and not comparable:
            c["recipient_after_delta_confounded_NOT_CAUSAL"] += 1
        if comparable:
            if trace_delta:
                c["source_trace_delta_comparable"] += 1
                if first["first_comparable_trace_delta"] is None:
                    first["first_comparable_trace_delta"] = gen
            if mask_delta:
                c["native_mask_delta_comparable"] += 1
            if mask_delta and not trace_delta:
                raise ValueError("equal-context native masks diverge without trace")
            expected = (b["source_latent_before"] & (
                b["native_mask"] ^ h["native_mask"]
            ))
            actual = b["recipient_latent_after"] ^ h["recipient_latent_after"]
            if actual != expected:
                raise ValueError("comparable native XOR difference identity failed")
            if expected:
                c["effective_source_mask_overlap_comparable"] += 1
            if actual:
                c["recipient_after_delta_comparable"] += 1

    matched = c["matched_contact_keys"]
    if matched != c["equal_nontrace_precontact"] + c["confounded_nontrace_precontact"]:
        raise ValueError("not a total exhaustive native partition")
    if matched != sum(c["partition_"+g] for g in (
        "---", "--O", "-R-", "-RO", "S--", "S-O", "SR-", "SRO"
    )):
        raise ValueError("native stage partitions do not sum")
    if matched == 0:
        result = "NOT_EVALUABLE_NO_MATCHED_CONTACT"
    elif c["source_trace_delta_comparable"]:
        result = "TRACE_REACHED_COMPARABLE_CONTACT"
    elif c["source_trace_delta_confounded"]:
        result = "TRACE_DIFFERENCE_ONLY_IN_CONFOUNDED_CONTACTS"
    else:
        result = "NO_SOURCE_TRACE_CONTRAST_AT_MATCHED_CONTACTS"
    return {
        "schema": SCHEMA,
        "classification": result,
        "counts": dict(sorted(c.items())),
        "first_native_generation": first,
        "scope": "SUPPLIED_SOURCE_NATIVE_EVENTS_ONLY_NOT_SELF_AUTHENTICATING",
        "nontrace_confounded_receiver_delta_is_NOT_caused_by_trace": True,
        "independent_confirmation": False,
        "learning_claim": False,
    }
