# UniverseGenome Phase 1 — minimal deterministic universe

## Goal

Implement only the Phase 1 single-universe physical foundation required by
UniverseGenome#7/#8. Preserve the inner-physics/outer-search boundary, the
no-permanent-Cell-ID invariant, fixed-point toroidal geometry, and the
headless core/GUI boundary.

## Design

- `core/state.py` owns a reusable fixed-capacity slot-pool state and explicit
  parameter data. Lists are used as the dependency-free fixed arrays in this
  phase; their lengths never grow during execution.
- `core/physics.py` owns synchronous proposal → aggregate → resolve → commit
  stepping. Movement uses fixed-point vectors and destination-only footprints.
  Temporary destination buckets are generation-local. Three-or-more arrival
  resolution selects one deterministic event-random pair without enumerating
  all pairs.
- `core/rng.py` uses a counter/event-key deterministic hash. Random outcomes
  depend only on `(seed, generation, spatial address, event type, local index)`;
  no slot identity is part of the key.
- Collision, HP/lifecycle, noise, and black-hole behavior are parameterized in
  `PhysicsConfig`; unresolved specification choices remain visible defaults in
  `config/default.json`.
- `persistence/snapshot.py` serializes the complete Phase 1 authoritative state
  and parameters as versioned JSON. Counter-based RNG needs no hidden mutable
  RNG object, so load → continue must equal uninterrupted continuation.
- `core/runner.py` exposes a headless Phase 1 run and JSON performance counters.
  The UI remains an observer scaffold and never owns the clock.

## TDD sequence

1. Add RED tests for TEST-P1-001..010: replay, torus, all speeds, tunneling,
   deterministic noise, bounded collision, HP/BLACK_HOLE/recovery/deletion,
   snapshot continuation, headless execution, and performance counters.
2. Implement state/config/RNG/geometry/physics/snapshot/runner in the smallest
   slices needed to turn the tests GREEN.
3. Run focused Phase 1 tests, then the full repository suite and compile checks.
4. Audit invariants and exact Phase 1 exclusions; update checked-in config,
   README/roadmap/spec changelog only for the accepted implementation frontier.
5. Open an exact-head PR, submit Formal Review, verify CI/main, and reconcile
   #8, #7, #1, and devflow#314 before any Phase 2A work.

## Explicit exclusions

No bond runtime, latent operators, fusion, fragmentation, aging, 128-universe
runtime/GUI, I/O learning, optimizer/evolution, semantic labels, dense global
mixing, permanent IDs, or GUI-driven ticks.
