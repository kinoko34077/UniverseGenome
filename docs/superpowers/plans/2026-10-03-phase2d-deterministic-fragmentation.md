# UniverseGenome Phase 2D — deterministic fragmentation

## Objective

Implement only the bounded hierarchy fragmentation behavior required by
`SPEC-FRAG-001..006` on the accepted Phase 2C core.

## Design boundary

- Use one counter-based event attempt per active slot and an explicit uint16
  fragmentation rate.
- For level > 0, retain the upper core and allocate one lower 1×1 fragment;
  split latent bits, HP and age according to the canonical formulas.
- Use opposite direction, the same speed, deterministic split mask and a fixed
  capacity no-op when no slot is available.
- At level 0, collapse compound shapes to 1×1 and delete a 1×1 cell through
  the existing reusable-slot path.
- Keep aging, multi-universe execution, I/O, optimization and Phase 6+
  deferred.

## Execution sequence

1. Add RED tests for level>0 split state, level-0 collapse/deletion,
   probability/capacity no-ops, snapshot continuation, runner status and
   counters.
2. Add parameterized fragmentation, deterministic split masks, fixed-capacity
   allocation and commit-order handling.
3. Reconcile config, runner, README, roadmap, changelog and specification
   status while keeping aging disabled.
4. Run focused/full tests, compile/headless checks and a diff/invariant audit.
5. Record exact-head evidence in Issue #16/#7, review and merge, verify main,
   reconcile devflow Control #314, then begin Phase 2E setup.
