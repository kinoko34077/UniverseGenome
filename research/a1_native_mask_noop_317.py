"""A1.3 #317: why genuine selected source-trace masks are locally inert.

Existing *outcome-exposed* R2 seed544 and negative seed545 only; read-only.
The observer calls the ORIGINAL native masked_copy on original branch states.
No counterfactual mutation, new cohort, learning, or causal generalization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import sys

from core.physics import apply_latent_operator
from research.a1_exposed_reader_pilot_317 import (
    SEEDS, BRANCHES, CAP_REPORT_BYTES, CAP_RSS_MIB, CAP_SECONDS,
    R2_FROZEN_DIGEST, check_budget, run_branch, sampled_max_rss_mib,
)
from research.a1_reader_provenance_317 import NONTRACE_FIELDS, PAIR_FIELDS
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import RATE, load_frozen
from research.phase_g_memory_search_159 import _digest

ISSUE = 317
SCHEMA = "UG_A1_MASK_NOOP_ORIGINAL_NATIVE_V1"
MAX_EXAMPLES = 12
EXPECTED_OPERATOR = "masked_copy"


def mask_effect(*, source: int, recipient: int, mask_b: int, mask_h: int) -> int:
    """Exact delta bits between ORIGINAL masked_copy outputs, no model changes."""
    if not all(0 <= x <= 65535 for x in (source, recipient, mask_b, mask_h)):
        raise ValueError("A1.3 masks and latents must be uint16")
    return (int(source) ^ int(recipient)) & (int(mask_b) ^ int(mask_h))


def classify(b_events: list[dict], h_events: list[dict]) -> dict:
    def index(events):
        result = {}
        for event in events:
            if any(name not in event for name in PAIR_FIELDS + NONTRACE_FIELDS):
                raise ValueError("missing original source/recipient provenance")
            if "recipient_latent_after" not in event or event["recipient_latent_after"] is None:
                raise ValueError("missing native physical recipient after-state")
            key = tuple(event[name] for name in PAIR_FIELDS)
            if key in result:
                raise ValueError("duplicate original physical life-epoch source event")
            result[key] = event
        return result
    b, h = index(b_events), index(h_events)
    counts = {
        "b_events": len(b_events), "h_events": len(h_events),
        "matched": 0, "unmatched_topology": 0,
        "confounded_nontrace": 0, "matched_trace_different": 0,
        "quantized_same_mask": 0, "different_mask": 0,
        "different_mask_algebraic_inert": 0, "different_mask_potential_latent_effect": 0,
        "different_mask_native_output_different": 0, "native_operator_parity_failures": 0,
    }
    examples = []
    for key in sorted(set(b) | set(h)):
        be, he = b.get(key), h.get(key)
        if be is None or he is None:
            counts["unmatched_topology"] += 1
            continue
        counts["matched"] += 1
        if any(be[name] != he[name] for name in NONTRACE_FIELDS):
            counts["confounded_nontrace"] += 1
            continue
        trace_diff = be["source_trace_start"] != he["source_trace_start"]
        mask_diff = be["native_mask"] != he["native_mask"]
        if trace_diff:
            counts["matched_trace_different"] += 1
        if trace_diff and not mask_diff:
            counts["quantized_same_mask"] += 1
        if not mask_diff:
            continue
        counts["different_mask"] += 1
        src = int(be["source_latent_before"])
        dst = int(be["recipient_latent_before"])
        mb, mh = int(be["native_mask"]), int(he["native_mask"])
        pb = apply_latent_operator(EXPECTED_OPERATOR, src, dst, mb)
        ph = apply_latent_operator(EXPECTED_OPERATOR, src, dst, mh)
        if pb != be["recipient_latent_after"] or ph != he["recipient_latent_after"]:
            counts["native_operator_parity_failures"] += 1
            raise ValueError("A1.3 source-native actual mask->recipient output mismatch")
        affected = mask_effect(source=src, recipient=dst, mask_b=mb, mask_h=mh)
        if (pb ^ ph) != affected:
            raise ValueError("A1.3 masked_copy algebra divergence")
        if affected:
            counts["different_mask_potential_latent_effect"] += 1
        else:
            counts["different_mask_algebraic_inert"] += 1
        if pb != ph:
            counts["different_mask_native_output_different"] += 1
        if len(examples) < MAX_EXAMPLES:
            examples.append({
                "key": list(key), "source_trace_bh": [be["source_trace_start"],he["source_trace_start"]],
                "mask_bh": [mb,mh], "source_latent_before": src,
                "recipient_latent_before": dst, "affected_bits": affected,
                "native_recipient_after_bh": [pb,ph],
            })
    return {"counts": counts, "examples": examples, "causal_readout_claim": False}


def analyze(*, source_sha: str) -> dict:
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("A1.3 source SHA required")
    cfg = profile(RATE)
    if cfg.latent_operator != EXPECTED_OPERATOR:
        raise ValueError("A1.3 only analyses unmodified original masked_copy; no substitutes")
    frozen = load_frozen()
    if frozen["digest"] != R2_FROZEN_DIGEST:
        raise ValueError("A1.3 original R2 manifest changed")
    start = time.perf_counter()
    observed = {}
    for seed in SEEDS:
        b = run_branch(seed, "b", frozen, start)
        h = run_branch(seed, "h", frozen, start)
        result = classify(b["events"], h["events"])
        if seed == 545 and (
            b["read_events_sha256"] != h["read_events_sha256"]
            or result["counts"]["matched_trace_different"] > 0
            or result["counts"]["different_mask"] > 0
        ):
            raise ValueError("A1.3 negative sentinel invalid")
        observed[str(seed)] = {
            "role": "exposed_positive" if seed == 544 else "exposed_negative",
            "b_events_sha256": b["read_events_sha256"],
            "h_events_sha256": h["read_events_sha256"],
            "checkpoints": {"b": b["checkpoint_digests"], "h": h["checkpoint_digests"]},
            **result,
        }
        check_budget(start)
    report = {
        "schema": SCHEMA, "owner": ISSUE, "source_sha": source_sha,
        "original_frozen_r2_manifest_digest": R2_FROZEN_DIGEST,
        "operator": EXPECTED_OPERATOR,
        "observed": observed,
        "environment": {
            "implementation": sys.implementation.name,
            "version": sys.version.split()[0],
            "max_rss_mib": sampled_max_rss_mib(),
            "elapsed_seconds": round(time.perf_counter()-start,3),
        },
        "finding_scope": "retrospective exact native masked_copy algebra, no causal or learning proof",
        "independent_confirmation": False, "learning_claim": False,
    }
    check_budget(start)
    report["digest"] = _digest(report)
    if len(json.dumps(report, sort_keys=True, separators=(",",":")).encode()) > CAP_REPORT_BYTES:
        raise ValueError("A1.3 report exceeds original retained compact cap")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = analyze(source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",",":"))+"\n", encoding="utf-8")
    print(json.dumps({
        "source_sha": result["source_sha"],
        "original_masked_copy_operator": result["operator"],
        "observed_counts": {k: v["counts"] for k,v in result["observed"].items()},
        "learning_claim": False,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
