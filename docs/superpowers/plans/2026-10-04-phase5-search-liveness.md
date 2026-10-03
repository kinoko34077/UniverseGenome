# Phase 5 search liveness and mutation-boundary remediation

## Objective

Address only the unambiguous implementation gaps recorded in Issue #65 and
the #68 remediation order. Keep the promising-allocation policy undecided;
do not add a 4→8→16→32 threshold or silently choose one.

## Scope

1. Add an observable 16-generation short-health path on authoritative
   physical-generation metrics, including deterministic absolute-failure
   detection and pruning eligibility.
2. Make integrated mutation deterministic, adjacent-grid, bidirectional, and
   bounded by the effective `PhysicsConfig` so mutation cannot be a no-op or
   create an invalid child.
3. Keep the accepted growth-bit names and semantics unchanged. Do not
   relabel retention/noise robustness as no-input/alternate-input cleanliness;
   that mapping remains an explicit specification decision gate.
4. Preserve the unresolved promising-policy gate and update the durable
   handoff evidence after verification.

## Execution order

- Write focused failing tests for each observable before implementation.
- Implement the smallest production changes that make those tests pass.
- Run the focused tests, then the full suite, compile check, diff check, and
  deterministic snapshot/headless checks.
- Self-review the exact diff for policy invention, snapshot compatibility,
  and accidental changes outside #65.
- Commit, push the branch, open a separate PR, and report the exact head and
  remaining Human decision gate. Do not merge.

## Acceptance checks

- `SHORT_WINDOW=16` is used by the authoritative optimizer path.
- Absolute failures are distinguishable from ordinary low growth and can free
  a slot without waiting for a 128-generation growth history.
- A mutation at either bound selects the opposite valid adjacent direction or
  reports that no valid mutation exists; no unchanged child is admitted.
- Mutation of `initial_density` respects the effective `max_cells` bound.
- Growth bits 5 and 6 retain their existing canonical names without a new
  proxy equivalence.
- The promising allocation policy remains a documented unresolved gate.
