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

The readiness-accepted v0.1 Phase 5 baseline did not itself define measurement
procedures for retention or noise robustness, so those dimensions stayed
inactive rather than using counterfactual proxies. Later bounded capabilities
activate them only through explicit evaluable evidence: P6.4 may populate
retention/bit5 and P6.5 may populate noise robustness/bit6. For either bit,
becoming newly evaluable is not itself improvement; both compared measurements
must carry evidence for that dimension.

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

The public headless optimizer preserves the loaded canonical experiment
protocol by default, including its configured per-candidate evaluation timeout.
A shorter timeout is allowed only through the explicit
`--optimizer-timeout-generations` override and is reported as an override in
the JSON status. CI may use such an explicit bounded override for smoke
verification without redefining the research protocol.
`--optimizer-iterations 4` is a bounded diagnostic run; seed evidence counts
are derived from actual same-genome Universe-slot allocation, not from a
CandidateSlot containing multiple hidden seed states. The result reports
authoritative slot counts, replacement/allocation counts, mutation fields,
seed-group counts, and generations per second. No unapproved promising
threshold is implied by this diagnostic output.


# 34. Phase 6.1 multiple byte mappings

## SPEC-P6MAP-001 — Ordered mapping protocol
**Status: accepted**

Phase 6.1 experiment protocol stores an ordered tuple of byte mappings outside
UniverseGenome. The first declared protocol is:

- `0x41 → 0x42` (A → B)
- `0x43 → 0x44` (C → D)

Input bytes must be unique within one protocol. A separate predeclared
counterfactual input byte must not be one of the mapped inputs.

The legacy Phase 4 single `A → B` protocol remains the default when no
Phase 6 mapping list is supplied.

## SPEC-P6MAP-002 — Shared training state
**Status: accepted**

For each teacher repetition, mappings are presented in declared order to one
continuing authoritative training Universe. Each mapping uses the existing
input hold/gap/delay and teacher byte + NULL stimulation. No reset occurs
between mappings.

Teacher stimulation is never inserted into autonomous output observations.

## SPEC-P6MAP-003 — Per-mapping clone evaluation
**Status: accepted**

Baseline and trained evaluation create a separate disposable clone for each
mapping. A mapping succeeds only when its autonomous event tuple exactly equals
the declared output byte followed by NULL. Cross-mapping bytes, extra events,
missing events and missing NULL remain failures.

No-input and the predeclared unmapped-input counterfactual are evaluated
separately from valid mapped inputs.

## SPEC-P6MAP-004 — Measurement and Phase 5 integration
**Status: accepted**

Measurements expose per-seed mapping results and per-mapping aggregate
successes. The aggregate learning claim requires all mapping/seed evaluation
cases to succeed, trained successes to exceed baseline successes, and both
counterfactual cleanliness gates to pass.

Phase 5 absolute fitness normalizes task success and output/error/latency/
activity metrics across all mapping evaluation cases selected by the active
experiment protocol. Counterfactual cleanliness remains normalized per seed.

Adding this measurement capability does not change Phase 5 category isolation,
seed evolution, pruning or promising-allocation semantics and does not by
itself establish a successful learning result.

---

# 35. Phase 6.2 temporal sequence discrimination

## SPEC-P6SEQ-001 — Two-byte ordered mapping protocol
**Status: accepted**

P6.2 extends the protocol mapping union with an ordered two-byte input sequence
and one expected output byte. The initial declared mappings are:

- `[0x41, 0x41] → 0x42` (AA → B);
- `[0x41, 0x43] → 0x44` (AC → D).

The mapping remains experiment/protocol data and is not an evolved
UniverseGenome field. The P6.1 one-byte mapping representation remains valid.

## SPEC-P6SEQ-002 — Inter-input timing and training order
**Status: accepted**

`inter_input_generations` is an explicit non-negative protocol parameter.
Each input byte is held using the existing byte-hold rule; between input bytes,
input is released for the declared inter-input interval. Teacher delay and
teacher byte→NULL stimulation begin only after the complete input sequence.
All mappings train one continuing authoritative Universe in deterministic
protocol order.

## SPEC-P6SEQ-003 — Sequence clone evaluation
**Status: accepted**

A sequence mapping is evaluated on a disposable clone. The evaluator records
autonomous output throughout input delivery and the subsequent evaluation
window. Any autonomous output event before completion of the full sequence
makes the mapping unsuccessful even if the final event tuple otherwise equals
the expected byte→NULL tuple.

Cross-target bytes, extra events, missing events, missing NULL and timeout remain
ordinary failures.

## SPEC-P6SEQ-004 — Temporal counterfactual controls
**Status: accepted**

When sequence mappings are active, the protocol persists and measures:

- `counterfactual_prefix`: initially `[0x41]`;
- `counterfactual_input_sequence`: initially `[0x43, 0x41]` (CA);
- the existing no-input control.

The prefix must match the shared declared sequence prefix. The unmapped sequence
must not equal any mapped input sequence. Both controls are evaluated on
disposable clones and gate the aggregate learning claim.

## SPEC-P6SEQ-005 — Phase 5 integration and reporting
**Status: accepted**

Phase 5 uses all trained mapping evaluations from the active protocol when
computing task success, wrong-output, timeout, latency and activity aggregates.
P6.2 does not alter search-category isolation, the canonical fitness ordering,
pruning, seed allocation, or promising policy.

Optimizer snapshots persist the sequence protocol through the existing
serialized `ExperimentConfig`; no new optimizer snapshot version is required
solely for P6.2 fields. Explicit timeout reconstruction may replace only the
timeout while preserving sequence mappings, timing and counterfactual controls.

Public experiment reporting identifies each mapping by `input_bytes` and
reports prefix/unmapped-sequence control results without relabeling failed
learning as success.

---

# 36. Phase 6.3 multi-event output timing

## SPEC-P6TIM-001 — Bounded repeated-output protocol
**Status: accepted**

P6.3 extends the active experiment protocol with two fields:

- `output_event_count`: expected byte-event count before NULL;
- `output_event_interval_generations`: physical-generation onset-to-onset
  interval between repeated expected byte events.

The backwards-compatible default is one byte event with interval zero. The
initial bounded P6.3 capability permits exactly two repeated byte events with an
interval of at least two generations, leaving at least one released physical generation between the one-generation teacher pulses. It does not generalize arbitrary distinct
output-byte sequences.

The initial declared mappings remain the P6.2 input sequences:

- `AA → B, B → NULL`;
- `AC → D, D → NULL`.

## SPEC-P6TIM-002 — Teacher output timing
**Status: accepted**

Teacher stimulation begins only after complete input-sequence delivery,
`byte_gap_generations`, and `teacher_delay_generations`.

Each teacher output event remains one physical-generation external stimulation.
For two-event P6.3, the first byte event begins at generation `t`, the second
byte event begins exactly
`output_event_interval_generations` physical generations later, and NULL is
then delivered through the existing termination path. Output is released during
the intervening idle generations.

All declared mappings and all repeated teacher events train one continuing
authoritative Universe for the seed. No reset is introduced between repeated
events or mappings, and teacher output remains excluded from autonomous scoring.

## SPEC-P6TIM-003 — Exact timed clone evaluation
**Status: accepted**

P6.3 uses the existing disposable-clone evaluation boundary. A mapping succeeds
only when the autonomous event tuple exactly matches the declared repeated byte
events followed by NULL and the repeated byte-event onsets have the exact
declared physical-generation interval.

An autonomous byte event with correct content but wrong repeated-event timing is
an output error, does not consume the timed expected match for error accounting,
and cannot make the evaluation successful. Early output, cross-target byte,
wrong count, extra event, missing event, missing NULL and timeout remain ordinary
failures.

NULL remains required termination but has no new independent timing objective in
P6.3.

## SPEC-P6TIM-004 — Measurement and learning claim
**Status: accepted**

Measurements retain the existing per-mapping/per-seed baseline and trained
results together with observed autonomous event generations. Public reporting
includes the active output-event count and interval and enough per-seed evidence
to inspect the timed-event result.

When the P6.2 sequence protocol is active, no-input, prefix-only `A`, and
unmapped `CA` controls remain unchanged. The aggregate learning claim requires
all mapping/seed cases to satisfy the exact timed-event criterion, trained
successes to exceed baseline successes, and all required counterfactuals to
remain clean.

A failed experiment remains `learning_claim=false`.

## SPEC-P6TIM-005 — Persistence and Phase 5 integration
**Status: accepted**

`output_event_count` and `output_event_interval_generations` are serialized
inside the existing `ExperimentConfig`. Optimizer snapshot round-trip and
explicit timeout reconstruction preserve both fields; no optimizer snapshot
format increment is required solely for P6.3.

Phase 5 continues to aggregate success, wrong-output, timeout, latency and
activity over all active mapping evaluations. P6.3 introduces no new fitness
weight or ordering and does not alter category isolation, pruning, seed
allocation, matched-seed handling, promising policy, or authoritative-slot
semantics.

Canonical and bounded-smoke P6.3 experiment configs use this same protocol
surface. Public and CI entry points report failed learning without
reinterpretation.

---

# 37. Phase 6.4 forgetting / relearning retention

## SPEC-P6RET-001 — Retention protocol fields and defaults
**Status: accepted**

`ExperimentConfig` adds:

- `retention_delay_generations`;
- `retention_interference_repetitions`;
- `relearning_teacher_repetitions`.

All three default to zero so P6.1/P6.2/P6.3 protocols remain unchanged.
P6.4 is enabled only when the retention protocol is explicitly populated; an
enabled protocol requires positive values and a declared unmapped interference
sequence. The canonical P6.4 values are 128 physical generations, one
deterministic unmapped `CA` interference episode, and one relearning
curriculum pass.

## SPEC-P6RET-002 — T0 / T1 / T2 continuing-state execution
**Status: accepted**

T0 evaluates the initially trained state on disposable clones. The authoritative
training Universe then advances for the declared no-teacher retention delay and
receives the declared interference episode without desired teacher output. T1
evaluates that continuing state on new disposable clones. The same authoritative
Universe then receives the declared relearning curriculum without reset or
rollback and T2 evaluates new clones.

Standalone experiments advance their actual trained state through this
protocol. Phase 5 measurement executes the same protocol on an isolated probe
clone so authoritative optimizer slot state is not advanced by evaluation.

## SPEC-P6RET-003 — Retention classification and null evaluability
**Status: accepted**

Per mapping and seed, measurement retains T0, T1 and T2 evaluation results.
T0 success creates retention eligibility. T0+T1 success is retained; T0 success
with T1 failure is forgotten. Forgotten cases are relearning-eligible and T2
success on such a case is relearned.

Aggregates expose eligible, retained, forgotten, relearning-eligible and
relearned counts. Retention/relearning rates are null when their denominator is
zero. A numeric zero rate and a non-evaluable result are distinct states.

## SPEC-P6RET-004 — Phase 5 retention growth boundary
**Status: accepted**

An evaluable P6.4 retention rate is projected to the existing growth-only
`Fitness.retention` field together with explicit
`retention_evidence_count`. Growth bit 5 is comparable only when both the
previous and current measurements carry retention evidence; becoming newly
measurable is not itself an improvement.

The absolute `Fitness.sort_key()` remains unchanged. Counterfactual
cleanliness is not relabeled as retention, relearning is not added to absolute
fitness, and P6.4 does not alter Phase 5 category/pruning/seed/promising-policy
semantics.

## SPEC-P6RET-005 — Persistence, configs, reporting and CI
**Status: accepted**

P6.4 fields serialize inside the existing `ExperimentConfig`; optimizer
snapshot round-trip and explicit timeout reconstruction preserve them without a
snapshot-format increment solely for P6.4.

The public experiment report exposes protocol fields, aggregate
retention/relearning counts and nullable rates, per-seed checkpoint generations,
and per-mapping T0/T1/T2 success plus event generations. Canonical and bounded
smoke configs use the same semantics. CI executes both the real bounded P6.4
experiment entrypoint and the optimizer reconstruction entrypoint.

---

# 38. Phase 6.5 controlled physical-noise robustness

## SPEC-P6NOISE-001 — Protocol field and effective rate
**Status: accepted**

`ExperimentConfig.noise_robustness_rate_delta` is a non-negative uint16-domain
protocol field with legacy default zero. A positive value enables P6.5.

The canonical delta is 256. For one clean trained T0 state with effective
`clean_noise_rate`, the noisy evaluation config uses:

`noisy_noise_rate = min(65535, clean_noise_rate + noise_robustness_rate_delta)`

Only the disposable noisy evaluation state receives this config change. The
field is not part of UniverseGenome.

## SPEC-P6NOISE-002 — Matched clone execution and controls
**Status: accepted**

Clean and noisy mapping evaluations begin from snapshot-identical trained T0
state. Each evaluator remains disposable. The noisy state uses the existing
SPEC-NOISE physical event path under its increased rate.

P6.5 also evaluates noisy no-input and the active protocol's alternate/prefix/
unmapped-sequence controls. For the accepted temporal sequence protocol, robust
classification requires noisy no-input, prefix-only A and unmapped CA controls
to remain output-clean.

Phase 5 `measure_trained_state` performs this probe without advancing the
authoritative slot state.

## SPEC-P6NOISE-003 — Eligibility and null-aware classification
**Status: accepted**

A mapping record is noise-eligible only when:
- its clean T0 evaluation succeeds; and
- the seed's noisy effective rate is strictly greater than its clean rate.

An eligible record is robust only when its noisy mapped evaluation succeeds and
the required noisy counterfactual controls are clean. Otherwise it is
noise-failed.

Measurement exposes `noise_robustness_eligible_count`,
`noise_robust_count`, `noise_failed_count`, and a robustness rate. The rate
is null when eligibility is zero and otherwise equals robust/eligible.

## SPEC-P6NOISE-004 — Phase 5 growth boundary
**Status: accepted**

An evaluable P6.5 rate is projected to growth-only
`Fitness.noise_robustness` with explicit
`noise_robustness_evidence_count`. Same-genome evidence aggregation weights
robustness by that evidence count.

Growth bit 6 is set for an improvement only when both previous and current
Fitness values carry positive noise-robustness evidence. The absolute
`Fitness.sort_key()` remains unchanged. P6.4 retention and bit5 remain
independent.

## SPEC-P6NOISE-005 — Persistence, reporting, configs and CI
**Status: accepted**

The P6.5 protocol field round-trips through ExperimentConfig, optimizer
snapshot/restore and explicit timeout reconstruction without requiring a new
snapshot format solely for P6.5.

Public experiment JSON reports protocol state, aggregate null-aware robustness,
per-seed clean/noisy effective rates and controls, and per-mapping noisy success
and event generations. Canonical config uses delta 256; the bounded smoke config
uses an explicitly stronger delta 65535 while preserving the same semantics.
CI executes both P6.5 experiment and optimizer entrypoints.

