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
**Status: accepted-default**

**Parameterization:** byte timing values remain externally parameterized.

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
**Status: accepted**

**Parameterization:** the listed genome fields have bounded/searchable values.

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
genome/seed positions should be used across categories when possible. After
initialization, allocating a seed for a genome should first reuse a seed already
represented by that same genome in another category when the seed is still free
inside the current category. This preserves matched comparison where practical
without coupling category-local selection or pruning.

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

Retention and alternate-input noise robustness remain distinct growth-only
dimensions and are not added to the absolute-fitness ordering. Phase 4
counterfactual measurements such as no-input-clean and alternate-input-clean
are recorded as separate observables; this specification does not equate
either observable with retention or noise robustness.

The integrated v0.1 Phase 5 protocol does not yet define a retention or
noise-robustness measurement procedure. Its authoritative measurement path
therefore leaves those two Fitness fields at zero and bits 5/6 remain unset in
integrated v0.1 growth history. Their semantic bit positions are reserved; they
may become active only under a later explicitly accepted measurement protocol.

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

At each authoritative multiple of 16 generations, short health records
whether active cells remain and whether the physical window produced
measurable activity. A window with no active cells is an
`all_active_cells_gone` absolute failure.

Persistent non-response uses the already-defined task/evaluation protocol,
rather than generic physical activity. At each authoritative 128-generation
growth boundary, the trained-state A-only evaluation clone records whether any
autonomous output event occurred. Four consecutive boundary observations with
no autonomous output event cover the accepted 512-generation stagnation
horizon and produce `persistent_non_response`, provided active cells still
remain. Any autonomous output event, including a wrong byte or NULL, counts as
a response for this absolute-failure test and breaks the consecutive
non-response run. Correctness remains the responsibility of absolute fitness
and growth. `activity_cost` is not used as a substitute for task response.

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

The v0.1 implementation retires both accepted measurable absolute failures
before growth-only protection and minimum-evidence maturity:
`all_active_cells_gone` and the 512-physical-generation
`persistent_non_response` protocol defined by SPEC-PRUNE-001. Malformed
state/configuration remains an error.

---

---

# 33. Steady-state evolution

## SPEC-EVOL-001
**Status: accepted-default**

Do not require whole-population synchronized evolutionary generations.

When a slot becomes free:

- add another seed for a promising genome, or
- insert a mutation child

Seed-evidence cardinalities for a promising genome are represented by actual
occupied slots in the same category/genome group. The notation

`4 → 8 → 16 → 32`

describes those real group sizes; it is not a `seed_count` field and must not
be implemented by packing multiple UniverseStates into one logical slot. A
newly allocated evidence or mutation slot owns one fresh UniverseState at
generation 0.

## SPEC-EVOL-002 — Promising allocation policy
**Status: accepted-default**

The accepted v0.1 policy is named `tiered_category_rank`.

Promising decisions are category-local and operate on one category/genome
evidence group, never on individual seed slots. Rank groups by aggregate
normalized `SPEC-FIT-001` absolute fitness using its canonical lexicographic
ordering. Only groups with at least four currently occupied real seed slots are
eligible.

The next real-seed evidence tier is selected from the group's current occupied
cardinality:

- 4..7 seeds: eligible for 4 → 8 only while the group ranks in the top 1/2;
- 8..15 seeds: eligible for 8 → 16 only while the group ranks in the top 1/4;
- 16..31 seeds: eligible for 16 → 32 only while the group ranks in the top 1/8;
- 32 seeds: no further evidence allocation.

For a fractional rank cutoff, use floor division with a minimum of one eligible
group. Rank ties are resolved by the stable genome key. Evidence-group rank is
computed once per group, so a group does not gain extra ranking weight merely
because it already occupies more seed slots.

A never-matured mutation group below four real seeds keeps the existing
minimum-evidence completion priority. Once that obligation is absent, and both
ordinary choices are available, each category alternates deterministically 1:1
between promising evidence allocation and a new mutation child. A category's
alternation cursor is independent of the other categories and is persisted in
the optimizer scheduler. If no promising group is eligible, mutation proceeds
without consuming the evidence side of the alternation.

When multiple promising groups can receive a real seed, prefer:

1. lower current occupied seed count;
2. better aggregate canonical absolute fitness;
3. stable genome key.

A pruned/free target cannot count as progress for its own evidence group: the
target's group is excluded from the promising ranking and evidence allocation
for that replacement. Allocation still occurs only into a real
free/prune-eligible slot; this policy does not authorize forced replacement.

The policy is persisted by name and does not add fields to the absolute-fitness
tuple, evolve seed, or permit cross-category elimination.

## SPEC-EVOL-003 — Minimum evidence eligibility
**Status: accepted**

**Invariant:** the minimum-evidence gate below is required for selection safety.

A category/genome group must have at least four currently allocated real seed
Universes before any of its slots may participate in parent selection or
absolute-fitness protection. This is the minimum evidence tier from the
canonical `4 → 8 → 16 → 32` real-slot ladder, not a new promising threshold
and not a change to the five-field absolute fitness ordering.

A newly inserted mutation child therefore remains selection-ineligible while
its group has fewer than four real seed slots. When a later pruning decision
frees another slot, the optimizer may allocate that slot as additional seed
evidence for an incomplete mutation-child group until the four-seed minimum
is reached. Only after that gate is satisfied can the still-open promising
allocation policy govern any later evidence expansion.

Minimum-evidence **selection eligibility** is distinct from pruning lifecycle.
A never-matured mutation group with fewer than four real seeds is provisional
and is temporarily excluded from growth pruning while its initial evidence is
being completed. Once a category/genome group has reached four real seed
Universes at least once, that maturity is persistent search metadata. If later
pruning reduces the group below four seeds, its remaining slots are no longer
eligible for parent selection or absolute-fitness protection, but they remain
eligible for growth pruning/retirement. A depleted mature group must not become
a permanently occupied, non-selectable and non-prunable population fragment.
This maturity state is included in optimizer persistence.

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
seed-group counts, and generations per second. No unapproved promising
threshold is implied by this diagnostic output.

---
