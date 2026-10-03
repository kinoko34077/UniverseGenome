# UniverseGenome Phase 2C — bounded local fusion

## Objective

Implement only the local 2×2 fusion transition required by
`SPEC-FUSION-001..003` and `REQ-040..042` on the accepted Phase 2B core.

## Design boundary

- Discover only anchors adjacent to occupied destination tiles; never scan
  arbitrary global groups.
- Enumerate bounded local groups of two through four non-overlapping footprints
  that exactly cover one 2×2 region.
- Require same level, pairwise fusion velocity threshold and local bond
  threshold; select deterministic non-overlapping groups.
- Reuse the lowest storage slot as the upper-level 1×1 result, saturate HP,
  choose highest-HP direction with lowest-slot tie-break, choose minimum speed,
  reset age/bond, mix latent state with fixed 0/4/8/12 rotations, and free the
  remaining participant slots.
- Keep fragmentation, aging, multi-universe execution, I/O, optimization and
  Phase 6+ deferred.

## Execution sequence

1. Add RED tests for eligibility, exact composition, result fields, latent
   mixer, freed-slot reuse, ineligible groups, snapshot continuation, status
   and counters.
2. Add parameterized fusion thresholds, local candidate discovery, synchronous
   result commit and headless fusion metrics.
3. Reconcile config, runner, README, roadmap, changelog and specification
   status while keeping fragmentation disabled.
4. Run focused/full tests, compile/headless checks and a diff/invariant audit.
5. Record exact-head evidence in Issue #14/#7, review and merge, verify main,
   reconcile devflow Control #314, then begin Phase 2D setup.
