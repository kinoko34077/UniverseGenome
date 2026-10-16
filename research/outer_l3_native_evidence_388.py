"""#388 O2-2: pure operator-aware source-selected native contact evidence checks.

NO UniverseState construction, no original/new physics step, seed selection,
native observer attachment or study execution. A supplied record can be
structurally consistent but NOT cryptographically or causally authenticated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from core.physics import LATENT_OPERATORS, apply_latent_operator
from research.a2_matched_recipient_contract_336 import (
    CONTACT_KEY, FIELDS, NONTRACE_CONTEXT,
)

_UINT16 = frozenset({
    "source_latent_before", "recipient_latent_before",
    "recipient_latent_after", "native_mask",
})
_UINT8 = frozenset({
    "source_trace_start", "source_bond_strength", "recipient_bond_strength",
})
_ALLOWED_NONTRACE_SHIFT = tuple(range(9))


@dataclass(frozen=True)
class NativeReadCheck:
    """Only arithmetic/source-structural eligibility, never actual proof."""

    native_key: tuple[int, ...]
    operator: str
    source_life_epoch: int
    recipient_life_epoch: int
    actual_receiver_after: int
    native_operator_identity_valid: bool = True
    actual_source_provenance_verified: bool = False
    causal_intervention_proven: bool = False
    cross_epoch_lineage_proven: bool = False
    independent_confirmation: bool = False
    learning_claim: bool = False


def _int(v: object, field: str, upper: int) -> int:
    if type(v) is not int or not 0 <= v <= upper:
        raise ValueError(f"invalid actual native {field}")
    return v


def check_native_operator_event(event: Mapping[str, object]) -> NativeReadCheck:
    """Verify all four actual native one-step operators on an observed-looking row.

    Requires the complete existing A2 native event schema, but permits every
    *registered* actual operator instead of A2's one fixed rotate-copy study.
    This is NOT a credential or original GitHub Actions source-authentication.
    """
    if type(event) is not dict or set(event) != set(FIELDS):
        raise ValueError("exact full native selected-contact fields required")
    key = tuple(_int(event[name], name, 2**63 - 1) for name in CONTACT_KEY)
    if key[2] == key[3]:
        raise ValueError("native selected contact cannot self-transfer")
    for field in NONTRACE_CONTEXT:
        v = event[field]
        if field.endswith("_xy"):
            if (type(v) not in (list, tuple) or len(v) != 2
                    or any(type(p) is not int or not 0 <= p <= 255 for p in v)):
                raise ValueError(f"invalid original native coordinate {field}")
        else:
            _int(v, field, 65535)
    for field in _UINT16:
        _int(event[field], field, 65535)
    for field in _UINT8:
        _int(event[field], field, 255)
    if event["trace_bonus_shift"] not in _ALLOWED_NONTRACE_SHIFT:
        raise ValueError("invalid original trace_bonus_shift")
    op = event["native_operator"]
    if type(op) is not str or op not in LATENT_OPERATORS:
        raise ValueError("unknown original native local latent operator")
    rotate = _int(event["rotate_amount"], "rotate_amount", 15)
    expected = apply_latent_operator(
        op, event["source_latent_before"],
        event["recipient_latent_before"], event["native_mask"],
        rotate_amount=rotate,
    )
    if expected != event["recipient_latent_after"]:
        raise ValueError("native operator-specific recipient-after identity failed")
    return NativeReadCheck(
        native_key=key, operator=op, source_life_epoch=key[4],
        recipient_life_epoch=key[5],
        actual_receiver_after=expected,
    )


def validate_native_operator_events(events: Sequence[dict]) -> tuple[NativeReadCheck, ...]:
    if type(events) not in (list, tuple) or len(events) > 200000:
        raise ValueError("bounded nonempty native directed evidence list required")
    if not events:
        raise ValueError("native source event list may not be empty")
    checks, used = [], set()
    for event in events:
        check = check_native_operator_event(event)
        if check.native_key in used:
            raise ValueError("duplicate native selected directed key/epoch")
        used.add(check.native_key)
        checks.append(check)
    return tuple(checks)


@dataclass(frozen=True)
class PairedNativeContactAssessment:
    classification: str
    native_key: tuple[int, ...] | None
    matched_source_context: bool
    native_source_provenance_verified: bool = False
    controlled_causal_trace_read_proven: bool = False
    turnover_proven: bool = False
    independent_learning_proven: bool = False


def compare_native_operator_contacts(
    baseline: dict, intervention: dict,
) -> PairedNativeContactAssessment:
    """Distinguish matched local physics from confounded downstream differences.

    Even an exactly matching nontrace snapshot plus a different resulting
    receiver is only a structurally possible *association* until genuine
    source-locked causal B-prestep clones/negative controls are authenticated.
    """
    left = check_native_operator_event(baseline)
    right = check_native_operator_event(intervention)
    if left.native_key != right.native_key:
        return PairedNativeContactAssessment(
            "DIFFERENT_ACTUAL_SELECTED_CONTACT", None, False,
        )
    if baseline["native_operator"] != intervention["native_operator"]:
        return PairedNativeContactAssessment(
            "OPERATOR_CHANGED_NOT_COMPARABLE", left.native_key, False,
        )
    if baseline["rotate_amount"] != intervention["rotate_amount"]:
        return PairedNativeContactAssessment(
            "ROTATION_CHANGED_NOT_COMPARABLE", left.native_key, False,
        )
    if any(baseline[k] != intervention[k] for k in NONTRACE_CONTEXT):
        return PairedNativeContactAssessment(
            "POST_TREATMENT_NONTRACE_CONTEXT_DIVERGENCE",
            left.native_key, False,
        )
    if baseline["source_trace_start"] == intervention["source_trace_start"]:
        return PairedNativeContactAssessment(
            "EQUAL_SOURCE_TRACE_NO_LOCAL_TRACE_TREATMENT",
            left.native_key, True,
        )
    if baseline["native_mask"] == intervention["native_mask"]:
        return PairedNativeContactAssessment(
            "TRACE_DIFFERENT_BUT_NATIVE_MASK_EQUAL",
            left.native_key, True,
        )
    if left.actual_receiver_after == right.actual_receiver_after:
        return PairedNativeContactAssessment(
            "TRACE_NATIVE_MASK_DIFFERENT_BUT_RECEIVER_EQUAL",
            left.native_key, True,
        )
    return PairedNativeContactAssessment(
        "STRUCTURALLY_ELIGIBLE_LOCAL_TRACE_READER_NOT_CAUSALLY_PROVEN",
        left.native_key, True,
    )
