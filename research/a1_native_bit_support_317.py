"""A1.4 #317: expose source/destination latent-bit support at real selected reads.

Only frozen, already outcome-exposed original R2 seeds 544 and 545.
No change to physics, RNG, genetic selection, teacher signal, or held-out roles.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

from core.physics import apply_latent_operator
from research.a1_exposed_reader_pilot_317 import (
    SEEDS, R2_FROZEN_DIGEST, CAP_REPORT_BYTES, check_budget, run_branch, sampled_max_rss_mib,
)
from research.a1_reader_provenance_317 import NONTRACE_FIELDS, PAIR_FIELDS
from research.a1_native_mask_noop_317 import mask_effect
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import RATE, h0_branches, load_frozen
from research.phase_g_memory_search_159 import _digest
from research.transduction_audit_120 import clone_state

SCHEMA = "UG_A1_NATIVE_BIT_SUPPORT_ORIGINAL_V1"
PERIODS = ((1, 100), (101, 250), (251, 500), (501, 1000))
EXPECTED_SELECTED = {544: (764, 95, 36), 545: (966, 0, 0)}
EXAMPLES_LIMIT = 36  # all changed-mask events; no post-hoc case selection


def period_for(relative_generation: int) -> str:
    if type(relative_generation) is not int:
        raise ValueError("native generation must be int")
    for lo, hi in PERIODS:
        if lo <= relative_generation <= hi:
            return f"{lo}-{hi}"
    raise ValueError("observed read generation outside frozen +1..+1000")


def event_index(events: list[dict]) -> dict[tuple, dict]:
    indexed = {}
    for e in events:
        if any(f not in e for f in (*PAIR_FIELDS, *NONTRACE_FIELDS,
                                      "native_mask", "source_trace_start",
                                      "recipient_latent_after")):
            raise ValueError("incomplete original source-native read event")
        if e["recipient_latent_after"] is None:
            raise ValueError("incomplete original physical recipient update")
        key = tuple(e[f] for f in PAIR_FIELDS)
        if key in indexed:
            raise ValueError("duplicate native reader pair/life epoch key")
        indexed[key] = e
    return indexed


def classify(b_events: list[dict], h_events: list[dict], *, h0_generation: int) -> dict:
    b, h = event_index(b_events), event_index(h_events)
    counts = Counter()
    stage = {f"{lo}-{hi}": Counter() for lo, hi in PERIODS}
    original_examples = []
    for key in sorted(set(b) | set(h)):
        eb, eh = b.get(key), h.get(key)
        if eb is None or eh is None:
            counts["unmatched_topology"] += 1
            continue
        relative_generation = int(eb["native_generation"]) - h0_generation + 1
        window = period_for(relative_generation)
        x = stage[window]
        counts["matched"] += 1
        x["matched"] += 1
        if any(eb[field] != eh[field] for field in NONTRACE_FIELDS):
            counts["confounded_nontrace"] += 1
            x["confounded_nontrace"] += 1
            continue
        trace_diff = eb["source_trace_start"] != eh["source_trace_start"]
        mask_diff = eb["native_mask"] != eh["native_mask"]
        if trace_diff:
            counts["trace_diff"] += 1
            x["trace_diff"] += 1
        if trace_diff and not mask_diff:
            counts["quantized_identical_mask"] += 1
            x["quantized_identical_mask"] += 1
        if not mask_diff:
            continue
        counts["changed_mask"] += 1
        x["changed_mask"] += 1
        source = int(eb["source_latent_before"])
        recipient = int(eb["recipient_latent_before"])
        m_b, m_h = int(eb["native_mask"]), int(eh["native_mask"])
        original_b = apply_latent_operator("masked_copy", source, recipient, m_b)
        original_h = apply_latent_operator("masked_copy", source, recipient, m_h)
        if (original_b != eb["recipient_latent_after"]
                or original_h != eh["recipient_latent_after"]):
            raise ValueError("original physical mask/recipient parity failure")
        support_xor = source ^ recipient
        changed_mask_xor = m_b ^ m_h
        effective = mask_effect(source=source, recipient=recipient,
                                mask_b=m_b, mask_h=m_h)
        if (original_b ^ original_h) != effective:
            raise ValueError("native masked_copy algebra mismatch")
        if support_xor == 0:
            category = "H1_equal_source_recipient_latent"
        elif (changed_mask_xor & support_xor) == 0:
            category = "H2_differing_latent_bits_unselected"
        else:
            category = "H3_nonzero_overlap_real_native_effect"
        counts[category] += 1
        x[category] += 1
        if effective and original_b == original_h:
            raise ValueError("latent overlap not reflected by native result")
        original_examples.append({
            "relative_generation": relative_generation, "period": window,
            "native_generation": int(eb["native_generation"]),
            "address": int(eb["address"]),
            "source_slot": int(eb["source_slot"]),
            "recipient_slot": int(eb["recipient_slot"]),
            "source_life_epoch_from_h0": int(eb["source_epoch"]),
            "recipient_life_epoch_from_h0": int(eb["recipient_epoch"]),
            "trace_bh": [int(eb["source_trace_start"]),int(eh["source_trace_start"])],
            "mask_bh": [m_b,m_h], "changed_mask_bitcount": changed_mask_xor.bit_count(),
            "source_latent_before": source, "recipient_latent_before": recipient,
            "source_recipient_xor": support_xor, "delta_mask_overlap": effective,
            "native_recipient_after_bh": [original_b,original_h], "class": category,
        })
    if len(original_examples) > EXAMPLES_LIMIT:
        raise ValueError("changed mask events exceed fixed full-detail retention budget")
    return {
        "source_events_b": len(b_events), "source_events_h": len(h_events),
        "counts": dict(sorted(counts.items())),
        "by_frozen_relative_period": {k:dict(sorted(v.items())) for k,v in stage.items()},
        "all_changed_mask_original_events": original_examples,
        "observational_only": True, "learning_claim": False,
    }


def analyze(*, source_sha: str) -> dict:
    if len(source_sha) != 40 or any(ch not in "0123456789abcdef" for ch in source_sha):
        raise ValueError("full source SHA required")
    frozen = load_frozen()
    if frozen["digest"] != R2_FROZEN_DIGEST or profile(RATE).latent_operator != "masked_copy":
        raise ValueError("original R2 manifest or native physics operator changed")
    start = time.perf_counter()
    report_by_seed = {}
    for seed in SEEDS:
        snapshots = h0_branches(seed)
        start_generation = int(clone_state(snapshots["b"],profile(RATE)).generation)
        if start_generation != clone_state(snapshots["h"],profile(RATE)).generation:
            raise ValueError("matched B/H h0 generation mismatch")
        rb = run_branch(seed,"b",frozen,start)
        rh = run_branch(seed,"h",frozen,start)
        observed = classify(rb["events"],rh["events"],h0_generation=start_generation)
        original = EXPECTED_SELECTED[seed]
        c = observed["counts"]
        if (c.get("matched",0),c.get("trace_diff",0),c.get("changed_mask",0)) != original:
            raise ValueError("A1.3 source-native original event denominator mismatch")
        if c.get("confounded_nontrace",0) or c.get("unmatched_topology",0):
            raise ValueError("previous accepted same-topology/nontrace evidence drift")
        if seed == 545 and rb["read_events_sha256"] != rh["read_events_sha256"]:
            raise ValueError("original negative sentinel B/H selected reader mismatch")
        if seed == 544 and sum(c.get(x,0) for x in (
            "H1_equal_source_recipient_latent",
            "H2_differing_latent_bits_unselected",
            "H3_nonzero_overlap_real_native_effect")) != 36:
            raise ValueError("original changed-mask cases not exhaustively classified")
        report_by_seed[str(seed)] = {
            "role":"exposed_positive" if seed==544 else "exposed_negative",
            "h0_native_generation": start_generation,
            "original_event_hashes":{"b":rb["read_events_sha256"],"h":rh["read_events_sha256"]},
            "original_r2_checkpoints":{"b":rb["checkpoint_digests"],"h":rh["checkpoint_digests"]},
            **observed,
        }
        check_budget(start)
    result = {
        "schema": SCHEMA, "source_sha": source_sha, "owner_issue":317,
        "previous_source_A1_3": "63ca219f807e184408e0a42640c5a7496938dd4c",
        "old_R2_manifest_digest": R2_FROZEN_DIGEST,
        "frozen_seed_roles":{"544":"previously_exposed_positive","545":"previously_exposed_negative"},
        "horizon":1000, "periods_relative_to_h0":[[a,b] for a,b in PERIODS],
        "native_operator":"masked_copy","research_write_rule":"unit_add",
        "observed": report_by_seed,
        "environment":{"runtime":sys.implementation.name,"version":sys.version.split()[0],
                       "max_rss_mib":sampled_max_rss_mib(),
                       "wall_s":round(time.perf_counter()-start,3)},
        "independent_confirmation":False,"learning_claim":False,
    }
    check_budget(start)
    result["digest"] = _digest(result)
    raw=json.dumps(result,sort_keys=True,separators=(",",":")).encode()
    if len(raw)>CAP_REPORT_BYTES:
        raise ValueError("research retained summary size cap exceeded")
    return result

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=analyze(source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"schema":SCHEMA,"counts":{s:v["counts"] for s,v in result["observed"].items()},
                      "rss_mib":result["environment"]["max_rss_mib"],"learning_claim":False},
                     sort_keys=True),flush=True)

if __name__=="__main__":
    main()
