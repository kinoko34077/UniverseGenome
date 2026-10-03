# UniverseGenome Implementation Roadmap

## Gate 0 — Specification basis
Status: completed by Phase 0 specification reconciliation.

## Phase 0 — Repository/spec scaffold
Goal: a fresh worker can begin Phase 1 from GitHub alone.

Deliverables:
- canonical specification index/files
- ADRs
- bounded package/module scaffolds
- config/persistence/server/UI/test scaffolds
- minimal headless entrypoint
- automated smoke verification
- README routing

## Phase 1 — Minimal deterministic universe (accepted on `main`; #8 / PR #9)
- 32×32 torus
- 256×256 fixed-point position
- fixed slot pool
- structure/latent/HP state
- direction/speed
- synchronous movement
- destination footprint
- tunneling
- noise spawn
- collision
- HP/BLACK_HOLE
- deterministic replay
- snapshot roundtrip
- headless performance counters

## Phase 2 — Local learning physics
2A contact/bond (accepted on `main`; #10 / PR #11)
2B four latent operators (accepted on `main`; #12 / PR #13)
2C fusion (accepted on `main`; #14 / PR #15)
2D fragmentation (accepted on `main`; #16 / PR #17)
2E aging (accepted on `main`; #18)

## Phase 3 — 128-universe runtime and observation GUI (accepted on `main`; #20 / PR #21, remediation #29 / PR #33)
4 categories × 32 slots, matched genome/seed comparisons, server-owned runtime
API, overview/detail/rewind/clone observation, and bounded controls.

## Phase 4 — I/O learning (accepted on `main`; #22 / PR #23, remediation #28 / PR #32)
8-bit bus, teacher stimulation, A → B → NULL, evaluation clone, real
baseline-vs-trained autonomous measurement. Current result remains 0 / 0 with
no learning claim.

## Phase 5 — Universe-genome optimization (accepted on `main`; #24 / PR #25, remediation #30 / PR #34)
validated genome-to-physics mapping, real Phase 4 candidate evaluation,
fitness/growth separation, category-local pruning, mutation, steady-state
replacement, and bounded multi-seed escalation.

## Phase 6+ — Capability ladder (handoff only after Phase 5)
multiple mappings, sequence discrimination, multi-event output, forgetting/relearning, robustness, generalization, multi-byte/raw UTF-8 experiments.
