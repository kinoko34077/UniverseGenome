# Specification Changelog

## 2026-10-03 — v0.1 specification basis established
- Issue #2 preserves historical rationale.
- Issue #3 requirements are canonicalized to `docs/spec/01_requirements.md`.
- Issue #4 detailed specification is split across `docs/spec/`.
- ADR-001..ADR-008 preserve architecture rationale.
- Phase 0/1 boundary remains explicit.
- No runtime physics capability is claimed by this specification-only checkpoint.

Future physical-rule changes must record affected REQ/SPEC IDs, old/new behavior, rationale, test impact, snapshot/compatibility impact and status changes.

## 2026-10-03 — Phase 1 accepted (#8 / PR #9)
- `core/physics.py` now implements the bounded deterministic single-universe
  step: fixed-point torus movement, destination-only footprints, tunneling,
  spatial buckets, bounded collision pairing, HP/lifecycle handling, noise and
  performance counters.
- `core/state.py` and `persistence/snapshot.py` provide reusable fixed slots,
  no permanent Cell ID, and versioned continuation-equivalent snapshots.
- `core/runner.py` provides a headless Phase 1 JSON run surface.
- Exact-head CI, formal review, PR merge, and post-main verification completed
  on merge commit `243ec24100cd96c051267ef53a74ca58652cb4b2`.

## 2026-10-03 — Phase 2A bond/contact implementation candidate (#10)
- `core/physics.py` now updates local `bond_strength:uint8` with explicit,
  saturating gain/decay parameters for compatible destination contact.
- Headless metrics expose compatible bond contacts, while bounded destination
  pair resolution remains unchanged.
- Phase 2B latent operators and all later phases were deferred pending a later
  child Issue.

## 2026-10-03 — Phase 2A accepted (#10 / PR #11)
- Local `bond_strength:uint8` gain/decay, deterministic contact accounting,
  snapshot continuation, and headless bond metrics passed exact-head review,
  merge, and post-main CI on `1e0a1fa0bae9a599d4f4f17564a4683d9f292992`.

## 2026-10-03 — Phase 2B latent operator implementation candidate (#12)
- `core/physics.py` implements deterministic 1..16-bit local masks and the four
  accepted 16-bit latent operator families with synchronous updates.
- Successful local transmission contributes activity for HP recovery and is
  exposed in headless metrics.
- Phase 2C fusion and later phases were deferred pending #12 acceptance.

## 2026-10-03 — Phase 2B accepted (#12 / PR #13)
- Deterministic local masks, four latent operators, synchronous propagation,
  activity recovery, snapshot continuation and headless transmission metrics
  passed exact-head review, merge, and post-main CI on
  `ee9a36d573707aeb9835c82f941beb526485c46f`.

## 2026-10-03 — Phase 2C fusion implementation candidate (#14)
- `core/physics.py` discovers bounded local exact 2×2 footprint covers and
  commits deterministic upper-level cores with the specified HP, direction,
  speed, age, bond, latent mixer and slot reuse behavior.
- Phase 2D fragmentation and later phases remain deferred pending #14
  acceptance.

## 2026-10-03 — Phase 2C accepted (#14 / PR #15)
- Bounded local exact 2×2 fusion, deterministic upper-level result state,
  latent mixer, HP/slot lifecycle and snapshot continuation passed exact-head
  review, merge, and post-main CI on
  `9d860c5e7cc61df647bc7c36c7f465854af565fa`.

## 2026-10-03 — Phase 2D fragmentation implementation candidate (#16)
- `core/physics.py` implements deterministic fixed-capacity fragmentation,
  level-0 collapse/deletion, latent/HP/age split and headless counters.
- Phase 2E aging and later phases remain deferred pending #16 acceptance.
## 2026-10-03 — Phase 2E aging implementation candidate (#18)
- `core/physics.py` implements safe highest-set-bit age classes and
  deterministic power-of-two fragmentation pressure with uint16 saturation.
- Phase 3 and later runtime/learning work remains deferred pending #18
  acceptance.
