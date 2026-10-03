# Phase 5 Semantic Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the Phase 5 optimizer with Issue #56 and the accepted Phase 5 contract without reopening Phase 4 learning or starting Phase 6.

**Architecture:** Keep the optimizer category-local and deterministic. Make Phase 4 evaluation expose explicit per-run observables, normalize those observables in `Fitness`, and represent seed escalation as an unchanged genome with an expanded deterministic seed set. Track physical evaluation generations separately from optimizer iterations; remove unused universe snapshots from optimizer persistence.

**Tech Stack:** Python 3.11+, `unittest`, deterministic fixed-array physics, JSON snapshots, GitHub Actions.

**Spec:** `docs/spec/02_functional_spec.md` sections SPEC-POP-002, SPEC-FIT-001, SPEC-GROWTH-001/002, SPEC-PRUNE-001/002, SPEC-EVOL-001; Issue #56.

## Global Constraints

- Preserve four category-local groups of 32 slots and matched genome/seed positions.
- Preserve the Phase 4 learning result and keep the learning claim false.
- Use deterministic seed expansion `4 → 8 → 16 → 32`; seed is not a genome field.
- Growth history remains four 8-bit windows covering 512 physical generations.
- Absolute fitness order is exactly success, wrong outputs, timeouts, response latency, activity cost.
- Do not retain or serialize universe snapshots that are not authoritative continuation state.

## Review Focus

- A queued seed escalation must preserve category, genome, and base seed while only expanding the sample set; test this before implementing the scheduler branch.
- Equivalent event rates at different seed counts must produce equivalent fitness ordering; test normalized metrics with 4 and 8 seeds.
- Wrong events, timeout, first response latency, and physics activity must come from their named observables rather than proxy totals; test each metric at the evaluation boundary.
- Growth history must not advance before 128 accumulated evaluation generations and must cover four windows after 512; test partial and exact boundaries.
- A zero-median pruning category must not become prunable solely because all growth is zero; test the canonical threshold directly.

---

### Task 1: Make Phase 4 evaluation metrics explicit

**Files:**
- Modify: `core/physics.py` (`StepMetrics` activity metric)
- Modify: `core/experiment.py` (`EvaluationResult`, `LearningMeasurement`, `IOExperiment.evaluate_autonomous`)
- Test: `tests/test_phase4.py`

**Interfaces:**
- Produces `EvaluationResult.event_generations`, `evaluation_generations`, `timed_out`, `wrong_output_count`, `response_latency`, and `activity_cost`.
- Produces `LearningMeasurement.evaluation_generations` for optimizer cadence.

- [x] **Step 1: Write failing tests** for wrong-event counting, timeout based on missing expected events, first relevant response latency, and activity accumulation from `StepMetrics` rather than output-event count.
- [x] **Step 2: Run `python -m unittest tests.test_phase4 -v` and confirm the new assertions fail for the current proxy metrics.**
- [x] **Step 3: Implement explicit event-generation bookkeeping and a named `StepMetrics.activity_cost` metric.**
- [x] **Step 4: Run the focused Phase 4 tests and confirm they pass.**
- [x] **Step 5: Commit `fix: expose authoritative phase4 evaluation metrics`.**

### Task 2: Normalize Fitness and restore canonical absolute ordering

**Files:**
- Modify: `search/fitness.py`
- Modify: `search/evolution.py` (`_fitness_from_measurement`, measurement summary)
- Test: `tests/test_phase5.py`

**Interfaces:**
- `Fitness` stores comparable normalized rates/means; `sort_key()` returns only the five canonical absolute fields.
- `_fitness_from_measurement()` divides count metrics by `measurement.seed_count` and consumes the explicit Phase 4 observables.

- [x] **Step 1: Write failing tests** for rate invariance across seed counts, event-based wrong outputs, timeout flags, first response latency, activity cost, and retention/noise exclusion from absolute sort order.
- [x] **Step 2: Run the focused Phase 5 tests and confirm they fail.**
- [x] **Step 3: Implement normalized `Fitness` serialization/comparison and the corrected measurement mapping.**
- [x] **Step 4: Run focused Phase 5 tests and then the Phase 4/5 suites.**
- [x] **Step 5: Commit `fix: normalize phase5 fitness semantics`.**

### Task 3: Separate initial genomes, seed escalation, and mutation children

**Files:**
- Modify: `search/genome.py` (deterministic initial genome variants)
- Modify: `search/evolution.py` (`CandidateSlot`, `from_defaults`, escalation/mutation operations, scheduler)
- Test: `tests/test_phase5.py`

**Interfaces:**
- `UniverseGenome.initial_population(count=8)` returns eight deterministic distinct parameter genomes.
- `SteadyStateOptimizer.escalate_seed_evidence(parent, target_index)` preserves genome/category/base seed and expands only `seed_count`.
- `replace_free_slot()` creates a new mutation child with a fresh deterministic seed base and starts at `seed_count=4`.

- [x] **Step 1: Write failing tests** for eight distinct matched genomes, same-genome seed-set expansion, and mutation-child separation.
- [x] **Step 2: Run focused tests and confirm current default clones and queued mutation fail the assertions.**
- [x] **Step 3: Implement the deterministic initial population and separate scheduler operations.**
- [x] **Step 4: Run focused Phase 5 tests and integrated optimizer smoke tests.**
- [x] **Step 5: Commit `fix: separate phase5 seed evidence from mutation`.**

### Task 4: Tie growth windows to physical evaluation generations

**Files:**
- Modify: `search/evolution.py` (`CandidateSlot` physical clock/reference and step cadence)
- Modify: `search/pruning.py` (zero-median threshold)
- Test: `tests/test_phase5.py`

**Interfaces:**
- Candidate snapshots store `physical_generations` and the fitness reference for the current growth window.
- Growth flags are appended only when accumulated evaluation generations cross 128; at most four windows are retained.

- [x] **Step 1: Write failing tests** for no growth window before 128 generations, one at 128, four at 512, and zero-median pruning behavior.
- [x] **Step 2: Run focused tests and confirm optimizer iterations currently advance growth too early.**
- [x] **Step 3: Implement the physical cadence gate and canonical `median >> 1` threshold.**
- [x] **Step 4: Run focused Phase 5 tests, including the integrated pruning path.**
- [x] **Step 5: Commit `fix: gate phase5 growth on physical cadence`.**

### Task 5: Make optimizer persistence authoritative and update evidence

**Files:**
- Modify: `search/evolution.py` (snapshot format and headless trace)
- Modify: `tests/test_phase5.py`
- Modify: `docs/spec/02_functional_spec.md`
- Modify: `docs/spec/07_test_spec.md`
- Modify: `docs/spec/08_changelog.md`
- Modify: `core/runner.py` or related CLI evidence text if iteration expectations change

**Interfaces:**
- Snapshot format records candidate parameters, normalized fitness, growth reference/history, physical clock, and scheduler state; it does not serialize unused universe snapshots.
- Headless evidence reports separate mutation-child creation and `4 → 8 → 16 → 32` evidence progression.

- [x] **Step 1: Write failing persistence/headless assertions** for the authoritative fields, absence of unused snapshots, deterministic continuation, and the corrected four-step progression.
- [x] **Step 2: Run focused tests and confirm the old snapshot schema/evidence fails.**
- [x] **Step 3: Implement the snapshot/evidence changes and update accepted spec/test documentation.**
- [x] **Step 4: Run full unittest, compileall, headless optimizer smoke, and diff checks.**
- [x] **Step 5: Commit `fix: align phase5 persistence and evidence`.**

### Task 6: Final verification and review handoff

- [x] Run `python -m unittest discover -s tests -v` and record the exact count.
- [x] Run `python -m compileall core search persistence server tests`.
- [x] Run the bounded optimizer smoke with explicit timeout and corrected iteration count.
- [x] Inspect the diff for stale `universe_snapshot`, raw-total fitness, optimizer-iteration growth, and retention/noise absolute sorting.
- [ ] Push the dedicated branch and request an independent review against the exact head before merge.
