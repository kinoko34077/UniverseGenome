# Specification Changelog

## 2026-10-03 — v0.1 specification basis established
- Issue #2 preserves historical rationale.
- Issue #3 requirements are canonicalized to `docs/spec/01_requirements.md`.
- Issue #4 detailed specification is split across `docs/spec/`.
- ADR-001..ADR-008 preserve architecture rationale.
- Phase 0/1 boundary remains explicit.
- No runtime physics capability is claimed by this specification-only checkpoint.

Future physical-rule changes must record affected REQ/SPEC IDs, old/new behavior, rationale, test impact, snapshot/compatibility impact and status changes.

## 2026-10-03 — Phase 1 implementation candidate (#8)
- `core/physics.py` now implements the bounded deterministic single-universe
  step: fixed-point torus movement, destination-only footprints, tunneling,
  spatial buckets, bounded collision pairing, HP/lifecycle handling, noise and
  performance counters.
- `core/state.py` and `persistence/snapshot.py` provide reusable fixed slots,
  no permanent Cell ID, and versioned continuation-equivalent snapshots.
- `core/runner.py` provides a headless Phase 1 JSON run surface.
- Phase 2A+ physics, multi-universe runtime, I/O learning, and outer search
  remain deferred. This entry records implementation/test status on child #8;
  Phase 1 acceptance remains gated by exact-head CI, Review, merge and
  post-main reconciliation.
