"""PERF230 P5.0: isolate authentic D15 physics selection vs observer/receipt costs.

TEST-ONLY already-exposed benchmark SEED 0, one original full default1024
native128 selected step; never run original reserved D16 seed16384 science.
Profiler CPU wall is instrumented; don't claim its wall as uninstrumented speed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from tempfile import TemporaryDirectory
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from benchmarks.perf_residual_219 import profile_native_default_slot
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d16_complete_round_checkpoint_217 import (
    check_round, read_completed, write_completed_atomic,
)
from research.d8_genome_diversity_190 import digest
from research.d16_twojob_run_control_217 import hash_of

ORIGINAL_BENCHMARK_SEED=0
FROZEN_SELECTED128_FIRST="725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"


def source() -> str:
    v=subprocess.check_output(["git","rev-parse","HEAD"],text=True,timeout=10).strip()
    if len(v)!=40 or any(x not in "0123456789abcdef" for x in v):
        raise AssertionError("exact source SHA required")
    return v


def run(output: Path) -> dict[str,Any]:
    sha=source()
    protocol=ExperimentConfig()
    physics=PhysicsConfig()
    wall_start=time.perf_counter()
    with TemporaryDirectory(prefix="perf230-p50-cost-") as temp:
        folder=Path(temp)
        t0=time.perf_counter()
        native=execute_selected_round(
            folder/"journal",
            source_commit=sha, base_seed=ORIGINAL_BENCHMARK_SEED,
            experiment=protocol,base_config=physics,
            workers=4,evaluation_batch_size=16,memory_mib=1536,
        )
        t1=time.perf_counter()
        observer=observe_committed_round(folder/"journal",source_commit=sha)
        t2=time.perf_counter()
        complete=native["final_snapshot"]
        check_round(source_sha=sha,seed=ORIGINAL_BENCHMARK_SEED,ordinal=1,
                    predecessor=None,selected=complete,
                    observer=observer,result=native,
                    experiment=protocol,physics=physics)
        complete={
            "kind":"D16_ORIGINAL_COMPLETED_SELECTED128_ROUND_CHECKPOINT_V1",
            "source_sha":sha,"seed":ORIGINAL_BENCHMARK_SEED,"ordinal":1,
            "selected_snapshot":complete,
            "selected_v7_sha256":native["final_digest"],
            "d15_verified_observer":observer,
            "d15_journal_bytes":native["journal_bytes"],
            "rss_sampled_bytes":native.get("peak_aggregate_rss_bytes",native.get("peak_rss_bytes")),
            "global_wall_ms":int((time.perf_counter()-wall_start)*1000),
            "learning_claim":False,
        }
        t3=time.perf_counter()
        path=write_completed_atomic(folder/"complete",complete)
        t4=time.perf_counter()
        restored=read_completed(path,source_sha=sha,seed=0,ordinal=1)
        t5=time.perf_counter()
        if (native["final_digest"]!=FROZEN_SELECTED128_FIRST
                or restored["selected_v7_sha256"]!=FROZEN_SELECTED128_FIRST
                or native["new_evaluations"]!=128
                or native["checkpoint_writes"]!=8
                or observer["evaluated_native_worlds"]!=128
                or observer["d15_journal_chain_verified"] is not True
                or native["journal_bytes"]>128*1024*1024
                or native.get("peak_aggregate_rss_bytes",2**64)>1536*1024*1024):
            raise AssertionError("original source selected128 semantics/resource drift")
        d15_wall=t1-t0
        observe_wall=t2-t1
        verify_wall=t3-t2
        output_wall=t4-t3
        readback_wall=t5-t4
        verified_total=t5-t0
        costs={
            "original_D15_native128_once_selection_wall_seconds":d15_wall,
            "original_D16_authentic_readonly_observer_wall_seconds":observe_wall,
            "source_bound_final_validation_wall_seconds":verify_wall,
            "immutable_completed_v7_checkpoint_write_wall_seconds":output_wall,
            "immutable_completed_v7_checksum_readback_wall_seconds":readback_wall,
            "whole_original_selected_round_plus_verification_wall_seconds":verified_total,
            "observer_verify_write_read_fraction":(
                observe_wall+verify_wall+output_wall+readback_wall
            )/verified_total,
            "snapshot_checkpoint_file_bytes":path.stat().st_size,
            "original_journal_bytes":native["journal_bytes"],
            "sampled_aggregate_rss_bytes":native["peak_aggregate_rss_bytes"],
            "native_selected_once":True,
            "original_world_evaluations":128,
        }

    profiled=profile_native_default_slot()  # distinct native slot0 profiler, not full128
    result={
        "kind":"PERF230_P50_900S_HOTSPOT_COST_ISOLATION_TEST_ONLY",
        "source_sha":sha,"benchmark_seed":ORIGINAL_BENCHMARK_SEED,
        "original_default1024":True,"workers":4,
        "python":platform.python_version(),"host":platform.platform(),
        "native128_frozen_selected_v7":FROZEN_SELECTED128_FIRST,
        "costs":costs,
        "native_one_slot_uninstrumented_seconds":profiled["uninstrumented_wall_s"],
        "native_one_slot_cprofile_instrumented_seconds":profiled["cprofile"]["wall_s"],
        "native_one_slot_cprofile_top_self":profiled["cprofile"]["top_self"][:22],
        "native_one_slot_cprofile_top_cumulative":profiled["cprofile"]["top_cumulative"][:18],
        "native_one_slot_frozen_v7":profiled["whole_optimizer_state_sha256"],
        "real_science_seed16384_executed":False,"learning_claim":False,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "kind":result["kind"],"source_sha":sha,"costs":costs,
        "top_self":profiled["cprofile"]["top_self"][:15],
        "top_cumulative":profiled["cprofile"]["top_cumulative"][:10],
        "science_executed":False,
    },sort_keys=True),flush=True)
    return result


def main() -> None:
    p=argparse.ArgumentParser(description="One pre-exposed source-native seed0 profile")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    run(args.output)


if __name__=="__main__":
    main()
