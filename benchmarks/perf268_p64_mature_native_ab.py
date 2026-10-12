"""PERF230 P5.6 TEST ONLY: source-frozen true maturity round10 and20 same-host A/B.

PERF268 P6.4 reuses the accepted tested P5.6 script at exact frozen source heads.
All original 128 native source-selected worlds use default1024 and exposed
seed0. Prefixes 1..9 and 11..19 generated ONCE by accepted baseline and
candidate is fed the exact same v7 predecessor. No original seed16384.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

BASE_SHA="91a1a3d712ce34bb0db591225d55f904648aae13"
CANDIDATE_SHA="118b6be0eb7a53844a20ead009c76658ed1efbfe"
KIND="PERF268_P64_ORIGINAL_NATIVE128_MATURE_SOURCE_COMPARE_TEST_ONLY"
GOLDEN_FIRST4=(
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
    "0ac1086caa69775a630165c2dab161513b240a63993e4f53a1be9b33688251f2",
    "b06e987f5dffbb114362be88bac56da7a1a00d1e1e60f18368c0fc78a3a7cc10",
)
ONE_SELECTED_ORIGINAL = r"""
import json,time,sys,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d8_genome_diversity_190 import digest
n=int(sys.argv[1]); src=Path(sys.argv[2]); dest=Path(sys.argv[3]); observe=int(sys.argv[4])
prior=None if str(src)=="NONE" else json.loads(src.read_bytes())["snapshot"]
source=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
with TemporaryDirectory(prefix="perf230-p56-source-native-") as temp:
    root=Path(temp)/"journal"
    start=time.perf_counter()
    r=execute_selected_round(root,source_commit=source,base_seed=0,
                             experiment=ExperimentConfig(),base_config=PhysicsConfig(),
                             base_snapshot=prior,memory_mib=1536,workers=4,
                             evaluation_batch_size=16)
    native_wall=time.perf_counter()-start
    observer=observe_committed_round(root,source_commit=source) if observe else None
    if (r["final_digest"]!=digest(r["final_snapshot"])
        or r["new_evaluations"]!=128 or r["resumed_from"]!=0
        or not r["final_committed"] or not r["finalization_performed"]
        or r["checkpoint_writes"]!=8 or r["journal_bytes"]>128*1024*1024
        or r.get("peak_aggregate_rss_bytes",2**64)>1536*1024*1024):
        raise AssertionError("original D15 full128 native once-selection/resource/source mismatch")
    if observer is not None and (
        observer["selected_post_v7_sha256"]!=r["final_digest"]
        or observer["evaluated_native_worlds"]!=128
        or observer["original_selected_once_proven_by_D15_final"] is not True
        or not observer["d15_journal_chain_verified"]):
        raise AssertionError("D16 authentic source observer diverged")
    report={
        "source_sha":source,"ordinal":n,"seed":0,"native_wall_seconds":native_wall,
        "selected_v7_sha256":r["final_digest"],"journal_bytes":r["journal_bytes"],
        "patches":r["checkpoint_writes"],
        "sampled_aggregate_rss_bytes":r["peak_aggregate_rss_bytes"],
        "native128_evaluations":128,"original_default1024":True,
        "snapshot":r["final_snapshot"],
        "observer_verified":observer is not None,
        "original_science_seed16384_executed":False,
    }
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="snapshot"},sort_keys=True),flush=True)
"""


def call(cwd:Path,*cmd:str,timeout:int=1200):
    return subprocess.run(cmd,cwd=cwd,text=True,check=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=timeout)


def run() -> None:
    cwd=Path.cwd()
    candidate=CANDIDATE_SHA
    if candidate==BASE_SHA or len(candidate)!=40:
        raise AssertionError("must test exact source change on candidate branch")
    dest=cwd/"reports"/"perf268-p64"
    dest.mkdir(parents=True,exist_ok=True)
    summary={
        "kind":KIND,"baseline_sha":BASE_SHA,"candidate_sha":candidate,
        "seed":0,"original_default1024":True,"native128_each_full_round":True,
        "last_baseline_prefix_selected_round":0,
        "source_parity":False,"target_900_achieved":False,
        "original_science_seed16384_executed":False,
        "learning_claim":False,"comparison":{},
        "status":"INCOMPLETE",
    }
    def save():
        (dest/"comparison.json").write_text(json.dumps(
            summary,sort_keys=True,indent=2)+"\n")
    save()
    with TemporaryDirectory(prefix="perf230-p56-hosted-") as t:
        baseline=Path(t)/"source-baseline"
        candidate_repo=Path(t)/"source-candidate"
        scratch=Path(t)/"round-records"
        scratch.mkdir()
        call(cwd,"git","worktree","add","--detach",str(baseline),BASE_SHA)
        call(cwd,"git","worktree","add","--detach",str(candidate_repo),CANDIDATE_SHA)
        last=None
        try:
            def one(repo,tag,n,predecessor,*,observe=False):
                nonlocal last
                path=scratch/f"{tag}-{n:02d}.json"
                orig="NONE" if predecessor is None else str(predecessor)
                proc=call(repo,sys.executable,"-c",ONE_SELECTED_ORIGINAL,
                          str(n),orig,str(path),"1" if observe else "0")
                v=json.loads(path.read_bytes())
                if v["ordinal"]!=n or v["source_sha"]!=(
                    BASE_SHA if repo==baseline else candidate):
                    raise AssertionError("source-bound original selected ledger mismatch")
                if n<=4 and v["selected_v7_sha256"]!=GOLDEN_FIRST4[n-1]:
                    raise AssertionError("historical native full-v7 source-oracle drift")
                print(json.dumps({"label":tag,"ordinal":n,
                                  "native_wall":v["native_wall_seconds"],
                                  "digest":v["selected_v7_sha256"]}),flush=True)
                return path,v
            def verify(a,b,n):
                if (a["selected_v7_sha256"]!=b["selected_v7_sha256"]
                    or a["journal_bytes"]!=b["journal_bytes"]
                    or not a["observer_verified"] or not b["observer_verified"]
                    or a["native128_evaluations"]!=128 or b["native128_evaluations"]!=128):
                    raise AssertionError("full original D15 native selected128 vs candidate mismatch")
                ratio=a["native_wall_seconds"]/b["native_wall_seconds"]
                summary["comparison"][str(n)]={
                    "original_baseline_wall_seconds":a["native_wall_seconds"],
                    "new_candidate_wall_seconds":b["native_wall_seconds"],
                    "ratio":ratio,"equal_native_full_selected_v7_sha256":a["selected_v7_sha256"],
                    "original_journal_bytes":a["journal_bytes"],
                }
                save()
            for n in range(1,10):
                last,v=one(baseline,"prefix",n,last)
                summary["last_baseline_prefix_selected_round"]=n
                save()
            seed9=last
            cand10,b10=one(candidate_repo,"B",10,seed9,observe=True)
            base10,a10=one(baseline,"A",10,seed9,observe=True)
            verify(a10,b10,10)
            last=base10
            for n in range(11,20):
                last,v=one(baseline,"prefix",n,last)
                summary["last_baseline_prefix_selected_round"]=n
                save()
            seed19=last
            base20,a20=one(baseline,"A",20,seed19,observe=True)
            cand20,b20=one(candidate_repo,"B",20,seed19,observe=True)
            verify(a20,b20,20)
            a_total=a10["native_wall_seconds"]+a20["native_wall_seconds"]
            b_total=b10["native_wall_seconds"]+b20["native_wall_seconds"]
            ratio=a_total/b_total
            summary["comparison_sum_ratio"]=ratio
            summary["source_parity"]=True
            summary["status"]=(
                "MATURE_ROUND10_20_CANDIDATE_PASS_PROVISIONAL"
                if ratio>=1.05
                and min(a10["native_wall_seconds"]/b10["native_wall_seconds"],
                        a20["native_wall_seconds"]/b20["native_wall_seconds"]) >= 0.97
                else "REJECT_MATURE_ROUND10_20_BELOW_PREDECLARED_GATE"
            )
            save()
            print(json.dumps({"status":summary["status"],
                              "mature_source_ratio":ratio,
                              "original_seed16384_executed":False}),flush=True)
        finally:
            subprocess.run(["git","worktree","remove","--force",str(baseline)],
                           cwd=cwd,timeout=15,check=False)
            subprocess.run(["git","worktree","remove","--force",str(candidate_repo)],
                           cwd=cwd,timeout=15,check=False)


if __name__=="__main__":
    run()
