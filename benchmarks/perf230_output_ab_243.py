"""PERF230 P4.3 strict test-only original selected128 same-host ABBA.
The accepted D16 study seed16384 is NEVER used by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

BASE_SHA = "5b91d6b3ee855f8aee5655efd387336455ba4688"
GOLDEN = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
)
MEMORY = 1536 * 1024 * 1024
MAX_JOURNAL = 128 * 1024 * 1024
MAX_RETAINED = 512 * 1024 * 1024
WALL = 900.0
MIN_RATIO = 1.05
MAX_REVERSED_PAIR = 1.03  # candidate may not be >3% slower in either ABBA pair


def put(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    os.replace(tmp, path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native(output: Path, label: str) -> None:
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(source) != 40:
        raise ValueError("source commit must be pinned")
    report = dict(label=label, source_sha=source, seed=0, workers=4,
                  mode="original native128 default1024 selected",
                  experiment=ExperimentConfig().to_dict(),
                  physics=PhysicsConfig().to_dict(),
                  rounds=[], complete=False, d16_science=False)
    put(output, report)
    started = time.monotonic()
    total_journal = 0
    previous = None
    with TemporaryDirectory(prefix="perf230-p43-original-") as td:
        for index in range(2):
            begin = time.monotonic()
            root = Path(td) / f"round-{index}"
            result = execute_selected_round(
                root, source_commit=source, base_seed=0,
                experiment=ExperimentConfig(), base_config=PhysicsConfig(),
                base_snapshot=previous, evaluation_batch_size=16,
                memory_mib=1536, workers=4,
            )
            wall = time.monotonic() - begin
            snapshot = result["final_snapshot"]
            opt = SteadyStateOptimizer.from_snapshot(snapshot)
            counts: dict[str, int] = {}
            for slot in opt.slots:
                counts[slot.category] = counts.get(slot.category, 0) + 1
            if sorted(counts.values()) != [32] * 4:
                raise AssertionError("original category4x32 changed")
            if (opt.to_snapshot() != snapshot
                    or opt.generation != index + 1
                    or result["final_digest"] != GOLDEN[index]
                    or result["final_digest"] != digest(snapshot)
                    or result["new_evaluations"] != 128
                    or result["resumed_from"] != 0
                    or result["checkpoint_writes"] != 8
                    or not result["final_committed"]
                    or not result["finalization_performed"]):
                raise AssertionError("original native selected128 parity/golden failed")
            if (result.get("peak_aggregate_rss_bytes") is None
                    or result["peak_aggregate_rss_bytes"] > MEMORY):
                raise AssertionError("aggregate RSS budget exceeded")
            journal_bytes = result["journal_bytes"]
            total_journal += journal_bytes
            if journal_bytes > MAX_JOURNAL or total_journal > MAX_RETAINED:
                raise AssertionError("native journal budget exceeded")
            # Strict bytewise comparison of base, ordered patches and final;
            # the provenance manifest necessarily differs across source SHAs.
            journal = {f.name: sha(f) for f in sorted(root.glob("*.json"))
                       if f.name != "manifest.json"}
            if sorted(journal) != (["base.json"] +
                    [f"batch-{i:05d}.json" for i in range(8)] +
                    ["final.json"]):
                # Compare as a set: the filename list's lexical order is not
                # our source-native patch execution order.
                expected = {"base.json", "final.json"} | {
                    f"batch-{i:05d}.json" for i in range(8)}
                if set(journal) != expected:
                    raise AssertionError("journal patch membership differs")
            row = dict(ordinal=index + 1, wall_s=wall,
                       digest=result["final_digest"],
                       journal_bytes=journal_bytes,
                       journal_file_sha256=journal,
                       sampled_rss=result["peak_aggregate_rss_bytes"],
                       patches=result["checkpoint_writes"])
            report["rounds"].append(row)
            report["elapsed_s"] = time.monotonic() - started
            put(output, report)
            print(json.dumps(dict(label=label, round=row), sort_keys=True), flush=True)
            previous = snapshot
    report["complete"] = len(report["rounds"]) == 2
    report["total_s"] = time.monotonic() - started
    put(output, report)


def compare(outdir: Path, expected_candidate: str) -> dict:
    data = {
        tag: json.loads((outdir / f"{tag}.json").read_text())
        for tag in ("A1", "B1", "B2", "A2")
    }
    for tag, record in data.items():
        if (not record["complete"] or len(record["rounds"]) != 2
                or record["seed"] != 0
                or record["source_sha"] != (BASE_SHA if tag[0] == "A"
                                            else expected_candidate)):
            raise AssertionError("case source/completion mismatch")
    for k in range(2):
        rows = [data[tag]["rounds"][k] for tag in ("A1", "B1", "B2", "A2")]
        if len({x["digest"] for x in rows}) != 1:
            raise AssertionError("full native selected v7 drift")
        if len({x["journal_bytes"] for x in rows}) != 1:
            raise AssertionError("journal byte count drift")
        if any(x["journal_file_sha256"] != rows[0]["journal_file_sha256"]
               for x in rows[1:]):
            raise AssertionError("ordered journal payload SHA drift")
    # Entire work includes both original rounds, parent journal and selection.
    a1, a2, b1, b2 = (data[k]["total_s"] for k in ("A1", "A2", "B1", "B2"))
    speed = (a1 + a2) / (b1 + b2)
    pairs = (a1 / b1, a2 / b2)
    report = dict(base_sha=BASE_SHA, candidate_sha=expected_candidate,
                  old_total_two_samples_s=a1 + a2,
                  new_total_two_samples_s=b1 + b2,
                  speed_ratio=speed, pair_speed_ratios=pairs,
                  source_identical_v7_and_journals=True,
                  accepted_performance=(speed >= MIN_RATIO and
                                        min(pairs) >= 1 / MAX_REVERSED_PAIR),
                  D16_seed16384_run=False)
    put(outdir / "verdict.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--label", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--abba", action="store_true")
    args = parser.parse_args()
    if args.native:
        if not args.output or not args.label:
            raise ValueError("--native needs --label and --output")
        native(args.output, args.label)
        return
    if not args.abba:
        raise ValueError("use --abba or --native")
    workspace = Path.cwd()
    reports = workspace / "reports" / "perf230-p43"
    reports.mkdir(parents=True, exist_ok=True)
    candidate = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if candidate == BASE_SHA:
        raise ValueError("test head must differ from baseline")
    started = time.monotonic()
    with TemporaryDirectory(prefix="perf230-p43-baseline-") as td:
        baseline = Path(td) / "source"
        subprocess.run(["git", "fetch", "--no-tags", "--depth=1", "origin", BASE_SHA],
                       check=True, timeout=120)
        subprocess.run(["git", "worktree", "add", "--detach", str(baseline), BASE_SHA],
                       check=True, timeout=60)
        try:
            shutil.copy2(workspace / "benchmarks" / "perf230_output_ab_243.py",
                         baseline / "benchmarks" / "perf230_output_ab_243.py")
            shutil.copy2(workspace / "tests" / "test_perf230_output_observation_243.py",
                         baseline / "tests" / "test_perf230_output_observation_243.py")
            check = [sys.executable, "-m", "unittest", "discover", "-s", "tests",
                     "-p", "test_perf230_output_observation_243.py"]
            old = subprocess.run(check, cwd=baseline, capture_output=True,
                                 text=True, timeout=60)
            (reports / "expected-red.txt").write_text(old.stdout + old.stderr)
            if old.returncode == 0 or "AssertionError: 40 != 10" not in old.stderr:
                raise AssertionError("baseline expected specific RED early-stop test")
            subprocess.run(check, cwd=workspace, check=True, timeout=60)
            for tag in ("A1", "B1", "B2", "A2"):
                folder = baseline if tag[0] == "A" else workspace
                remaining = WALL - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("A/B all-case 900-second cap reached")
                subprocess.run(
                    [sys.executable, "-m", "benchmarks.perf230_output_ab_243",
                     "--native", "--label", tag,
                     "--output", str(reports / f"{tag}.json")],
                    cwd=folder, check=True, timeout=remaining,
                )
            verdict = compare(reports, candidate)
            print(json.dumps(verdict, sort_keys=True), flush=True)
            if not verdict["accepted_performance"]:
                raise AssertionError("predeclared >=1.05 full selected wall gain absent")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(baseline)],
                           check=False, timeout=60)


if __name__ == "__main__":
    main()
