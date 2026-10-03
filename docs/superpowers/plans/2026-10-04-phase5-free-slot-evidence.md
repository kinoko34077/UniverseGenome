# Phase 5 Free-Slot Evidence Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Phase 5 replace authoritative Universe slots only after a real free/prune-eligible slot exists, and prevent mutation genomes from influencing selection before four real seed Universes establish minimum evidence.

**Architecture:** Keep the fixed 128-slot authoritative population and persistent `UniverseState` model. `step()` will perform no replacement when no slot is prune-eligible; when a slot is freed, incomplete mutation-child groups are completed with additional real seed slots before any new mutation or approved promising-policy allocation. Parent and protection decisions will consider only category/genome groups with at least four real seed slots.

**Tech Stack:** Python 3, `unittest`, existing Phase 5 optimizer and snapshot model.

**Spec:** `docs/spec/02_functional_spec.md`, `docs/spec/07_test_spec.md`, Issue #58, PR #59, Review 5401398642.

## Global Constraints

- Preserve exactly 128 authoritative Universe slots, one persistent `UniverseState` per occupied slot.
- Replace a live slot only when a real pruning/explicit-free decision makes that slot available.
- Represent evidence with real same-category/same-genome slots; do not add hidden multi-seed state.
- Treat `4 → 8 → 16 → 32` as real evidence cardinalities; do not introduce a new promising threshold.
- Keep the promising-allocation policy hook open and default-disabled.
- Keep evaluation-clone generations separate from authoritative physical generations.
- Do not start Phase 6 or change the learning claim.

## Review Focus

- No-prune optimizer step: every live slot identity and state must survive.
- One-seed mutation child: a lucky fitness value must not make it a parent or protected leader.
- Minimum evidence completion: a freed slot must be able to add a real seed to an incomplete mutation group until four seeds exist.
- Parent fallback: no mutation child below four seeds may be used as the source of another mutation child.
- Growth cadence: fresh generation 0 reference followed by exactly four observed windows at 128, 256, 384, and 512.

---

### Task 1: Add regression tests for the two blockers and the growth boundary

**Files:**
- Modify: `tests/test_phase5.py`

**Interfaces:**
- Consumes: `SteadyStateOptimizer.step`, `_select_parent`, `_protected_indices`, `allocate_seed_slot`, `_evaluate_slot`.
- Produces: failing tests that pin no forced replacement, minimum-evidence selection gating, evidence completion, and direct 0→512 growth coverage.

- [ ] **Step 1: Write the failing tests**

  Update the existing integrated-loop test to require zero replacements and preserved state identities when no growth window has made a slot free. Add tests that make a one-seed mutation child unusually fit and assert it is excluded from parent/protection decisions, and that a pruned target is used to allocate another real seed to that incomplete mutation group. Replace the generation-127 setup with a fresh generation-0 growth test asserting four windows after 512 authoritative generations.

- [ ] **Step 2: Run the focused tests to verify the blockers**

  Run: `python -m unittest tests.test_phase5.Phase5OptimizerTests.test_p5_020_integrated_loop_does_not_replace_live_slot_without_free_slot tests.test_phase5.Phase5OptimizerTests.test_p5_031_one_seed_mutation_child_is_not_selection_eligible tests.test_phase5.Phase5OptimizerTests.test_p5_032_incomplete_mutation_child_group_is_completed_from_pruned_slot tests.test_phase5.Phase5OptimizerTests.test_p5_021_growth_windows_follow_128_physical_generations -v`

  Expected: the no-replacement and one-seed/evidence-completion tests fail against the current implementation; the fresh generation-0 growth characterization test may pass because that runtime fix already exists.

- [ ] **Step 3: Commit the red regression tests**

  Commit message: `test: pin Phase 5 free-slot and evidence blockers`

### Task 2: Enforce free-slot replacement and minimum-evidence eligibility

**Files:**
- Modify: `search/evolution.py`

**Interfaces:**
- Consumes: `UniverseSlot.evidence_group`, `group_fitnesses`, `prune_candidates`, and existing real-slot allocation methods.
- Produces: deterministic selection helpers and `step()` behavior that preserves live slots without a free target and stages mutation groups to four real seeds before selection.

- [ ] **Step 1: Implement the minimum-evidence helpers**

  Add a named minimum evidence constant of four real slots, group-count helpers, and an internal filter for selection-eligible slots. Apply the filter to parent and protected-leader selection; keep aggregate fitness as the comparison value.

- [ ] **Step 2: Implement deterministic evidence completion**

  When a real target slot has been freed, first choose an incomplete mutation-child group that has another slot available as its parent and allocate a same-genome seed into the target. Only if no such group exists may the existing approved-policy hook or mutation-child path run. A mutation parent must be selection-eligible.

- [ ] **Step 3: Remove forced live-slot exploration replacement**

  In `step()`, skip the category when `prune_candidates()` returns no target. Do not select a worst live non-protected slot as `steady_state_exploration`.

- [ ] **Step 4: Keep immature mutation groups out of growth pruning**

  Pass only four-seed selection-eligible groups to growth pruning so a single lucky/unlucky seed cannot decide whether a mutation child is discarded before its minimum evidence tier is complete.

- [ ] **Step 5: Run the focused tests to verify GREEN**

  Run the Task 1 focused command. Expected: all named tests pass.

- [ ] **Step 6: Commit the implementation**

  Commit message: `fix: gate Phase 5 replacement on free slots and evidence`

### Task 3: Reconcile the Phase 5 specification and test contract

**Files:**
- Modify: `docs/spec/02_functional_spec.md`
- Modify: `docs/spec/07_test_spec.md`

**Interfaces:**
- Consumes: the implementation's four-real-slot evidence eligibility invariant.
- Produces: explicit documentation that minimum evidence is a selection-safety gate, not an unapproved promising threshold.

- [ ] **Step 1: Document the invariant**

  Add the minimum-evidence rule beside `SPEC-EVOL-001`/`SPEC-EVOL-002`: a category/genome group below four real seed slots cannot be used for parent or protection decisions; freed slots may complete an incomplete mutation group; the promising policy remains open.

- [ ] **Step 2: Document the acceptance coverage**

  Update `TEST-P5-004` to require no replacement without a real free/prune-eligible slot, minimum-evidence exclusion, and real 0/128/256/384/512 growth coverage.

- [ ] **Step 3: Run documentation consistency checks**

  Run: `rg -n "free|minimum evidence|4.*8.*16.*32|0.*128.*256.*384.*512|promising" docs/spec/02_functional_spec.md docs/spec/07_test_spec.md`

  Expected: the canonical free-slot rule, the four-seed gate, the evidence ladder, and the open promising-policy hook are all present without a new median/strict-fitness default.

- [ ] **Step 4: Commit the specification update**

  Commit message: `docs: record Phase 5 minimum evidence gate`

### Task 4: Full verification and handoff

**Files:**
- Verify: repository worktree and full test suite.

- [ ] **Step 1: Run the full Python test suite**

  Run: `python -m unittest discover -s tests -q`

  Expected: zero failures and zero errors. If the default Windows Node shim is unavailable, rerun with the repository's Python process PATH prefixed by the installed Codex Node runtime and record that environment limitation.

- [ ] **Step 2: Run compile and diff checks**

  Run: `python -m compileall -q core search persistence server tests; git diff --check`

  Expected: both commands exit 0.

- [ ] **Step 3: Review the final diff and local branch state**

  Confirm only the Phase 5 implementation, tests, specification, and required plan/ledger artifacts changed; do not push, merge, or publish.

- [ ] **Step 4: Record verification evidence**

  Report the exact local branch/head, test counts, and any unavailable external CI/browser gate without claiming those gates passed locally.
