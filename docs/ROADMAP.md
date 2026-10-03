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
2B four latent operators (in progress; #12)
2C fusion
2D fragmentation
2E aging

## Phase 3 — 128-universe runtime and observation GUI
4 categories × 32 slots, matched genome/seed comparisons, overview/detail/rewind/clone observation.

## Phase 4 — I/O learning
8-bit bus, teacher stimulation, A → B → NULL, evaluation clone, baseline-vs-trained measurement.

## Phase 5 — Universe-genome optimization
fitness/growth separation, pruning, mutation, steady-state evolution, multi-seed escalation.

## Phase 6+ — Capability ladder (handoff only after Phase 5)
multiple mappings, sequence discrimination, multi-event output, forgetting/relearning, robustness, generalization, multi-byte/raw UTF-8 experiments.
