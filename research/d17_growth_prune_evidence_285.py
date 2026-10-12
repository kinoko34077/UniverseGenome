"""D17 #285: verify ALREADY COMPLETED original D16 evidence, without evolution.

Input is the one immutable original seed16384 37-selected-round ZIP. This
program never imports/calls any evaluator or dispatcher; never consumes a seed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median
import zipfile

from research.d16_complete_round_checkpoint_217 import KIND
from research.d16_complete_prefix_recovery_217 import SCHEMA as RECEIPT_SCHEMA
from research.d16_original_twojob_science_217 import original_observation, REPORT_SCHEMA
from research.d16_twojob_run_control_217 import D16BoundaryError, hash_of
from research.d8_genome_diversity_190 import digest

ORIGINAL_SOURCE = "e7f2efd0c9ec49afc53b9265ec4b17e936798160"
ORIGINAL_ZIP_SHA256 = "7e6fba85bb1b2964866ee474443534ede1da0ec7b26277f60733ed3d9ccc15e3"
ORIGINAL_SEED = 16384
ORIGINAL_ROUNDS = 37
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_SELECTED_FILE_BYTES = 32 * 1024 * 1024
CATEGORIES = ("masked_and", "masked_copy", "masked_xor", "rotate_copy")


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise D16BoundaryError(reason)


def category_candidate_counts(category: dict) -> dict:
    """Native prune includes all absolute failures, so extra is growth-only."""
    indices = category["native_eligible_prune_indices"]
    absolute = category["absolute_failure_count"]
    complete = category["complete_nonfailure_count"]
    need(isinstance(indices, list) and len(indices) == len(set(indices))
         and all(type(x) is int for x in indices),
         "invalid original native prune indices")
    need(type(absolute) is int and type(complete) is int
         and 0 <= absolute <= len(indices) <= 32
         and 0 <= complete <= 32 - absolute,
         "native absolute-failure/prune-count inconsistency")
    return {
        "absolute_failure_count": absolute,
        "native_pruned_count": len(indices),
        "growth_only_candidate_count": len(indices) - absolute,
        "complete_nonfailure_count": complete,
        "native_replacement_count": category["native_replacement_count"],
    }


def growth_thresholds(selected_snapshot: dict, category: str) -> dict:
    """Selected-state witness; used only when native source retired failures."""
    complete = [
        slot for slot in selected_snapshot["slots"]
        if slot["category"] == category and not slot["absolute_failure"]
        and len(slot["growth_windows"]) == 4
    ]
    vectors = [
        tuple(int(value).bit_count() for value in slot["growth_windows"])
        for slot in complete
    ]
    medians = (
        tuple(median(v[i] for v in vectors) for i in range(4))
        if vectors else ()
    )
    thresholds = tuple(int(x) >> 1 for x in medians)
    underperformers = sum(
        all(x < t for x, t in zip(vector, thresholds))
        for vector in vectors
    )
    return {
        "complete_nonfailure_selected_count": len(vectors),
        "selected_healthy_growth_vectors": [list(v) for v in vectors],
        "selected_healthy_slot_indices": [s["index"] for s in complete],
        "median_bitcounts": list(medians),
        "native_half_median_thresholds": list(thresholds),
        "underthreshold_selected_healthy_count": underperformers,
    }



def check_original_selection_clock(previous_receipt_ms: int,
                                   selected_ms: int, receipt_ms: int) -> None:
    """The accepted selection precedes its separately published receipt."""
    need(all(type(v) is int for v in
             (previous_receipt_ms, selected_ms, receipt_ms))
         and 0 <= previous_receipt_ms <= selected_ms <= receipt_ms <= 1800000,
         "original selected/receipt cross-host global clock drift")


def check_original_final_clock(selected_ms: int, report_ms: int,
                               receipt_ms: int) -> None:
    """Verdict follows selected proof but can precede immutable receipt."""
    need(all(type(x) is int for x in (selected_ms, report_ms, receipt_ms))
         and 0 <= selected_ms <= report_ms <= receipt_ms <= 1800000,
         "original terminal native replacement/clock accounting mismatch")


def audit_archive(path: Path) -> dict:
    path = Path(path)
    need(path.is_file() and path.stat().st_size <= MAX_ARCHIVE_BYTES,
         "missing or oversized original D16 artifact ZIP")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while piece := f.read(1024 * 1024):
            h.update(piece)
    need(h.hexdigest() == ORIGINAL_ZIP_SHA256,
         "artifact ZIP does not match frozen actual original GitHub artifact digest")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        expected = {
            "partial-report.json", "stage1-partial-report.json",
            "stage1-manifest.json", "science-verdict.json",
        } | {
            f"selected-{kind}-{ordinal:02d}.json"
            for kind in ("round", "receipt")
            for ordinal in range(1, ORIGINAL_ROUNDS + 1)
        }
        need(set(names) == expected and len(names) == len(expected),
             "original full evidence is missing/extra or not a flat complete ZIP")
        need(all(0 <= x.file_size <= MAX_SELECTED_FILE_BYTES for x in z.infolist())
             and sum(x.file_size for x in z.infolist()) <= MAX_ARCHIVE_BYTES,
             "original ZIP contents exceed retained evidence bounds")

        def load(name: str) -> dict:
            return json.loads(z.read(name))

        verdict = load("science-verdict.json")
        need(verdict.get("schema") == REPORT_SCHEMA
             and verdict.get("status") == "OBSERVED_FINAL"
             and verdict.get("science_terminal") is True
             and verdict.get("source_sha") == ORIGINAL_SOURCE
             and verdict.get("seed") == ORIGINAL_SEED
             and verdict.get("last_completed_selected_round") == ORIGINAL_ROUNDS
             and len(verdict.get("rounds", [])) == ORIGINAL_ROUNDS
             and verdict.get("learning_claim") is False,
             "original science final report provenance/terminal mismatch")
        totals = Counter()
        retirement_reasons = Counter()
        by_round = []
        prior_global_ms = 0
        last_selected_ms = 0
        last_snapshot = None
        for ordinal in range(1, ORIGINAL_ROUNDS + 1):
            filename = f"selected-round-{ordinal:02d}.json"
            raw = z.read(filename)
            envelope = json.loads(raw)
            need(envelope.get("schema") == KIND
                 and envelope.get("round") == ordinal,
                 "original completed round envelope mismatch")
            payload = envelope.get("payload")
            need(isinstance(payload, dict)
                 and hash_of(payload) == envelope.get("payload_sha256")
                 and payload.get("kind") == KIND
                 and payload.get("source_sha") == ORIGINAL_SOURCE
                 and payload.get("seed") == ORIGINAL_SEED
                 and payload.get("ordinal") == ordinal
                 and payload.get("learning_claim") is False,
                 "original completed selected payload corrupt")
            selected = payload["selected_snapshot"]
            need(selected.get("generation") == ordinal
                 and len(selected.get("slots", [])) == 128
                 and digest(selected) == payload["selected_v7_sha256"],
                 "original native optimizer-v7 selected state mismatch")
            obs = payload["d15_verified_observer"]
            need(obs.get("source_commit") == ORIGINAL_SOURCE
                 and obs.get("base_seed") == ORIGINAL_SEED
                 and obs.get("selected_optimizer_generation") == ordinal
                 and obs.get("selected_post_v7_sha256") == payload["selected_v7_sha256"]
                 and obs.get("d15_journal_chain_verified") is True
                 and obs.get("original_selected_once_proven_by_D15_final") is True,
                 "original source-bound D15 observer invalid")
            receipt = load(f"selected-receipt-{ordinal:02d}.json")
            need(receipt.get("schema") == RECEIPT_SCHEMA
                 and receipt.get("source_sha") == ORIGINAL_SOURCE
                 and receipt.get("seed") == ORIGINAL_SEED
                 and receipt.get("ordinal") == ordinal
                 and receipt.get("job") == (1 if ordinal <= 20 else 2)
                 and receipt.get("selected_file_sha256") == hashlib.sha256(raw).hexdigest()
                 and receipt.get("selected_v7_sha256") == payload["selected_v7_sha256"]
                 and receipt.get("actual_d15_observer_sha256") == hash_of(obs)
                 and receipt.get("learning_claim") is False,
                 "original immutable D15 selected receipt mismatch")
            now = receipt["global_elapsed_ms"]
            selected_ms = payload["global_wall_ms"]
            # Native completion timestamp precedes immutable-receipt fsync.
            # Final scientific verdict records the selected-state timestamp,
            # not the later receipt publication timestamp.
            check_original_selection_clock(prior_global_ms, selected_ms, now)
            prior_global_ms = now
            last_selected_ms = selected_ms
            need(verdict["rounds"][ordinal - 1] == original_observation(payload),
                 "original scientific report differs from native source-bound observer")
            need(tuple(sorted(obs["categories"])) == CATEGORIES,
                 "native original four categories mismatch")
            cats = {}
            for category in CATEGORIES:
                entry = category_candidate_counts(obs["categories"][category])
                cats[category] = entry
                totals["category_rounds"] += 1
                totals["growth_only_candidates"] += entry["growth_only_candidate_count"]
                totals["absolute_failed_candidates"] += entry["absolute_failure_count"]
                totals["actual_replacements"] += entry["native_replacement_count"]
            for retired in obs["native_retirements"]:
                retirement_reasons[retired["retirement_reason"]] += 1
            by_round.append({"round": ordinal, "categories": cats})
            last_snapshot = selected
        # The report is finalized after selected checkpoint publication but
        # before the last immutable receipt becomes authoritative. Its clock
        # may be a few milliseconds later than the D15 selected snapshot.
        check_original_final_clock(
            last_selected_ms, verdict["global_elapsed_ms"], prior_global_ms)
        need(verdict["original_native_replacements_total"] == totals["actual_replacements"]
             and totals["actual_replacements"] == sum(retirement_reasons.values()),
             "original terminal native replacement/clock accounting mismatch")
        last = by_round[-1]
        selected37 = {}
        for category in CATEGORIES:
            count = growth_thresholds(last_snapshot, category)
            need(count["complete_nonfailure_selected_count"] ==
                 last["categories"][category]["complete_nonfailure_count"],
                 "selected round37 healthy complete window diverged from native observer")
            selected37[category] = count
        return {
            "schema": "D17_ORIGINAL_READONLY_GROWTH_PRUNE_AUDIT_V1",
            "input_zip_sha256": ORIGINAL_ZIP_SHA256,
            "original_source_sha": ORIGINAL_SOURCE,
            "seed": ORIGINAL_SEED,
            "rounds": ORIGINAL_ROUNDS,
            "original_global_elapsed_ms": verdict["global_elapsed_ms"],
            "category_rounds": totals["category_rounds"],
            "absolute_failed_prune_candidates": totals["absolute_failed_candidates"],
            "growth_only_prune_candidates": totals["growth_only_candidates"],
            "native_replacements": totals["actual_replacements"],
            "retirement_reasons": dict(sorted(retirement_reasons.items())),
            "selected_round37_growth_scores": selected37,
            "learning_claim": False,
            "independent_generalization_claim": False,
            "scope": "one outcome-exposed original D16 study; postselected growth-score witness",
        }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-zip", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = audit_archive(args.original_zip)
    raw = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(raw)


if __name__ == "__main__":
    main()
