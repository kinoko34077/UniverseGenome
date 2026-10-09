"""D15 #213 frozen native 128 selected-round memory/CPU/disk cost witness.

No genetics/physics modification or independent learning claim. The comparison
is eight+ complete *initial-sized* full snapshots, not an observed alternative
writer nor a workload-independent savings theorem.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from research.d15_selected_resume_213 import (
    FROZEN_PRE_D14_SELECTED_SHA, execute_selected_round,
)
from research.d15_sparse_recovery_213 import ResourceBudget


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--memory-mib",type=int,default=1536)
    p.add_argument("--batch",type=int,default=16)
    args=p.parse_args()
    actual_source=subprocess.check_output(
        ["git","rev-parse","HEAD"],text=True,timeout=10,
    ).strip()
    experiment=ExperimentConfig(evaluation_timeout_generations=2)
    with TemporaryDirectory(prefix="d15-selected128-resource-") as root_str:
        root=Path(root_str)/"selected-round0"
        cpu_start=time.process_time()
        result=execute_selected_round(
            root, source_commit=actual_source, base_seed=0,
            experiment=experiment, memory_mib=args.memory_mib,
            evaluation_batch_size=args.batch,
        )
        cpu_seconds=time.process_time()-cpu_start
        original_full_bytes=(root/"base.json").stat().st_size
        # Counterfactual repeated size only, not actual alternate writes:
        # base + each intermediate complete128 copy + final complete128 copy.
        repeated_full_bytes=original_full_bytes*(result["checkpoint_writes"]+2)
        report={
            "issue":213, "selected_native_128":True,
            "source_commit":actual_source, "seed":0,
            "experiment_timeout_generations":2,
            "requested_memory_mib":args.memory_mib,
            "evaluation_batch_size":args.batch,
            "evaluated_worlds":result["new_evaluations"],
            "completed_optimizer_generation":result["final_snapshot"]["generation"],
            "actual_checkpoint_patches":result["checkpoint_writes"],
            "actual_journal_bytes":result["journal_bytes"],
            "observed_initial_full_snapshot_bytes":original_full_bytes,
            "counterfactual_initial_sized_full_every_save_bytes":repeated_full_bytes,
            "ratio_to_initial_sized_counterfactual":result["journal_bytes"]/repeated_full_bytes,
            "observed_peak_parent_rss_bytes":result["peak_rss_bytes"],
            "observed_cpu_seconds":cpu_seconds,
            "observed_wall_seconds":result["elapsed_wall_seconds"],
            "exact_pre_D14_state_sha256":result["final_digest"],
            "learning_claim":False,
            "limits":"single selected128 initial round, normal density, no high-growth or hard-RSS/parallel guarantee",
        }
        assert result["final_digest"]==FROZEN_PRE_D14_SELECTED_SHA, "source-frozen state regression"
        assert result["new_evaluations"]==128 and result["final_committed"]
        assert result["checkpoint_writes"]==8, "unexpected adaptive checkpoint count"
        assert result["peak_rss_bytes"]<=(args.memory_mib*1024*1024), "memory budget regression"
        assert result["journal_bytes"]<repeated_full_bytes, "incremental witness too large"
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                               encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
