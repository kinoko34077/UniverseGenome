# Phase 5 Authoritative Universe Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or **superpowers:executing-plans** to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Phase 5 to the original 128-authoritative-Universe architecture so persistent learning, 128/512-generation growth, allocation, pruning, and snapshot continuation all use real Universe slots.

**Architecture:** Replace the CandidateSlot-only search record with one `UniverseSlot` per occupied search slot. Each slot owns exactly one persistent `UniverseState`, one genome/category/seed, and its fitness/growth metadata; outer optimizer metadata never embeds multiple seed Universes. Phase 4 evaluation continues to clone the current slot state and discard the clone, while authoritative training advances the slot one physical generation at a time and observes exact growth boundaries.

**Tech Stack:** Python 3.11+, `unittest`, deterministic fixed-array physics, JSON snapshots, GitHub Actions.

**Spec:** `docs/spec/02_functional_spec.md`, `docs/spec/04_data_spec.md`, and UniverseGenome Issue #58 architecture invariants A1–A9.

## Global Constraints

- Maintain exactly 128 authoritative simultaneous Universe slots as four categories × 32.
- One occupied slot contains exactly one category, genome, seed, persistent UniverseState, physical generation, and fitness/growth/pruning metadata.
- Never embed multiple authoritative seed Universes inside one CandidateSlot/UniverseSlot.
- Evaluation clones are disposable and their generations never advance authoritative generation or growth.
- Growth observations occur at real generation 0/128/256/384/512 boundaries; never synthesize unobserved zero windows.
- Initial layout remains eight deterministic genomes × four real seed Universes per category.
- New seed Universes start at their own generation 0; no implicit catch-up.
- Same-genome evidence allocation consumes actual free slots; mutation allocation creates a distinct slot.
- Keep the canonical five-field fitness order and false Phase 4 learning result.
- Keep cross-category elimination and Phase 6 disabled.
- The default promising policy is explicitly named and documented; no undocumented median rule is introduced.

## Review Focus

- A repeated optimizer step must mutate the existing authoritative UniverseState, not recreate it; test state identity/generation continuity.
- An evaluation with a long disposable clone run must leave the authoritative state and generation unchanged except for the explicit training step.
- A newly allocated same-genome seed must be one fresh UniverseSlot at generation 0, not a hidden state in an existing slot.
- A training episode crossing generation 128 must observe exactly the real boundary and must not append synthetic zero windows.
- Snapshot/restore must include all 128 authoritative state arrays and produce the same next-step result as uninterrupted execution.
- Allocation and pruning must remain category-local and deterministic, including empty/free-slot and protected-leader cases.

---

### Task 1: Reconcile the accepted Phase 5 specification

**Files:**
- Modify: `docs/spec/02_functional_spec.md`
- Modify: `docs/spec/04_data_spec.md`
- Modify: `docs/spec/07_test_spec.md`
- Modify: `docs/spec/08_changelog.md`

**Interfaces:**
- Documents `UniverseSlot` as one authoritative state and seed evidence as multiple actual slots.
- Defines the exact generation-boundary growth lifecycle and excludes evaluation-clone generations.
- Records the explicit promising allocation policy as an accepted-default, isolated from fitness implementation.

- [x] **Step 1: Rewrite SPEC-EVOL-001** to describe 128 authoritative Universe slots, persistent inner state, disposable evaluation clones, real 0/128/256/384/512 observations, and slot-based seed/mutation allocation.
- [x] **Step 2: Reconcile SPEC-SNAP-001** with complete Phase 5 UniverseState arrays and metadata while excluding disposable clones.
- [x] **Step 3: Add the accepted-default promising policy**: a genome qualifies for another seed allocation only when the selected category-local policy marks it promising; the default v0.1 policy is strict improvement over the category median canonical fitness tuple, and the policy name is persisted.
- [x] **Step 4: Update Phase 5 test/changelog prose** to remove CandidateSlot-hidden-seed and evaluation-clock claims.

### Task 2: Add state-boundary training and current-state measurement APIs

**Files:**
- Modify: `core/experiment.py`
- Test: `tests/test_phase4.py`

**Interfaces:**
- Add `IOExperiment.train_a_to_b_null(..., on_generation: Callable[[int], None] | None = None) -> TrainingRecord`; invoke the callback after every authoritative training step, including teacher B/NULL steps.
- Add `measure_trained_state(state: UniverseState, *, experiment: ExperimentConfig | None = None) -> LearningMeasurement`; measure baseline from an explicit fresh baseline setup, but measure trained/counterfactual results by cloning the supplied current state.
- Preserve `compare_baseline_trained()` behavior and the false learning claim.

- [x] **Step 1: Write RED tests** proving a training callback observes every physical generation, `measure_trained_state()` does not mutate its input state, and evaluation clone generations are not included in the authoritative state generation.
- [x] **Step 2: Run `python -m unittest tests.test_phase4 -v`; confirm the new API assertions fail against the current implementation.
- [x] **Step 3: Implement callback-driven training and current-state measurement with existing `EvaluationResult` observables.**
- [x] **Step 4: Run Phase 4 tests and confirm all pass.**
- [x] **Step 5: Commit `feat: expose persistent phase4 state measurements`.**

### Task 3: Replace CandidateSlot-only records with one-state UniverseSlot records

**Files:**
- Modify: `search/evolution.py`
- Modify: `search/genome.py` if a stable genome key is needed
- Test: `tests/test_phase5.py`

**Interfaces:**
- Add `UniverseSlot` containing `index, category, genome, seed, state, fitness, growth_windows, growth_reference, parent_index, last_mutation_field, allocation_reason`.
- `UniverseSlot.seed_count` is not authoritative; same-genome evidence count is derived by grouping real occupied slots.
- `SteadyStateOptimizer.from_defaults()` creates 128 slots with real `UniverseState` instances and matched genome/seed positions.
- `SteadyStateOptimizer._evaluate_slot(slot)` advances that slot’s authoritative state through one training episode and returns current measurement plus exact-boundary measurements.
- `SteadyStateOptimizer.allocate_seed_slot(free_index, parent)` creates one new same-genome/category slot at a fresh deterministic seed and generation 0.
- `SteadyStateOptimizer.replace_free_slot(free_index, parent)` creates one mutation-child slot with a fresh state and four-seed-group membership represented by actual slots only.

- [x] **Step 1: Write RED tests** for 128 real states, no state sharing, one-state-per-slot serialization, persistent generation continuity across optimizer steps, and real same-genome slot allocation.
- [x] **Step 2: Run focused Phase 5 tests and confirm current CandidateSlot metadata/fresh reconstruction fails those architecture assertions.**
- [x] **Step 3:** Implement `UniverseSlot`, deterministic state creation, grouping-based evidence counts, and allocation operations without changing growth policy yet.
- [x] **Step 4:** Run focused tests and confirm persistent slot/state assertions pass.
- [x] **Step 5:** Commit `feat: restore authoritative phase5 universe slots`.

### Task 4: Tie growth to observed authoritative boundaries

**Files:**
- Modify: `search/evolution.py`
- Modify: `search/pruning.py` only if the real-window input contract requires a narrow change
- Test: `tests/test_phase5.py`

**Interfaces:**
- `UniverseSlot.physical_generations` reflects `slot.state.generation`.
- The start reference is measured at the slot’s current generation before the first training interval.
- Boundary callbacks measure at every exact multiple of 128 and append one `growth_flags(reference, observed)` result.
- No callback or measurement from evaluation clones changes `physical_generations`.
- Four stored windows represent four actual 128-generation intervals; long evaluation time produces no synthetic zeros.

- [x] **Step 1: Write RED tests** for generation-0 reference, exact 128/256/384/512 boundary windows, default timeout isolation, and a training run that crosses a boundary without zero fabrication.
- [x] **Step 2: Run focused tests and confirm synthetic-zero/fresh-evaluation behavior fails.**
- [x] **Step 3:** Implement boundary observation around the authoritative training callback and remove `record_candidate_evaluation()`’s disposable-generation accounting.
- [x] **Step 4:** Run the growth/pruning tests and confirm only real windows reach pruning.
- [x] **Step 5:** Commit `fix: measure phase5 growth on authoritative generations`.

### Task 5: Restore slot-based allocation, policy hook, and persistence

**Files:**
- Modify: `search/evolution.py`
- Modify: `core/runner.py`
- Modify: `tests/test_phase5.py`
- Modify: `docs/spec/02_functional_spec.md`
- Modify: `docs/spec/07_test_spec.md`
- Modify: `docs/spec/08_changelog.md`

**Interfaces:**
- Scheduler persists `promising_policy`, allocation/mutation cursors, evaluation/replacement counts, and lineage; category-local selection remains derived from the authoritative slots.
- Default policy is explicit and tested; it is not hidden in `seed_count` logic.
- Seed evidence summaries report actual per-genome slot counts; no `4→8→16→32` claim is emitted unless actual slots reach those counts.
- Integrated snapshots use a new format version and serialize each occupied `UniverseSlot.state.to_snapshot()`; disposable clones are absent.
- `SteadyStateOptimizer.from_snapshot()` restores all 128 authoritative states and deterministic continuation.

- [x] **Step 1: Write RED tests** for explicit promising policy, category-local actual slot allocation, mutation-child distinction, snapshot fields, no disposable clone serialization, and restore equivalence.
- [x] **Step 2: Run focused tests and confirm old scheduler/snapshot/headless evidence fails.**
- [x] **Step 3:** Implement the policy hook, actual free-slot allocation, format migration, and headless evidence from slot groups.
- [x] **Step 4:** Run focused Phase 5 tests and an optimizer smoke with a bounded training budget.
- [x] **Step 5:** Commit `fix: persist phase5 slots and allocation policy`.

### Task 6: Final verification and review handoff

- [ ] Run `python -m unittest discover -s tests -v` and record the exact count.
- [ ] Run `python -m compileall core search persistence server tests`.
- [ ] Run the bounded optimizer smoke and verify authoritative slot generations, group counts, growth windows, and false learning claim.
- [ ] Run `git diff --check` and inspect for hidden multi-seed state, synthetic zero windows, evaluation-clock growth, and stale CandidateSlot prose.
- [ ] Push a dedicated PR, verify exact-head CI, and obtain independent exact-head review before merge.
- [ ] Merge only after checks pass; verify post-merge main CI.
- [ ] Update UniverseGenome #58 and devflow Control #314; keep Phase 6 blocked until the subsequent readiness audit.
