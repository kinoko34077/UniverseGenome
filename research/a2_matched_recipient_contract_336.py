"""A2 #336 source-only native-recipient witness contract: NO physical experiment.

Inputs must be captured by a future AUTHORIZED observer of genuine
source-selected physical contacts. Synthetic tests here do NOT establish
a single original or alternate-physics outcome. No seed/world/step call.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from core.physics import apply_latent_operator

SCHEMA = "UG_A2_MATCHED_NATIVE_RECIPIENT_CONTACTS_V1"
CONTACT_KEY = (
    "native_generation", "physical_address",
    "source_slot", "recipient_slot",
    "source_life_epoch", "recipient_life_epoch",
)
NONTRACE_CONTEXT = (
    "source_xy", "recipient_xy",
    "source_structure", "recipient_structure",
    "source_direction", "recipient_direction",
    "source_speed_code", "recipient_speed_code",
    "source_hp", "recipient_hp",
    "source_bond_strength", "recipient_bond_strength",
    "source_latent_before", "recipient_latent_before",
    "trace_bonus_shift",
)
FIELDS = CONTACT_KEY + NONTRACE_CONTEXT + (
    "source_trace_start", "native_mask",
    "recipient_latent_after", "native_operator", "rotate_amount",
)
EXPECTED_OPERATOR = "rotate_copy"
EXPECTED_ROTATE = 4
MAX_NATIVE_EVENTS = 200000


def _canonical_event(event: dict) -> tuple:
    if set(event) != set(FIELDS):
        raise ValueError("A2 event must have exactly the native witness schema")
    for name in CONTACT_KEY:
        if type(event[name]) is not int or event[name] < 0:
            raise ValueError("A2 native key must be nonnegative integral")
    if event["source_slot"] == event["recipient_slot"]:
        raise ValueError("A2 self-transfer is not a true selected pair")
    for name in NONTRACE_CONTEXT:
        v = event[name]
        if name.endswith("_xy"):
            if not isinstance(v, (list, tuple)) or len(v) != 2 or any(
                type(n) is not int or n < 0 for n in v
            ):
                raise ValueError("invalid source-native physical coordinate")
        elif type(v) is not int or v < 0:
            raise ValueError("invalid source-native nontrace context")
    if not (
        0 <= event["source_latent_before"] <= 65535
        and 0 <= event["recipient_latent_before"] <= 65535
        and 0 <= event["recipient_latent_after"] <= 65535
        and 0 <= event["source_bond_strength"] <= 255
        and 0 <= event["recipient_bond_strength"] <= 255
        and 0 <= event["trace_bonus_shift"] <= 8
        and type(event["source_trace_start"]) is int
        and 0 <= event["source_trace_start"] <= 255
        and type(event["native_mask"]) is int
        and 0 <= event["native_mask"] <= 65535
        and event["native_operator"] == EXPECTED_OPERATOR
        and type(event["rotate_amount"]) is int
        and event["rotate_amount"] == EXPECTED_ROTATE
    ):
        raise ValueError("native original source mode/ranges are not satisfied")

    # The mask is a source-native observation, not constructed here.
    width = min(
        16,
        1 + (event["source_bond_strength"] >> 4)
        + (event["source_trace_start"] >> event["trace_bonus_shift"]),
    )
    if event["native_mask"].bit_count() != width:
        raise ValueError("native selected bit width does not match contact state")
    predicted = apply_latent_operator(
        EXPECTED_OPERATOR,
        event["source_latent_before"],
        event["recipient_latent_before"],
        event["native_mask"],
        rotate_amount=EXPECTED_ROTATE,
    )
    if event["recipient_latent_after"] != predicted:
        raise ValueError("native recipient_after not consistent with operator")
    return tuple(event[name] for name in CONTACT_KEY)


def compare_native_contact_witnesses(
    b_events: list[dict[str, Any]], h_events: list[dict[str, Any]]
) -> dict[str, Any]:
    """Count only directly matched physical contacts; never assert causality.

    A matched event has the same generation/address and both living source
    and recipient identities. Context-equal excludes all *observed* nontrace
    physical state differences, but does not prove unobserved causal identity.
    """

    def index(events):
        if len(events) > MAX_NATIVE_EVENTS:
            raise ValueError("A2 native per-branch event budget exceeded")
        result = {}
        for event in events:
            key = _canonical_event(event)
            if key in result:
                raise ValueError("duplicate native physical life-epoch contact")
            result[key] = event
        return result

    b_map = index(b_events)
    h_map = index(h_events)
    counts: Counter[str] = Counter({
        "matched_selected_contacts":0,
        "unmatched_topology":0,
        "confounded_precontext":0,
        "same_nontrace_context":0,
        "trace_difference_with_equal_context":0,
        "mask_difference_with_equal_context":0,
        "recipient_difference_with_equal_context":0,
        "trace_mask_recipient_difference_with_equal_context":0,
    })
    for key in sorted(set(b_map) | set(h_map)):
        if key not in b_map or key not in h_map:
            counts["unmatched_topology"] += 1
            continue
        counts["matched_selected_contacts"] += 1
        b, h = b_map[key], h_map[key]
        if any(b[f] != h[f] for f in NONTRACE_CONTEXT):
            counts["confounded_precontext"] += 1
            continue
        counts["same_nontrace_context"] += 1
        trace_diff = b["source_trace_start"] != h["source_trace_start"]
        mask_diff = b["native_mask"] != h["native_mask"]
        after_diff = b["recipient_latent_after"] != h["recipient_latent_after"]
        if not trace_diff and mask_diff:
            raise ValueError("same native source trace and state chose different mask")
        counts["trace_difference_with_equal_context"] += int(trace_diff)
        counts["mask_difference_with_equal_context"] += int(mask_diff)
        counts["recipient_difference_with_equal_context"] += int(after_diff)
        counts["trace_mask_recipient_difference_with_equal_context"] += int(
            trace_diff and mask_diff and after_diff
        )
    return {
        "schema": SCHEMA,
        "b_native_source_event_count": len(b_map),
        "h_native_source_event_count": len(h_map),
        "counts": dict(sorted(counts.items())),
        "native_event_source_required":True,
        "actual_alternate_physics_executed_here":False,
        "independent_confirmation":False,
        "teacher_specific_causal_learning_proven":False,
        "learning_claim":False,
        "interpretation":(
            "Pure counter of future AUTHENTIC native contact events only. "
            "Matched context and after-latent contrast are mechanistic "
            "observations, not randomized teacher-specific causal proof, "
            "lasting memory, or unseen learning."
        ),
    }
