# UniverseGenome Phase 2A — local contact/bond physics

## Objective

Implement only the bounded local contact/bond behavior required by
`REQ-070..071` and `SPEC-BOND-001..002` on the accepted Phase 1 core.

## Design boundary

- Keep bond strength as local `uint8` state; never create a persistent pair
  graph or permanent cell identity.
- Reuse the existing destination occupancy buckets and one-pair bounded
  resolver for contact candidates.
- Treat a pair as compatible when its direction-aware relative velocity is at
  or below the configured Phase 2A threshold.
- Apply saturating gain to both compatible participants and saturating decay to
  every other active cell once per generation.
- Keep latent operators, transmission masks, fusion, fragmentation, aging,
  multi-universe execution, I/O, optimization, and Phase 6+ deferred.

## Execution sequence

1. Add RED tests for compatible gain, incompatible/non-contact decay, bounded
   3+ handling, snapshot continuation, runner status, and counters.
2. Add explicit bond parameters and the synchronous bond update after bounded
   collision/contact resolution.
3. Reconcile config, runner, README, roadmap, changelog, specification routing
   and feature flags.
4. Run focused tests, full tests, compile checks, headless execution, and a
   diff/invariant self-audit.
5. Record the exact head in Issue #10/#7, obtain formal review and CI, merge,
   verify main, then reconcile devflow Control #314 before Phase 2B.
