"""#363 E1: predeclared choice of an exposed original selected native contact.

PURE SOURCE-ONLY selector. This does not authenticate supplied events, execute
physics, read intervention outcomes, or permit a new original experiment.
The source-locked E1 runner must separately prove genuine branch provenance,
capture pre-step state, and compare the same native event under intervention.
"""
from __future__ import annotations

from research.a2_matched_recipient_contract_336 import CONTACT_KEY, MAX_NATIVE_EVENTS

INITIAL_H0_CARRIER_SLOT = 31
ORIGINAL_LIFE_EPOCH = 0


def first_h0_carrier_trace_contrast(b_events: list[dict], h_events: list[dict]):
    """Select FIRST matched selected directed contact on frozen input criteria.

    Does not inspect mask, recipient-after, outcome, or post-step information.
    Return None rather than using a post-outcome alternative when ineligible.
    """
    def index(events):
        if type(events) is not list or len(events) > MAX_NATIVE_EVENTS:
            raise ValueError("E1 genuine native event budget invalid")
        result = {}
        for e in events:
            key = tuple(e[name] for name in CONTACT_KEY)
            if any(type(v) is not int or v < 0 for v in key):
                raise ValueError("E1 invalid original selected native key")
            value = e["source_trace_start"]
            if type(value) is not int or not 0 <= value <= 255:
                raise ValueError("E1 native source trace must be uint8")
            if key in result:
                raise ValueError("E1 duplicate authentic directed contact key")
            result[key] = value
        return result

    b = index(b_events)
    h = index(h_events)
    for key in sorted(b.keys() & h.keys()):
        if (key[CONTACT_KEY.index("source_slot")] == INITIAL_H0_CARRIER_SLOT
                and key[CONTACT_KEY.index("source_life_epoch")] == ORIGINAL_LIFE_EPOCH
                and b[key] != h[key]):
            return {
                "native_key": dict(zip(CONTACT_KEY, key)),
                "baseline_B_source_trace": b[key],
                "intervention_H_source_trace": h[key],
                "selection_basis": "FIRST_MATCHED_ORIGINAL_H0_CARRIER_TRACE_CONTRAST",
                "provenance_verified_here": False,
                "recipient_outcome_inspected": False,
            }
    return None
