# UniverseGenome Implementation Roadmap

## Current repository state

Phase 0 through Phase 5 are readiness-accepted on `main`. Remediation and
residual reconciliation are complete and readiness rerun #60 passed. Phase 6
roadmap #78 is active. P6.1 multiple independent byte mappings is implemented
and accepted via #79 / PR #80. The current frontier is P6.2 temporal sequence
discrimination, which must begin as a separate bounded child Issue.

## Gate 0 — Specification basis
Status: accepted by Phase 0 specification reconciliation.

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

## Phase 1 — Minimal deterministic universe (implementation present; historical acceptance #8 / PR #9)
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
2A contact/bond (implementation present; historical acceptance #10 / PR #11)
2B four latent operators (implementation present; historical acceptance #12 / PR #13)
2C fusion (implementation present; historical acceptance #14 / PR #15)
2D fragmentation (implementation present; historical acceptance #16 / PR #17)
2E aging (implementation present; historical acceptance #18 / PR #19)

## Phase 3 — 128-universe runtime and observation GUI (implementation present; historical acceptance #20 / PR #21, remediation #29 / PR #33)
4 categories × 32 slots, matched genome/seed comparisons, server-owned runtime
API, overview/detail/rewind/clone observation, and bounded controls.

## Phase 4 — I/O learning (implementation present; historical acceptance #22 / PR #23, remediation #28 / PR #32)
8-bit bus, teacher stimulation, A → B → NULL, evaluation clone, real
baseline-vs-trained autonomous measurement. Current result remains 0 / 0 with
no learning claim.

## Phase 5 — Universe-genome optimization (implementation present; historical architecture restoration #58 / PR #59)
The historical Phase 5 contract restored by #58 / PR #59 uses exactly 128 persistent authoritative
Universe slots as four category-local groups of 32. One slot owns one category,
one genome, one seed and one continuing UniverseState. Fitness aggregates real
same-genome seed slots; growth is observed on real 128-generation boundaries;
steady-state replacement occurs only after a real prune/free target exists;
minimum evidence and depleted-mature-group lifecycle are explicit; optimizer
snapshot/restore preserves deterministic continuation.

Phase 5 search-semantics remediation #65 is complete via PR #70 and
cross-phase GUI/authoritative-search remediation #63 is complete via PR #73.
Earlier implementation/remediation history: #24 / PR #25, #30 / PR #34,
#36 / PR #39, #37 / PR #40, #38 / PR #41, #44 / PR #50, #56 / PR #57.

## Phase 6+ — Capability ladder (#78)

### P6.1 — Multiple independent byte mappings — COMPLETE
#79 / PR #80 implements ordered A→B and C→D protocol mappings on one
authoritative training history with isolated per-mapping evaluation. The
accepted smoke result remains 0 trained successes for both mappings and
`learning_claim=false`.

### P6.2 — Temporal sequence discrimination — CURRENT FRONTIER
Next candidate targets are `AA→B→NULL` and `AC→D→NULL`. This capability must
be specified and implemented in one new bounded child Issue; it is not included
in P6.1.

Later ladder items remain:
3. multi-event output timing;
4. forgetting/relearning;
5. noise robustness;
6. generalization;
7. multi-byte sequences;
8. raw UTF-8 experiments.

Each step advances only after its own acceptance, exact-head verification,
merged-main verification and Current State reconciliation.
