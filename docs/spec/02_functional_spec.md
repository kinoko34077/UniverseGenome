# Functional Specification

Owns I/O, training/evaluation, population, mutation, fitness, pruning and
evolution behavior. Phase 4 and Phase 5 sections below describe the accepted
implemented boundary; later capability-ladder work remains handoff-only.

# 22. I/O organs

Specified for Phase 4.

## SPEC-IO-001 — Input bus
**Status: accepted-default**

Fixed organs:

- IN0
- IN1
- IN2
- IN3
- IN4
- IN5
- IN6
- IN7
- IN_VALID

A byte value is represented by the eight data lines while VALID marks the event.

All-zero byte remains representable because VALID is independent.

---

## SPEC-IO-002 — Output bus
**Status: accepted-default**

Fixed organs:

- OUT0..OUT7
- OUT_VALID
- OUT_NULL

---

## SPEC-IO-003 — Fixed organs
**Status: accepted-default**

I/O organs:

- fixed position
- not ordinary movable cells
- no HP death
- no fusion
- no fragmentation
- not noise-spawn targets
- may exchange signals with nearby normal cells

---

## SPEC-IO-004 — Placement
**Status: accepted-default**

Do not place input and output on opposite torus edges.

Implemented v0.1 logical-tile coordinates:

| Organ | Coordinate |
| --- | --- |
| IN0 | `(8, 12)` |
| IN1 | `(8, 13)` |
| IN2 | `(8, 14)` |
| IN3 | `(8, 15)` |
| IN4 | `(8, 16)` |
| IN5 | `(8, 17)` |
| IN6 | `(8, 18)` |
| IN7 | `(8, 19)` |
| IN_VALID | `(8, 21)` |
| OUT0 | `(24, 12)` |
| OUT1 | `(24, 13)` |
| OUT2 | `(24, 14)` |
| OUT3 | `(24, 15)` |
| OUT4 | `(24, 16)` |
| OUT5 | `(24, 17)` |
| OUT6 | `(24, 18)` |
| OUT7 | `(24, 19)` |
| OUT_VALID | `(24, 21)` |
| OUT_NULL | `(24, 22)` |

The coordinates are fixed non-cell organs and are sampled by the Phase 4
input/output boundary.

Initial-density and noise spawns reject every fixed-organ tile in the complete
destination footprint of the candidate cell. Compound cells therefore cannot
partially overlap an I/O line at creation time.

---

---

# 23. Output events

## SPEC-OUT-001 — Rising edge
**Status: accepted**

A byte output occurs only on `OUT_VALID: 0→1`.

Continuous HIGH does not emit repeated bytes.

A later LOW then HIGH emits a new byte.

NULL uses equivalent edge semantics.

NULL ends one utterance but does not stop universe time.

The evaluation detector is primed from the clone's current `OUT_VALID` level
without emitting an event. A persistent HIGH already present at evaluation
start is therefore not misclassified as a newly generated output.

Output occupancy and input stimulation use every tile in a compound cell's
destination footprint, not only its anchor tile.

---

---

# 24. Training protocol

## SPEC-TRAIN-001 — Initial task
**Status: accepted**

`A → B → NULL`

---

## SPEC-TRAIN-002 — Teacher episode
**Status: accepted-default**

Episode outline:

1. drive byte A at input
2. wait teacher delay
3. drive teacher B from output-side teaching interface inward
4. drive teacher NULL
5. continue universe time

Teacher-forced output activity must be excluded from autonomous score.

---

## SPEC-TRAIN-003 — Byte timing
**Status: accepted-default / parameterized**

Initial defaults:

- byte hold = 4 generations
- byte gap = 4 generations

Teacher delay is parameterized.

Do not make per-byte hold duration scale with entire input string length; that would create approximately quadratic total stimulus with string length.

Autonomous evaluation also records two output-clean counterfactuals for each
seed: no input signal and an alternate input byte. The learning claim requires
the trained A→B→NULL result to beat baseline and both counterfactuals to emit
no events across all evaluated seeds.

---

---

# 25. Evaluation clone

## SPEC-EVAL-001 — Clone evaluation
**Status: accepted-default**

At evaluation point:

1. clone authoritative training universe
2. apply input A only
3. do not teacher-force B/NULL
4. capture output events
5. score clone
6. discard clone

The authoritative training universe is unchanged by evaluation.

---

---

# 26. Universe parameters

## SPEC-PARAM-001 — Universe genome fields
**Status: accepted / parameterized values**

Candidate v0.1 genome/search fields include:

- initial density
- HP decay
- HP gain
- noise rate
- bond gain
- bond decay
- collision threshold
- fusion threshold
- fragmentation base probability
- black-hole grace
- rotate amount

Values should use binary-friendly grids where practical, without banning empirically useful intermediate values later.

---

---

# 27. Experiment parameters

## SPEC-PARAM-010 — Separate protocol config
**Status: accepted**

Experiment config is not part of the universe genome.

Examples:

- byte hold
- byte gap
- teacher delay
- teacher repetitions
- evaluation timeout
- test noise strength

---

---

# 28. Population layout

Specified for Phase 3/5.

## SPEC-POP-001 — Slots
**Status: accepted**

128 simultaneous universe slots.

Four categories × 32 slots.

---

## SPEC-POP-002 — Initial category population
**Status: accepted-default**

Per category:

- 8 parameter genomes
- 4 seeds each
- 32 slots total

The eight parameter genomes are deterministic and distinct. Matched
genome/seed positions should be used across categories when possible.

---

---

# 29. Mutation

## SPEC-MUT-001
**Status: accepted**

Numerical parameter mutation defaults to one adjacent binary-grid step.

Examples:

- 1/256 → 1/512 or 1/128
- 4 → 2 or 8

Do not evolve the physical rule category itself during the first category-comparison phase.

---

---

# 30. Fitness

## SPEC-FIT-001 — Lexicographic tuple
**Status: accepted-default**

Compare in order:

1. success
2. fewer wrong outputs
3. fewer timeouts
4. lower response latency
5. lower activity cost

Do not use internal structural abundance as direct success reward.

Optimizer fitness stores normalized rates for event/count fields and means for
latency/activity so candidates with 4, 8, 16, or 32 evidence seeds remain
comparable. Retention and alternate-input noise robustness are growth-only
dimensions, not additional absolute-fitness tie-breakers. Activity cost sums
the per-generation physics activity-event count over an evaluation: collisions,
bond contacts, latent transmissions, fusions, fragmentations, and noise
spawns.

---

---

# 31. Growth bitset

## SPEC-GROWTH-001
**Status: accepted-default**

Every 128 generations, derive an 8-bit improvement flag set.

Initial candidate bits:

- bit0 success improved
- bit1 wrong output decreased
- bit2 timeout improved
- bit3 latency improved
- bit4 activity efficiency improved
- bit5 retention improved
- bit6 noise robustness improved
- bit7 reserved

---

## SPEC-GROWTH-002
**Status: accepted-default**

Keep four recent 8-bit windows in one 32-bit history.

Coverage:

`128 × 4 = 512 generations`

Recent growth score may use:

`popcount(growth_history)`

---

---

# 32. Pruning

## SPEC-PRUNE-001 — Evaluation cadence
**Status: accepted**

- 16-generation short health window
- 128-generation growth window
- 512-generation stagnation horizon

---

## SPEC-PRUNE-002 — Category-relative threshold
**Status: accepted-default**

Within each category:

`low_growth = growth < (median_growth >> 1)`

Four consecutive low-growth windows may make a universe eligible for pruning.

---

## SPEC-PRUNE-003 — Protect mature leaders
**Status: accepted**

Absolute-fitness top 1/8 are protected from growth-only pruning.

---

## SPEC-PRUNE-004 — Absolute failures
**Status: accepted**

Examples:

- all active cells gone
- persistent non-response / no meaningful activity under defined protocol

“Chaos” is not a visual label. If chaos-based pruning is introduced, it must be defined through measurable conditions.

Implementation corruption is an error, not evolutionary death.

---

---

# 33. Steady-state evolution

## SPEC-EVOL-001
**Status: accepted-default**

Do not require whole-population synchronized evolutionary generations.

When a slot becomes free:

- add another seed for a promising genome, or
- insert a mutation child

Seed escalation for promising genome:

`4 → 8 → 16 → 32`

## SPEC-EVOL-002 — Promising allocation policy
**Status: accepted-default**

The v0.1 category-local policy is named `strict_fitness`. A genome is
promising for an additional seed allocation when at least one occupied slot for
that genome has a canonical fitness `sort_key()` strictly better than the
category median `sort_key()` among currently occupied slots. Equality is not
promising. The policy is scheduler state, is persisted in optimizer snapshots,
and may be replaced only by an explicit specification change. This rule is an
allocation policy; it does not add fields to the absolute fitness ordering.

The implemented steady-state boundary maintains exactly 128 authoritative
Universe slots as four category-local groups of 32. Each occupied slot owns
one category, one genome, one seed, one persistent `UniverseState`, that
Universe's physical generation, and its fitness/growth/pruning metadata.
Repeated optimizer steps continue the same authoritative Universe through
teacher/input/noise evolution. Evaluation clones are created from the current
authoritative Universe, scored, and discarded; their generations do not advance
the slot or its growth clock.

At generation 0, 128, 256, 384, and 512, the slot has an observed fitness
measurement. Each 128-generation interval derives one growth flag set from the
two real boundary measurements. No unobserved interval is represented by a
synthetic zero window. Parents are selected only within the same category.
When a slot becomes free, the outer optimizer either allocates another actual
seed Universe to a promising genome or creates a separate mutation-child
Universe in that free slot. A logical CandidateSlot must not contain multiple
authoritative seed Universes. Mutation fields are selected from the complete
genome field set rather than being hard-coded to a single parameter.

An integrated optimizer snapshot includes the effective `PhysicsConfig`,
`ExperimentConfig`, all 128 authoritative slot records and their complete
`UniverseState` arrays, physical generations, observed fitness references,
growth/pruning state, lineage, and category-local scheduler/policy state. It
does not serialize disposable evaluation clones. Restoring it and continuing
the same protocol is deterministic.

The headless runner uses one integrated step and an 8-generation per-candidate
evaluation timeout by default as an explicit bounded-performance budget.
`--optimizer-iterations 4` is a bounded diagnostic run; seed evidence counts
are derived from actual same-genome Universe-slot allocation, not from a
CandidateSlot containing multiple hidden seed states. The result reports
authoritative slot counts, replacement/allocation counts, mutation fields,
seed-group counts, and generations per second.

---
