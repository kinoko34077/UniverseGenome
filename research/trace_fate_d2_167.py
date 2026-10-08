"""#167 D2: frozen 40-case diagnostic execution and integrity-gated aggregation.

This is an observational consumer of accepted D1. It does NOT rank physics
candidates, use held-out evidence, or authorize a learning claim.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from research.phase_g_decay_axis_159 import case_once, load_frozen_contract
from research.phase_g_memory_search_159 import _digest
from research.trace_fate_diagnosis_167 import (
    CHECKPOINTS, MEASUREMENTS, OBSERVATION_SCHEMA, RATES,
    contract_digest, observe_case,
)

ISSUE = 167
D1_ACCEPTED_MAIN = "fa2d9df8e4ddab795e9731252af25078f5ff5f35"
RUN_HORIZON = 1000
SHARD_SIZE = 5
PARITY_HORIZONS = ("0", "1", "100", "1000")


def assignments(frozen: dict[str, Any]) -> list[tuple[int, str]]:
    return (
        [(seed, "search") for seed in frozen["search_cohort"]]
        + [(seed, "sentinel") for seed in frozen["search_negative_sentinels"]]
    )


def validate_observation(observed: dict[str, Any], *, rate: int,
                         seed: int, role: str, frozen: dict[str, Any]) -> None:
    if observed["artifact_digest"] != _digest(
        {k: v for k, v in observed.items() if k != "artifact_digest"}
    ):
        raise ValueError("tampered full D1 observation")
    expected = {
        "schema_version": OBSERVATION_SCHEMA, "issue": ISSUE,
        "kind": "post_g1_diagnostic_not_heldout",
        "seed": seed, "role": role, "decay_rate": rate,
        "max_horizon": RUN_HORIZON,
        "g0_digest": frozen["artifact_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "contract_digest": contract_digest(frozen),
        "heldout_max_horizon": 0, "learning_claim": False,
    }
    for field, value in expected.items():
        if observed.get(field) != value:
            raise ValueError(f"D2 observation contract mismatch: {field}")
    # JSON artifact serialization sorts object keys lexicographically;
    # checkpoint validity must not depend on mapping insertion order.
    if set(observed["checkpoint_branch_digests"]) != {
        str(n) for n in CHECKPOINTS
    }:
        raise ValueError("D2 checkpoint schema mismatch")
    if len(observed["trace_timeline"]) != RUN_HORIZON + 1:
        raise ValueError("D2 trace timeline incomplete")
    if len(observed["matched_read_timeline"]) != RUN_HORIZON:
        raise ValueError("D2 matched-read timeline incomplete")
    for branch in ("b", "h"):
        events = observed["event_timeline"][branch]
        if len(events) != RUN_HORIZON:
            raise ValueError("D2 event timeline incomplete")
        if [x["generation"] for x in events] != list(range(1, RUN_HORIZON + 1)):
            raise ValueError("D2 event generation discontinuity")
        for measurement in MEASUREMENTS:
            if observed["event_totals"][branch][measurement] != sum(
                item["counters"].get(measurement, 0) for item in events
            ):
                raise ValueError("D2 event accounting mismatch")
    for h in observed["checkpoints"].values():
        if h["control_vs_control_repeat"]["different"]:
            raise ValueError("duplicate control diverged")
        if role == "sentinel" and h["b_vs_h"]["different"]:
            raise ValueError("negative sentinel spontaneously distinguished B/H")


def run_case(*, seed: int, role: str, rate: int,
             source_sha: str) -> dict[str, Any]:
    frozen = load_frozen_contract()
    if (seed, role) not in assignments(frozen) or rate not in RATES:
        raise ValueError("seed or rate outside predeclared D2 evidence")
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("source SHA must be exact full hex commit")
    first = observe_case(seed=seed, role=role, decay_rate=rate,
                         max_horizon=RUN_HORIZON)
    validate_observation(first, rate=rate, seed=seed, role=role, frozen=frozen)
    repeat = observe_case(seed=seed, role=role, decay_rate=rate,
                          max_horizon=RUN_HORIZON)
    if repeat != first:
        raise ValueError("observed event timeline failed deterministic replay")
    baseline = case_once(
        seed=seed, role=role, decay_rate=rate, frozen=frozen,
        instrumented=False, max_horizon=RUN_HORIZON,
    )
    for h in PARITY_HORIZONS:
        if (first["checkpoint_branch_digests"][h]
                != baseline["checkpoints"][h]["branch_digests"] or
                first["checkpoints"][h]
                != baseline["checkpoints"][h]["comparisons"]):
            raise ValueError(f"raw-vs-observed authoritative parity mismatch at {h}")
    result = {
        "schema_version": 1, "issue": ISSUE, "phase": "D2",
        "accepted_d1_main": D1_ACCEPTED_MAIN,
        "source_sha": source_sha,
        "seed": seed, "role": role, "rate": rate,
        "g0_digest": frozen["artifact_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "contract_digest": contract_digest(frozen),
        "heldout_max_horizon": 0,
        "replay_clean": True, "raw_observed_parity_clean": True,
        "negative_control_clean": True, "duplicate_control_clean": True,
        "observation": first,
        "learning_claim": False,
    }
    result["artifact_digest"] = _digest(result)
    return result


def run_shard(*, rate: int, shard: int, source_sha: str,
              output_dir: Path) -> None:
    frozen = load_frozen_contract()
    if rate not in RATES or shard not in range(4):
        raise ValueError("outside frozen two-rate/four-shard D2 matrix")
    subset = assignments(frozen)[shard * SHARD_SIZE:(shard + 1) * SHARD_SIZE]
    if len(subset) != SHARD_SIZE:
        raise ValueError("incomplete D2 matrix shard")
    output_dir.mkdir(parents=True, exist_ok=True)
    for seed, role in subset:
        result = run_case(seed=seed, role=role, rate=rate, source_sha=source_sha)
        path = output_dir / f"case-{rate}-{seed}.json"
        path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "rate": rate, "seed": seed,
            "h100": result["observation"]["checkpoints"]["100"]["b_vs_h"]["different"],
            "h1000": result["observation"]["checkpoints"]["1000"]["b_vs_h"]["different"],
            "digest": result["artifact_digest"],
        }, sort_keys=True), flush=True)


def _transition_window(obs: dict[str, Any]) -> dict[str, Any]:
    first = obs["transitions"]["trace"]["first_reconvergence"]
    if first is None:
        return {"first_trace_reconvergence": None, "nearby_events": None}
    per_branch = {}
    for branch in ("b", "h"):
        rows = obs["event_timeline"][branch]
        counts: Counter = Counter()
        for row in rows:
            if first - 1 <= row["generation"] <= first + 1:
                counts.update(row["counters"])
        per_branch[branch] = dict(counts)
    return {
        "first_trace_reconvergence": first,
        "nearby_events": per_branch,
    }


def aggregate(directory: Path, *, source_sha: str) -> dict[str, Any]:
    frozen = load_frozen_contract()
    expected = {(rate, seed, role) for rate in RATES
                for seed, role in assignments(frozen)}
    files = list(directory.glob("case-*.json"))
    if len(files) != len(expected):
        raise ValueError(f"incomplete D2 matrix: {len(files)}/{len(expected)}")
    checked = {}
    for path in files:
        case = json.loads(path.read_text(encoding="utf-8"))
        d = case.pop("artifact_digest", None)
        if d != _digest(case):
            raise ValueError("tampered D2 case artifact")
        case["artifact_digest"] = d
        ident = (case["rate"], case["seed"], case["role"])
        if ident not in expected or ident in checked:
            raise ValueError("duplicate or unregistered D2 case")
        if (path.name != f"case-{case['rate']}-{case['seed']}.json"
                or case["source_sha"] != source_sha
                or case["accepted_d1_main"] != D1_ACCEPTED_MAIN
                or case["heldout_max_horizon"] != 0
                or case["learning_claim"] is not False
                or not all(case.get(k) is True for k in (
                    "replay_clean", "raw_observed_parity_clean",
                    "negative_control_clean", "duplicate_control_clean",
                ))):
            raise ValueError("D2 case provenance/validity mismatch")
        validate_observation(case["observation"], rate=ident[0],
                             seed=ident[1], role=ident[2], frozen=frozen)
        checked[ident] = case
    if set(checked) != expected:
        raise ValueError("D2 cohort coverage mismatch")

    rate_summaries = []
    for rate in RATES:
        search = [checked[rate, seed, "search"] for seed in frozen["search_cohort"]]
        sentinels = [checked[rate, seed, "sentinel"]
                     for seed in frozen["search_negative_sentinels"]]
        h100 = sum(c["observation"]["checkpoints"]["100"]["b_vs_h"]["different"]
                   for c in search)
        h1000 = sum(c["observation"]["checkpoints"]["1000"]["b_vs_h"]["different"]
                    for c in search)
        if (h100, h1000) != (13, 0):
            raise ValueError("D2 mismatch with accepted #159 G1 reference (13,0)")
        details = []
        for case in search:
            obs = case["observation"]
            details.append({
                "seed": case["seed"],
                "h0_trace_distinct": bool(
                    obs["checkpoints"]["0"]["b_vs_h"]["fields"]
                    ["slow_trace"]["changed_slots"]
                ),
                "h100_trace_distinct": bool(
                    obs["checkpoints"]["100"]["b_vs_h"]["fields"]
                    ["slow_trace"]["changed_slots"]
                ),
                "h1000_trace_distinct": bool(
                    obs["checkpoints"]["1000"]["b_vs_h"]["fields"]
                    ["slow_trace"]["changed_slots"]
                ),
                "transitions": obs["transitions"],
                "trace_loss_window": _transition_window(obs),
                "b_events": obs["event_totals"]["b"],
                "h_events": obs["event_totals"]["h"],
                "matched_reads": obs["physically_matched_reads"],
                "artifact_digest": case["artifact_digest"],
            })
        rate_summaries.append({
            "rate": rate, "search_count": len(search),
            "negative_sentinels": len(sentinels),
            "h100_distinct": h100, "h1000_distinct": h1000,
            "h0_trace_distinct": sum(x["h0_trace_distinct"] for x in details),
            "h100_trace_distinct": sum(x["h100_trace_distinct"] for x in details),
            "h1000_trace_distinct": sum(x["h1000_trace_distinct"] for x in details),
            "cases": details,
        })
    summary = {
        "schema_version": 1, "issue": ISSUE, "phase": "D2",
        "accepted_d1_main": D1_ACCEPTED_MAIN, "source_sha": source_sha,
        "g0_digest": frozen["artifact_digest"],
        "protocol_digest": frozen["protocol_digest"],
        "contract_digest": contract_digest(frozen),
        "case_count": 40, "heldout_max_horizon": 0,
        "valid": True, "learning_claim": False,
        "disposition": "EVIDENCE_ONLY_PENDING_D3",
        "rates": rate_summaries,
    }
    summary["artifact_digest"] = _digest(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run-shard", action="store_true")
    mode.add_argument("--aggregate-dir", type=Path)
    parser.add_argument("--rate", type=int)
    parser.add_argument("--shard", type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.run_shard:
        if args.output_dir is None or args.rate is None or args.shard is None:
            parser.error("--run-shard requires --output-dir/--rate/--shard")
        run_shard(rate=args.rate, shard=args.shard, source_sha=args.source_sha,
                  output_dir=args.output_dir)
    else:
        if args.output is None:
            parser.error("--aggregate-dir requires --output")
        summary = aggregate(args.aggregate_dir, source_sha=args.source_sha)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        print(json.dumps({
            "valid": summary["valid"], "case_count": summary["case_count"],
            "rates": [{
                "rate": x["rate"], "h100": x["h100_distinct"],
                "h1000": x["h1000_distinct"],
                "h0_trace_distinct": x["h0_trace_distinct"],
                "h100_trace_distinct": x["h100_trace_distinct"],
            } for x in summary["rates"]],
            "artifact_digest": summary["artifact_digest"],
        }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
