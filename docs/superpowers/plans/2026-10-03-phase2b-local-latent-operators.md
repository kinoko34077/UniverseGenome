# UniverseGenome Phase 2B — local latent operator transmission

## Objective

Implement only the four bounded local latent transmission families required by
`REQ-050..052`, `SPEC-MASK-001`, and `SPEC-LATENT-C0..C3` on the accepted
Phase 2A core.

## Design boundary

- Keep latent state anonymous `uint16`; operator category is a universe
  parameter, not a semantic label on individual bits.
- Derive a 1..16-bit mask from each transmitting participant's local bond
  strength using counter-based event randomness.
- Use one deterministic non-overlapping compatible pair per slot at most for
  transmission, and apply all latent results from a pre-transmission snapshot.
- Count successful local transmission as activity for HP recovery; ordinary
  movement remains insufficient.
- Keep fusion, fragmentation, aging, multi-universe execution, I/O,
  optimization and Phase 6+ deferred.

## Execution sequence

1. Add RED tests for all four formulas, mask width/determinism, synchronous
   contact transmission, snapshot continuation, runner status and metrics.
2. Add parameterized operators, deterministic masks, synchronous latent
   resolution and activity recovery.
3. Reconcile config, runner, README, roadmap, changelog and specification
   status while keeping fusion disabled.
4. Run focused/full tests, compile/headless checks and a diff/invariant audit.
5. Record exact-head evidence in Issue #12/#7, review and merge, verify main,
   reconcile devflow Control #314, then begin Phase 2C setup.
