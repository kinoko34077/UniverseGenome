"""D15 #213 source-frozen sparse journal disk/CPU witness, no selected round."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d8_genome_diversity_190 import digest
from research.d15_sparse_recovery_213 import ResourceBudget, SparseEvaluationJournal
from search.evolution import SteadyStateOptimizer


def _canonical_size(obj:object)->int:
    return len(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))


def run_fixture(initial_density:int)->dict[str,object]:
    base_config=PhysicsConfig(initial_density=initial_density)
    experiment=ExperimentConfig(evaluation_timeout_generations=2)
    population=SteadyStateOptimizer.from_defaults(
        base_seed=0,base_config=base_config,experiment=experiment)
    base=population.to_snapshot()
    full_bytes=[_canonical_size(base)]
    eval_seconds=0.0
    patch_seconds=0.0
    with TemporaryDirectory() as directory:
        path=Path(directory)/"world-round"
        journal=SparseEvaluationJournal.create(
            path,base_snapshot=base,source_commit="d15-main-71656fad",
            max_bytes=128*1024*1024)
        for first in (0,16):
            batch=[]
            start=time.perf_counter()
            for slot in population.slots[first:first+16]:
                population._evaluate_slot(slot)
                batch.append(slot.to_dict())
            eval_seconds+=time.perf_counter()-start
            full_bytes.append(_canonical_size(population.to_snapshot()))
            start=time.perf_counter()
            journal.commit(batch)
            patch_seconds+=time.perf_counter()-start
        recovered=SparseEvaluationJournal.open(
            path,source_commit="d15-main-71656fad").recover()
        original=population.to_snapshot()
        assert recovered.next_index==32 and not recovered.evaluation_complete
        assert recovered.final_snapshot is None and not recovered.final_committed
        assert digest(recovered.snapshot)==digest(original),"journal state parity failed"
        disk_bytes=sum(x.stat().st_size for x in path.iterdir() if x.is_file())
        full_every_batch_bytes=sum(full_bytes)
        assert disk_bytes < full_every_batch_bytes,"sparse journal did not reduce checkpoint bytes"
        assert disk_bytes < 128*1024*1024
        return {
            "fixture_initial_density":initial_density,
            "native_full_population":128,
            "actual_evaluated_worlds":32,
            "complete_sparse_batches":2,
            "batch_size":16,
            "actual_physical_evaluation_seconds":round(eval_seconds,5),
            "incremental_commit_seconds":round(patch_seconds,5),
            "sparse_journal_bytes":disk_bytes,
            "naive_full_each_batch_bytes":full_every_batch_bytes,
            "disk_fraction":round(disk_bytes/full_every_batch_bytes,5),
            "actual_rss_bytes":ResourceBudget.current_rss_bytes(),
            "full_state_digest_after_32":digest(original),
            "recovered_state_digest":digest(recovered.snapshot),
            "genetic_selection_performed":False,
            "learning_claim":False,
        }


def main()->None:
    records=[run_fixture(initial_density=d) for d in (0,32)]
    report={"issue":213,"kind":"real_32_of_128_sparse_journal_cost",
            "accepted_source":"71656fadf7f5b78466b6e2b1f576b5ae0fe7bbfa",
            "records":records,"independent_heldout":False,
            "selected_round_recovery":False}
    Path("d15-checkpoint-cost-213.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
