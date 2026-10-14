"""#336: pre-outcome, pure A2 E2 native-effect validity classifier.

Consumes ONLY an already-produced report; imports no physics or seed runner.
A matched immediate recipient effect and long-term lineage are separate axes.
Synthetic tests are NOT scientific evidence. No persistent-memory/L3 promotion.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "UG_A2_E2_EXPOSED_OUTCOME_CLASSIFIER_V1"
INPUT_SCHEMA = "UG_A2_RESEARCH_ONLY_ROTATE_COPY_EXPOSED_PILOT_V1"
CONTACT_SCHEMA = "UG_A2_MATCHED_NATIVE_RECIPIENT_CONTACTS_V1"
HORIZONS = frozenset(("0", "1", "10", "100", "250", "500", "1000"))
INVALID = "NOT_EVALUABLE_NO_POSTHOC_SEED_REPLACEMENT"
NEGATIVE = "NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT"
UNRESOLVED = "LOCAL_RECEIVER_EFFECT_RETENTION_UNRESOLVED"
COUNT_KEYS = (
    "matched_selected_contacts", "unmatched_topology",
    "confounded_precontext", "same_nontrace_context",
    "trace_difference_with_equal_context",
    "mask_difference_with_equal_context",
    "recipient_difference_with_equal_context",
    "trace_mask_recipient_difference_with_equal_context",
)


def _invalid(reason: str, counts: dict | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "validity": "NOT_EVALUABLE",
        "reason": reason, "classification": INVALID,
        "local_receiver_effect": "NOT_EVALUABLE",
        "long_term_retention": "NOT_ESTABLISHED",
        "counts": counts or {},
        "no_teacher_reference_used": False,
        "independent_confirmation": False,
        "learning_claim": False,
    }


def classify_report(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("schema") != INPUT_SCHEMA:
        return _invalid("INVALID_SOURCE_REPORT_SCHEMA")
    for flag in ("original_masked_copy_golden_parity",
                 "negative_BH_full_equality", "positive_BB_sham_full_equality"):
        if report.get(flag) is not True:
            return _invalid("FAILED_OR_MISSING_CONTROL_" + flag.upper())
    if (report.get("independent_confirmation") is not False
            or report.get("learning_claim") is not False):
        return _invalid("UNAUTHORIZED_INDEPENDENT_OR_LEARNING_CLAIM")
    conditions = report.get("conditions")
    if not isinstance(conditions, dict) or (
        conditions.get("positive_exposed_seed") != 544
        or conditions.get("negative_exposed_seed") != 545
        or conditions.get("teacher_B_H") != [66, 8]
        or conditions.get("post_h0_native_steps") != 1000
        or conditions.get("treatment_operator") != "rotate_copy"
        or conditions.get("baseline_operator") != "masked_copy"
        or conditions.get("rotate_amount") != 4
        or conditions.get("trace_decay_rate") != 256
        or conditions.get("only_physical_config_delta") != "latent_operator"
    ):
        return _invalid("CHANGED_FROZEN_STUDY_CONDITIONS")
    environment = report.get("environment")
    if not isinstance(environment, dict):
        return _invalid("MISSING_HOST_BUDGET")
    seconds, rss = environment.get("wall_seconds"), environment.get("rss_mib")
    if (type(seconds) not in (float, int) or type(rss) not in (float, int)
            or seconds < 0 or seconds > 900 or rss < 0 or rss > 1536):
        return _invalid("RESOURCE_BOUND_OR_HOST_EVIDENCE_FAILED")
    data = report.get("data")
    if not isinstance(data, dict) or set(data) != {"544", "545"}:
        return _invalid("INVALID_EXPOSED_SEED_ROSTER")
    if not isinstance(data["544"], dict) or not isinstance(data["545"], dict):
        return _invalid("INVALID_ROLE_RECORDS")
    if set(data["544"]) != {"b", "h", "control"} or set(data["545"]) != {"b", "h"}:
        return _invalid("MISSING_NO_TEACHER_OR_SENTINEL")
    for seed, roles in data.items():
        for role, record in roles.items():
            if not isinstance(record, dict) or record.get("seed") != int(seed) or record.get("role") != role:
                return _invalid("INVALID_BRANCH_PROVENANCE")
            if (record.get("uninstrumented_full_state_parity") is not True
                or not isinstance(record.get("checkpoints"), dict)
                or set(record["checkpoints"]) != HORIZONS
                or type(record.get("native_selected_events")) is not int
                or record["native_selected_events"] < 0
                or record["native_selected_events"] > 200000):
                return _invalid("INVALID_BRANCH_PARITY_OR_EVENT_BUDGET")
    neg = data["545"]
    for field in ("original_h0_sha256", "native_selected_events",
                  "native_selected_event_sha256", "native_free_event_sha256",
                  "checkpoints"):
        if neg["b"].get(field) != neg["h"].get(field):
            return _invalid("NEGATIVE_SENTINEL_DIVERGED_" + field.upper())
    # Source-distinct no-teacher original h0 is a required reference, NOT a B/H
    # bitwise-identical sham. Do not require control == either teacher branch.
    ctrl = data["544"]["control"]
    if not isinstance(ctrl.get("original_h0_sha256"), str):
        return _invalid("MISSING_CANONICAL_NO_TEACHER_REFERENCE")
    contrast = report.get("positive_native_paired_read_contrast")
    if not isinstance(contrast, dict) or contrast.get("schema") != CONTACT_SCHEMA:
        return _invalid("MISSING_NATIVE_MATCHED_WITNESS")
    counts = contrast.get("counts")
    if (not isinstance(counts, dict) or
            any(type(counts.get(k)) is not int or counts[k] < 0 for k in COUNT_KEYS)):
        return _invalid("INVALID_NATIVE_CONTACT_COUNTS")
    matched = counts["matched_selected_contacts"]
    same = counts["same_nontrace_context"]
    trace = counts["trace_difference_with_equal_context"]
    mask = counts["mask_difference_with_equal_context"]
    receiver = counts["recipient_difference_with_equal_context"]
    triple = counts["trace_mask_recipient_difference_with_equal_context"]
    if (matched != same + counts["confounded_precontext"]
            or same < trace or trace < mask or receiver != triple
            or receiver > mask):
        return _invalid("INCONSISTENT_SOURCE_NATIVE_CAUSAL_DENOMINATORS", counts)
    if matched == 0 or same == 0:
        return _invalid("EMPTY_OR_ONLY_CONFOUNDED_MATCHED_CONTACTS", counts)
    effect = "OBSERVED_MATCHED_NATIVE_RECEIVER_DELTA" if receiver else "NO_MATCHED_NATIVE_RECEIVER_DELTA"
    # There is no per-carrier/epoch survival proof in this compact report.
    # An immediate change can neither be called TRANSIENT nor PERSISTENT here.
    return {
        "schema": SCHEMA,
        "validity": "CONTROLS_AND_MATCHED_CONTACT_COUNTS_VALID",
        "reason": "SOURCE_DISTINCT_NO_TEACHER_REFERENCE_INCLUDED",
        "classification": UNRESOLVED if receiver else NEGATIVE,
        "local_receiver_effect": effect,
        "long_term_retention": "NOT_ESTABLISHED",
        "counts": {key: counts[key] for key in COUNT_KEYS},
        "no_teacher_reference_used": True,
        "independent_confirmation": False,
        "learning_claim": False,
    }
