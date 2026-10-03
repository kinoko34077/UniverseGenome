# Current-State Truth Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile UniverseGenome's checked-in documentation, runtime status projection, and durable traceability so unresolved #63/#65/#66 remediation keeps Phase 6 explicitly blocked without rewriting historical acceptance evidence.

**Architecture:** Keep feature flags as implementation-presence signals only. Add an explicit repository current-state projection for acceptance/readiness, make every public status surface consume that distinction, and preserve historical plans/checkpoints as non-canonical execution records. Use additive changelog and issue-routing notes for historical traceability.

**Tech Stack:** Python 3, `unittest`, JSON configuration, Markdown documentation, GitHub Issue/PR comments.

**Spec:** `docs/SPECIFICATION.md`, `docs/spec/00_overview.md`, `docs/spec/06_implementation_spec.md`, Issue #66, handoff Issue #68.

## Global Constraints

- Do not implement Phase 6+ capability.
- Do not change Phase 4's recorded `baseline 0 / trained 0 / learning_claim=false` result.
- Feature flags may report implementation presence but never prove acceptance or readiness.
- Keep Phase 6 blocked while current P1 owners #63, #65, and #66 remain unresolved; #60 is the later readiness rerun.
- Preserve historical acceptance records and plan files; add correction/routing notes instead of rewriting history.
- Do not choose the open Phase 5 promising-allocation policy.

## Review Focus

- A config with all implementation flags enabled must still report remediation-blocked readiness; test the separation from `phase5_optimizer_implemented`.
- A partial feature configuration must retain accurate implementation-phase reporting while keeping the explicit readiness state truthful.
- Every top-level status/documentation surface must use the same blocked vocabulary; test the runtime projection and representative text together.
- Historical plan checkboxes and merge SHAs must remain present while being clearly labeled non-canonical; test that the historical markers are not deleted.
- Traceability corrections must be additive and point to the accepted PR/Issue references; test the exact roadmap/changelog/REQ correction strings.

---

### Task 1: Pin the blocked current-state contract

**Files:**
- Modify: `tests/test_scaffold.py`
- Modify: `tests/test_phase2a.py`, `tests/test_phase2b.py`, `tests/test_phase2c.py`, `tests/test_phase2d.py`, `tests/test_phase2e.py`, `tests/test_phase3.py`, `tests/test_phase4.py`, `tests/test_phase5.py`

**Interfaces:**
- Consumes: `core.runner.build_status()` and current-state documentation files.
- Produces: failing assertions for implementation presence versus acceptance/readiness and truthful routing language.

- [ ] **Step 1: Write the failing tests** for an all-enabled configuration that asserts implementation flags remain true, `acceptance_state` is remediation-blocked, `phase6_ready` is false, the unresolved owners are named, and `next_phase` routes to remediation rather than Phase 6.
- [ ] **Step 2: Run the focused scaffold/status tests** and confirm the old feature-flag-derived projection fails the new assertions.
- [ ] **Step 3: Commit the RED contract tests** with `test: pin post-audit current-state truth`.

### Task 2: Implement the explicit runtime status projection

**Files:**
- Modify: `core/runner.py`
- Modify: `config/default.json`

**Interfaces:**
- Consumes: explicit `project.current_state` data from the default config.
- Produces: `build_status()` fields separating implementation flags from `acceptance_state`, `phase6_ready`, `blocking_owners`, and `next_phase` routing.

- [ ] **Step 1: Add the explicit current-state configuration** with remediation-blocked status, Phase 6 disabled, and the current owner routing; do not derive these values from feature flags.
- [ ] **Step 2: Implement the smallest status projection** that preserves the existing `phase*_implemented` fields while exposing the explicit acceptance/readiness fields.
- [ ] **Step 3: Run the Task 1 focused tests** and confirm GREEN.
- [ ] **Step 4: Commit** with `fix: separate implementation status from readiness`.

### Task 3: Reconcile canonical documentation and historical plans

**Files:**
- Modify: `README.md`
- Modify: `docs/SPECIFICATION.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/PHASE6_HANDOFF.md`
- Modify: `docs/spec/00_overview.md`
- Modify: `docs/spec/01_requirements.md`
- Modify: `docs/spec/02_functional_spec.md`
- Modify: `docs/spec/08_changelog.md`
- Modify: `docs/superpowers/plans/2026-10-03-phase5-authoritative-slots.md`
- Modify: `docs/superpowers/plans/2026-10-03-phase5-semantic-corrections.md`
- Modify: `docs/superpowers/plans/2026-10-04-phase5-free-slot-evidence.md`

**Interfaces:**
- Consumes: the Task 2 current-state vocabulary and #66/#68 routing.
- Produces: additive documentation that says Phase 0–5 implementation is present but acceptance remediation is active and Phase 6 is blocked; historical plan files explicitly remain historical records.

- [ ] **Step 1: Update the current-state surfaces** to name #63/#65/#66 as unresolved P1 owners, #60 as the later readiness rerun, and Phase 6 as blocked.
- [ ] **Step 2: Normalize the specification status vocabulary** by keeping the declared base status terms and moving invariant/parameter/policy-hook qualifiers into explicit explanatory text.
- [ ] **Step 3: Add additive traceability corrections** for Phase 2D `#16 / PR #17`, the Phase 2D acceptance changelog entry, and the historical `REQ-083` reference issue without rewriting prior acceptance entries.
- [ ] **Step 4: Mark the three Phase 5 plans as historical execution records** whose checkboxes do not define Current State.
- [ ] **Step 5: Run text consistency checks** for blocked routing, historical markers, status vocabulary, and the additive traceability references.
- [ ] **Step 6: Commit** with `docs: reconcile post-audit current state`.

### Task 4: Full verification and durable handoff

**Files:**
- Verify: repository tests, source tree, current PR/Issue state.

- [ ] **Step 1: Run the full Python test suite** and record the exact count and exit status.
- [ ] **Step 2: Run `compileall` and `git diff --check`.**
- [ ] **Step 3: Inspect the final diff** to confirm no Phase 6 capability, no learning-claim change, no historical deletion, and no unapproved Phase 5 policy.
- [ ] **Step 4: Push the dedicated branch and open/update a PR against `main`.**
- [ ] **Step 5: Add durable comments to #66 and the relevant historical routing Issues (#1, #4, #7), then record exact head and verification evidence in the PR.**
- [ ] **Step 6: Request exact-head review; leave merge to the user.**
