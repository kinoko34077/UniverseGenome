# UniverseGenome Implementation Roadmap

## Current repository state

Phase 0 through Phase 5 are readiness-accepted on `main`. Current State
reconciliation #66, Phase 5 remediation #65, GUI/search integration #63, and
post-v0.1 residual reconciliation #61 are complete; readiness rerun #60 passed.
Phase 6 roadmap #78 is active. P6.1 multiple independent byte mappings are
accepted through #79 / PR #80, P6.2 temporal sequence discrimination through
#82 / PR #83, and P6.3 multi-event output timing through #85 / PR #86 on main;
the next bounded frontier is P6.4 forgetting/relearning.

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

P6.1 multiple independent byte mappings is implemented/accepted through #79 /
PR #80. P6.2 temporal sequence discrimination is implemented/accepted through
#82 / PR #83. P6.3 multi-event output timing is implemented/accepted through
#85 / PR #86: the protocol can require two repeated autonomous byte events at
a declared physical-generation onset interval before NULL, evaluate exact
content/order/count/timing on isolated clones, preserve P6.2 controls, and
round-trip the timing contract through Phase 5 optimizer snapshots.

The accepted bounded P6.3 smoke observed AA→B,B 0→0 and AC→D,D 0→0 across
three seeds; no-input, prefix-A and unmapped-CA controls were clean, so
`learning_claim=false` remains the truthful result.

Next frontier: **P6.4 forgetting/relearning** as one new bounded child Issue.
P6.5+ remains deferred: noise robustness, generalization, multi-byte sequences,
and raw UTF-8 experiments.
