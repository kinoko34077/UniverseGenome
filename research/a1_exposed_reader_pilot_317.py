"""A1.2 #317: original R2 exposed-seed reader provenance pilot (read-only).

No new seed, physics, genetics, teacher signal, or candidate tuning.
Do not interpret matched B/H latent differences as an independent causal effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import resource
import sys
import time

from core.experiment import IOExperiment
from research.a1_reader_provenance_317 import ReadOnlyReaderProvenance, compare_branches
from research.phase_g_memory_search_159 import _digest, _load_protocol
from research.r1_causal_isolation_172 import profile
from research.r2_write_rules_175 import (
    LocalWriteRule, RATE, HORIZONS, h0_branches, load_frozen,
)
from research.transduction_audit_120 import canonical_digest, clone_state

ISSUE = 317
SEEDS = (544, 545)  # predeclared outcome-exposed R2 positive and negative
ROLES = {544: "positive", 545: "negative"}
BRANCHES = ("b", "h")
R2_ORIGINAL_SOURCE = "af568ac1558f2f3f86e51341208f5b51557b7a39"
R2_FROZEN_DIGEST = "3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543"
R2_ORIGINAL_ZIP_SHAS = {
    544: "682aa608a31d1ad1d30905ee85e9a94b5691f63889ca228d9c87f43b0c1a2165",
    545: "8944bd0d21b4db05ed63f1d99eff47e4fbb8ab4bde3627398ac2b8d91668df1e",
}
HORIZON = 1000
CAP_SECONDS = 900.0
CAP_RSS_MIB = 1536.0
CAP_EVENTS = 200000
CAP_REPORT_BYTES = 128 * 1024

# Original accepted R2 case JSON: sharded Actions 37950076024, unit_add profile.
# Checkpoint digests are *authoritative original-case snapshot digests*,
# not new A1 outcomes. Sorted horizons preserved exactly from original R2.
GOLDEN = {
 544: {
  "b": {
   "1": "a778f7796c5e631e89a38188d42bfb45975f32d372406e14fd979a4033658bcb",
   "10": "851f1a10bf0107db248042b78dc9c47247ed75c5291a9bbd0f0b9c044983b290",
   "100": "29baf9421123f584ac1afd5a91aa964896441c36eb6bc2fb09c88f6e30d0d3e2",
   "250": "a325a369426dc4c9fac20bd57574f8e90df60948bfbb9841f466707285ba7772",
   "500": "da2e1d41909b0c56317c8bc8ca9f2a0397806b6168a24b8279f17cd900c962cf",
   "1000": "aab79bdf2717851af356f0900228a43af952b32eb4b1eab5ca8ac50078badd53",
  },
  "h": {
   "1": "bb474995f46f1de7a29f19b672f7474f5e3d2cef38c6a7c28eee534e8eb33918",
   "10": "e2aa269888301267fe5a25b46eb90329fe169550897523788345efff81fbb45f",
   "100": "e3d57095877a3080439363cc448b5c0af965d988948582d5f21e1e8a0b39aca9",
   "250": "bcc856f3b5515b79d723db06dd05c0ef8955d5425d4f5c46b94e3237146871f2",
   "500": "d6a4d824e389b4fc5e3b3af54aad9fbe7794fb634cc5441ad45495592712cccf",
   "1000": "8259f46b73e2f0335d80b8dbd057ec39158023178028a648aedfff2a191e7b70",
  },
 },
 545: {
  "b": {
   "1": "145c0d1312382974c9c93a7e367800ef1cce41b06b740eaa5ce6df48b2d7062d",
   "10": "85020b1b7fa738d94efad3efad21119d59fdd3db1ee3f0659471528bd951b499",
   "100": "ebdb5e0b0bd2e4d6ccd6d20949e0e60b3bd7cae03f8f546c69e6358382fd23f9",
   "250": "16008e1050017b18b69865b3ab6c366c20048c7ab82e08a05e2059a8a1970695",
   "500": "bfd60c42eebae112db5165f75015a63ff885d303a9e96c42679214f6e261f326",
   "1000": "61f04806748eed1c75596648fea118711c6ee04a0a5951f9f48df8fd9346e422",
  },
  "h": {
   "1": "145c0d1312382974c9c93a7e367800ef1cce41b06b740eaa5ce6df48b2d7062d",
   "10": "85020b1b7fa738d94efad3efad21119d59fdd3db1ee3f0659471528bd951b499",
   "100": "ebdb5e0b0bd2e4d6ccd6d20949e0e60b3bd7cae03f8f546c69e6358382fd23f9",
   "250": "16008e1050017b18b69865b3ab6c366c20048c7ab82e08a05e2059a8a1970695",
   "500": "bfd60c42eebae112db5165f75015a63ff885d303a9e96c42679214f6e261f326",
   "1000": "61f04806748eed1c75596648fea118711c6ee04a0a5951f9f48df8fd9346e422",
  },
 },
}


def source_event_digest(events: list[dict]) -> str:
    data = json.dumps(events, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sampled_max_rss_mib() -> float:
    # GitHub Actions uses Linux; ru_maxrss is KiB on Linux.
    if sys.platform != "linux":
        raise RuntimeError("A1.2 resource measurement requires Linux")
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def check_budget(start: float) -> None:
    if time.perf_counter() - start > CAP_SECONDS:
        raise TimeoutError("A1.2 global wall cap exceeded: INCOMPLETE")
    if sampled_max_rss_mib() > CAP_RSS_MIB:
        raise MemoryError("A1.2 global RSS cap exceeded: INCOMPLETE")


def run_branch(seed: int, label: str, frozen: dict, start: float) -> dict:
    if seed not in SEEDS or label not in BRANCHES:
        raise ValueError("unregistered seed/teacher branch")
    if seed == 544 and seed not in frozen["positive_seeds"]:
        raise ValueError("R2 positive seed role mismatch")
    if seed == 545 and seed not in frozen["negative_seeds"]:
        raise ValueError("R2 negative seed role mismatch")
    h0 = h0_branches(seed)
    for role, snapshot in h0.items():
        observed = canonical_digest(snapshot)
        if observed != frozen["h0_evidence"][str(seed)][role + "_digest"]:
            raise ValueError("R2 original h0 snapshot digest mismatch")
    originals = {i for i, (b, h) in enumerate(zip(
        h0["b"]["arrays"]["slow_trace"], h0["h"]["arrays"]["slow_trace"]
    )) if b != h}
    if bool(originals) != (seed == 544):
        raise ValueError("frozen original positive/negative trace qualification changed")
    state = clone_state(h0[label], profile(RATE))
    experiment = IOExperiment(state, experiment=_load_protocol())
    rule = LocalWriteRule("unit_add", originals)
    observer = ReadOnlyReaderProvenance(state, event_limit=CAP_EVENTS)
    checks = {}
    with rule.attach(), observer.attach():
        for generation in range(1, HORIZON + 1):
            experiment._advance(())  # Real native step generates and selects pairs.
            if generation in HORIZONS[1:]:
                checks[str(generation)] = canonical_digest(state.to_snapshot())
                if checks[str(generation)] != GOLDEN[seed][label][str(generation)]:
                    raise ValueError("INVALID_PARITY: original R2 checkpoint mismatch")
            if generation % 25 == 0:
                check_budget(start)
    result = {
        "seed": seed, "label": label, "role": ROLES[seed],
        "h0_sha256": frozen["h0_evidence"][str(seed)][label + "_digest"],
        "checkpoint_digests": checks,
        "reader_events": len(observer.events),
        "read_events_sha256": source_event_digest(observer.events),
        "free_events": len(observer.free_events),
        "free_events_sha256": source_event_digest(observer.free_events),
        "events": observer.events,
    }
    check_budget(start)
    return result


def single_pass(frozen: dict, start: float) -> dict:
    study = {}
    for seed in SEEDS:
        b = run_branch(seed, "b", frozen, start)
        h = run_branch(seed, "h", frozen, start)
        paired = compare_branches(b["events"], h["events"], example_limit=12)
        if seed == 545:
            if b["read_events_sha256"] != h["read_events_sha256"]:
                raise ValueError("INVALID_NEGATIVE: sentinel read events diverged")
            if paired["counts"].get("matched_trace_different", 0):
                raise ValueError("INVALID_NEGATIVE: sentinel trace difference")
        study[str(seed)] = {
            "role": ROLES[seed], "original_case_zip_sha256": R2_ORIGINAL_ZIP_SHAS[seed],
            "b": {k: v for k, v in b.items() if k != "events"},
            "h": {k: v for k, v in h.items() if k != "events"},
            "comparison": paired,
        }
        check_budget(start)
    return study


def report(*, source_sha: str) -> dict:
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("A1.2 exact source SHA is required")
    frozen = load_frozen()
    if frozen["digest"] != R2_FROZEN_DIGEST:
        raise ValueError("frozen R2 digest mismatch")
    started = time.perf_counter()
    original = single_pass(frozen, started)
    repeat = single_pass(frozen, started)
    if original != repeat:
        raise ValueError("INVALID_REPLAY: exact native instrumented repeat mismatch")
    result = {
        "schema": "UG_A1_EXPOSED_READER_PILOT_V1", "issue": ISSUE,
        "protocol": {
            "source_sha": source_sha, "r2_original_source_sha": R2_ORIGINAL_SOURCE,
            "r2_manifest_digest": R2_FROZEN_DIGEST,
            "r2_original_run_id": 37950076024,
            "seed_roles": {"544": "positive_exposed", "545": "negative_exposed"},
            "input_labels": {"b": 66, "h": 8},
            "candidate": "research_only_unit_add", "rate": RATE,
            "horizon": HORIZON, "checkpoints": list(HORIZONS[1:]),
            "max_event_records_per_branch": CAP_EVENTS,
            "wall_limit_seconds": CAP_SECONDS, "rss_cap_mib": CAP_RSS_MIB,
            "no_new_seed": True, "learning_claim": False,
        },
        "environment": {
            "implementation": sys.implementation.name,
            "python": platform.python_version(), "platform": platform.platform(),
            "cpu_arch": platform.machine(),
            "max_rss_mib": sampled_max_rss_mib(),
            "wall_seconds": round(time.perf_counter() - started, 3),
        },
        "status": "VALIDATED_RETROSPECTIVE_EXPLORATORY_ONLY",
        "studies": original,
        "original_case_sha_parity": True, "instrumented_deterministic_repeat": True,
        "source_native_physical_contact_only": True,
        "independent_confirmation": False, "learning_claim": False,
    }
    check_budget(started)
    result["digest"] = _digest(result)
    raw = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > CAP_REPORT_BYTES:
        raise ValueError("INCOMPLETE: retained report size cap exceeded")
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = report(source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "digest": result["digest"],
        "environment": result["environment"],
        "studies": {seed: value["comparison"]["counts"] for seed, value in result["studies"].items()},
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
