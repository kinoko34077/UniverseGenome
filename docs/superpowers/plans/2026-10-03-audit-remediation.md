# Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the material Phase 3–5 acceptance gaps found by UniverseGenome#27, then reconcile configuration, documentation, and devflow projections without starting Phase 6+.

**Architecture:** Keep the physics core authoritative and headless. Add a small explicit Phase 4 I/O observation boundary, a server-owned runtime controller/API for the browser observer, and a validated UniverseGenome-to-PhysicsConfig/evaluation boundary for Phase 5. Keep each boundary deterministic, bounded, and independently testable.

**Tech Stack:** Python 3.12, standard-library `unittest`, `http.server`, JSON, browser ES modules, GitHub Actions, devflow MCP/API.

**Spec:** `docs/spec/01_requirements.md`, `docs/spec/02_functional_spec.md`, `docs/spec/05_ui_spec.md`, `docs/spec/06_implementation_spec.md`, `docs/spec/07_test_spec.md`, `docs/PHASE6_HANDOFF.md`, and remediation Issues #28–#31.

## Global Constraints

- Do not implement Phase 6+ capability-ladder behavior.
- Preserve the inner-physics / outer-search separation.
- Do not introduce semantic labels, tokenizer vocabulary, backpropagation, or permanent Cell IDs.
- The browser must not own the authoritative simulation clock.
- Preserve bounded history, snapshot isolation, deterministic replay, and category-local comparison.
- Every production change begins with a failing real-behavior test and ends with the full suite.
- Normal changes use a dedicated branch, PR, exact-head Formal Review, CI, merge, and post-main verification.

## Review Focus

- A seeded output-side cell must produce a real byte/NULL event through the same collector used by evaluation; an empty result must never be hard-coded.
- Teacher output must affect training state without entering autonomous scoring.
- A GUI control must produce an observable bounded runtime state transition, not only a browser event.
- Every UniverseGenome field must either map to an effective PhysicsConfig behavior or be rejected explicitly; unmapped silent fields are not acceptable.
- Rewind, clone, snapshot, and reset must not mutate unrelated authoritative state.

### Task 1: Phase 4 real I/O observation

**Issue:** UniverseGenome#28

**Files:**
- Modify: `core/io_bus.py`, `core/experiment.py`, `core/runner.py`, `config/experiment_v0_1.json`
- Test: `tests/test_phase4.py`

**Interfaces:**
- Produces a deterministic output-organ sampler and `IOExperiment.evaluate_autonomous()` results populated from observed output edges.
- Keeps teacher events separate from autonomous events and uses an explicit `ExperimentConfig` loaded from the effective configuration.

- [ ] Write failing tests for seeded output collection, teacher exclusion, and effective protocol loading.
- [ ] Run the focused tests and verify they fail because the current evaluator returns an empty tuple and ignores the experiment file.
- [ ] Implement fixed-organ coordinate sampling, bit/VALID/NULL decoding, and edge collection through the real evaluation loop.
- [ ] Run focused tests and the full suite.
- [ ] Commit the Phase 4 repair.

### Task 2: Phase 3 runtime/API and browser surface

**Issue:** UniverseGenome#29

**Files:**
- Create: `server/runtime.py`, `tests/test_server_runtime.py`
- Modify: `server/app.py`, `ui/index.html`, `ui/controls.js`, `ui/sim_view.js`, `tests/test_phase3.py`

**Interfaces:**
- `PopulationRuntime` owns a bounded `Population`, selected slot, running state, and explicit control operations.
- HTTP JSON endpoints expose state/control/snapshot behavior; browser rendering consumes the API and does not advance the core by animation frames.

- [ ] Write failing API/runtime tests for state, step, select, clone, rewind, reset, and snapshot operations.
- [ ] Run them and verify the static server has no runtime API.
- [ ] Implement the runtime controller and bounded JSON API.
- [ ] Wire browser fetch/polling, real summaries/cells, selection, mode state, and control actions.
- [ ] Add contract assertions for the browser API surface and run the full Python suite.
- [ ] Commit the Phase 3 repair.

### Task 3: Phase 5 executable optimizer boundary

**Issue:** UniverseGenome#30

**Files:**
- Modify: `core/physics.py`, `search/genome.py`, `search/evolution.py`, `core/experiment.py`, `core/runner.py`, `tests/test_phase5.py`

**Interfaces:**
- `UniverseGenome.to_physics_config(base)` returns a validated effective physics configuration with every genome field represented by an effective runtime parameter.
- Headless optimizer diagnostics evaluate real candidates through the Phase 4 measurement function and use bounded seed escalation for replacement.

- [ ] Write failing tests for genome validation/mapping, real candidate evaluation, and 4→8→16→32 replacement escalation.
- [ ] Run focused tests and verify diagnostics-only/unmapped behavior fails.
- [ ] Implement the minimal explicit mapping and deterministic candidate evaluation/replacement.
- [ ] Run focused tests, integration runner, and full suite.
- [ ] Commit the Phase 5 repair.

### Task 4: Configuration/specification/CI reconciliation

**Issue:** UniverseGenome#31

**Files:**
- Modify: `config/default.json`, `config/experiment_v0_1.json`, `.github/workflows/ci.yml`, `core/runner.py`, `server/app.py`, `docs/SPECIFICATION.md`, `docs/ROADMAP.md`, `docs/spec/08_changelog.md`, `README.md`, `docs/PHASE6_HANDOFF.md`, `tests/test_scaffold.py`

**Interfaces:**
- Configuration and documentation describe only verified Phase 0–5 behavior and explicitly retain the Phase 4 no-learning-claim result.

- [ ] Add failing consistency tests for phase markers, stale labels, and explicit experiment timing.
- [ ] Run them and verify the known drift is detected.
- [ ] Reconcile config, labels, canonical status, changelog, README, and handoff wording from current code/CI evidence.
- [ ] Run full suite, compile, headless runner, and diff checks.
- [ ] Commit the reconciliation.

### Task 5: Review, merge, and cross-repository reconciliation

- [ ] Run final self-audit against Issues #27–#31 and the AI/devflow rules.
- [ ] Open a PR from the dedicated branch, obtain exact-head Formal Review and green CI.
- [ ] Merge safely and verify post-main CI.
- [ ] Update devflow Control #314 Audit SHA/routing according to devflow#321, verify live MCP output, and close/reconcile #321 only after evidence is green.
- [ ] Update #27 and all child cursors/session records with final evidence; keep Phase 6+ blocked until a new bounded owner is explicitly created.
