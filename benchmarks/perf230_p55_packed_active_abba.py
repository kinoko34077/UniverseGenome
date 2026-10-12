"""P5.5 test-only predeclared same-host original slot0 ABBA then gated native128 A/B.

Only exposed seed0; never original reserved D16 seed16384. Uninstrumented
wall measured inside original _evaluate_slot, not interpreter startup.
An initial low-gain candidate stops before four full native128 evaluations.
"""
from __future__ import annotations
import json
from pathlib import Path
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory

BASE_SHA="6e03659bd31f9b8851228635f2ea0d912f7af974"
SLOT_GOLD="e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
SELECTED_GOLD="725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"
MIN_SLOT_GAIN=1.08
MIN_SELECTED_GAIN=1.05

EXACT_NATIVE_SLOT_CODE=r"""
import time,json
from search.evolution import SteadyStateOptimizer
from research.d8_genome_diversity_190 import digest
o=SteadyStateOptimizer.from_defaults(base_seed=0)
s=time.perf_counter()
o._evaluate_slot(o.slots[0])
w=time.perf_counter()-s
print(json.dumps(dict(wall=w,full_v7=digest(o.to_snapshot()),seed=0,science=False)))
"""


def command(cwd:Path, *args:str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,check=True,timeout=400)


def main() -> None:
    cwd=Path.cwd()
    current=command(cwd,"git","rev-parse","HEAD").stdout.strip()
    if current==BASE_SHA:
        raise AssertionError("source candidate identical to accepted baseline")
    result={
        "kind":"PERF230_P55_PACKED_NATIVE_ACTIVE_SCAN_ABBA_TEST_ONLY",
        "source_main_baseline":BASE_SHA,"source_candidate":current,
        "seed":0,"reserved_seed16384_executed":False,
        "original_physics_genetics_selection_unchanged":True,
        "slot0_samples":[],
        "status":"INCOMPLETE",
        "learning_claim":False,
    }
    out=cwd/"reports"/"p55"
    out.mkdir(parents=True,exist_ok=True)
    dest=out/"comparison.json"
    def save():
        dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    save()
    with TemporaryDirectory(prefix="perf230-p55-samehost-") as root:
        base=Path(root)/"baseline"
        command(cwd,"git","worktree","add","--detach",str(base),BASE_SHA)
        try:
            measurements={}
            for label,repo in (("A1",base),("B1",cwd),("B2",cwd),("A2",base)):
                proc=command(repo,sys.executable,"-c",EXACT_NATIVE_SLOT_CODE)
                sample=json.loads(proc.stdout.strip().splitlines()[-1])
                if sample["full_v7"]!=SLOT_GOLD or sample["seed"]!=0:
                    raise AssertionError("original seeded full optimizer v7 mismatch")
                measurements[label]=sample
                result["slot0_samples"].append({"label":label,"wall":sample["wall"],
                                                "whole_optimizer_v7":sample["full_v7"]})
                save()
                print(json.dumps(result["slot0_samples"][-1]),flush=True)
            old=(measurements["A1"]["wall"],measurements["A2"]["wall"])
            new=(measurements["B1"]["wall"],measurements["B2"]["wall"])
            ratios=[old[0]/new[0],old[1]/new[1]]
            ratio=statistics.median(old)/statistics.median(new)
            result.update(slot0_ratio=ratio,matched_pair_ratios=ratios)
            if ratio<MIN_SLOT_GAIN or min(ratios)<0.97:
                result["status"]="REJECT_MICRO_BELOW_8PCT_OR_UNSTABLE"
                save()
                print(json.dumps({"status":result["status"],"ratio":ratio,
                                  "full128_executed":False}),flush=True)
                return
            # A micro hotspot must prove its end-to-end native selected
            # relevance before source changes may be considered for merge.
            for label,repo in (("A",base),("B",cwd)):
                report_path=out/f"native-{label}.json"
                proc=command(repo,sys.executable,"-m",
                             "benchmarks.perf230_full128_no_bh_ab",
                             "--output",str(report_path))
                report=json.loads(report_path.read_bytes())
                if (report["original_native_full_optimizer_digest"]!=SELECTED_GOLD
                    or report["evaluated_worlds"]!=128
                    or report["checkpoint_writes"]!=8
                    or report["sampled_aggregate_peak_rss_bytes"]>1536*1024*1024
                    or report["source_sha"]!=(BASE_SHA if label=="A" else current)):
                    raise AssertionError("source-selected full128/writer/resource mismatch")
                result[f"native_{label}"]=report
                save()
                print(json.dumps({"label":label,"wall":report["wall_seconds"]}),flush=True)
            a=result["native_A"]
            b=result["native_B"]
            if a["journal_bytes"]!=b["journal_bytes"]:
                raise AssertionError("original full128 D15 journal size changed")
            selected_ratio=a["wall_seconds"]/b["wall_seconds"]
            result["full_selected128_ratio"]=selected_ratio
            result["status"]=(
                "CANDIDATE_NATIVE128_GAIN_PASSED_NEEDS_MATURE_VALIDATION"
                if selected_ratio>=MIN_SELECTED_GAIN else
                "REJECT_FULL_SELECTED128_BELOW_5PCT"
            )
            save()
            print(json.dumps({"status":result["status"],
                              "selected_ratio":selected_ratio}),flush=True)
        finally:
            subprocess.run(["git","worktree","remove","--force",str(base)],
                           cwd=cwd,check=False,timeout=15)


if __name__=="__main__":
    main()
