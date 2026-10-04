# UniverseGenome Implementation Roadmap

## Current repository state

Phase 0 through Phase 5 are readiness-accepted on `main`. Current State
reconciliation #66, Phase 5 remediation #65, GUI/search integration #63, and
post-v0.1 residual reconciliation #61 are complete; readiness rerun #60 passed.
Phase 6 roadmap #78 is active. P6.1 multiple independent byte mappings are
accepted through #79 / PR #80, P6.2 temporal sequence discrimination through
#82 / PR #83, P6.3 multi-event output timing through #85 / PR #86, P6.4
forgetting/relearning retention through #88 / PR #89, P6.5 controlled
physical-noise robustness through #91 / PR #92, P6.6 predeclared held-out
relation generalization through #95 / PR #96, P6.7 bounded distinct
multi-byte output sequences through #98 / PR #99, and P6.8 bounded raw UTF-8
byte experiments through #101 / PR #102 on main. No later capability is
currently selected; the next frontier is an explicit roadmap/research decision.

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
#85 / PR #86. P6.4 forgetting/relearning is implemented/accepted through #88 /
PR #89: the protocol measures T0 immediate retention eligibility, advances the
same trained state through a declared no-teacher delay plus deterministic
unmapped-CA interference, evaluates T1, applies one relearning curriculum pass
without reset, then evaluates T2. Evaluable retention is growth-only Phase 5
evidence and does not alter absolute fitness ordering.

The accepted bounded P6.4 smoke produced no T0-success cases across its three
seeds × two mappings. Therefore retention/relearning were explicitly
non-evaluable (`null`) and `learning_claim=false`; capability acceptance is
not a learning or retention-success claim.

P6.5 controlled physical-noise robustness is implemented/accepted through #91 /
PR #92. It compares matched clean/noisy disposable evaluations from the same
trained T0 state, uses the existing physical background-noise path, requires
clean mapped success for evaluability, and exposes null-aware robust/failure
evidence. Evaluable noise robustness may drive growth-only Phase 5 bit 6 without
changing absolute fitness.

The accepted bounded P6.5 smoke produced zero clean-success eligible cases.
Noise robustness was therefore explicitly non-evaluable (`null`) and
`learning_claim=false`; capability acceptance is not a robustness-success
claim.

P6.6 predeclared held-out relation generalization is implemented/accepted
through #95 / PR #96. The bounded smoke produced teacher success 0→0,
`training_qualified_count=0`, `generalization_eligible_count=0`, and
`generalization_rate=null`; `learning_claim=false`. Capability acceptance is
therefore not a successful-generalization claim.

P6.7 bounded distinct multi-byte output sequences are implemented/accepted
through #98 / PR #99. The capability changes the timed output target from
repeated identical bytes to exact ordered tuples `B,C` and `D,E`, while
preserving legacy protocol behavior and Phase 5 search semantics. The bounded
smoke produced zero trained mapped successes and `learning_claim=false`;
capability acceptance is not a sequence-learning-success claim.

P6.8 bounded raw UTF-8 byte experiments are implemented/accepted through #101 /
PR #102. They reuse the P6.7 byte-sequence runtime with externally documented
valid UTF-8 byte arrays only; no tokenizer, Unicode semantic state or Phase 5
search change is introduced. The bounded smoke produced zero trained mapped
successes and `learning_claim=false`; capability acceptance is not a
UTF-8-learning-success claim.

Next frontier: **explicit Phase 6+ roadmap/research decision**. No P6.9 or later
capability is automatically authorized. Any continuation requires #78 to select
one bounded capability and a new child Issue with explicit acceptance criteria.
