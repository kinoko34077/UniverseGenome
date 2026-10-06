# Test Specification

These are Phase 1 acceptance tests. Phase 0 adds scaffold/smoke checks without claiming Phase 1 acceptance.

# 43. Phase 1 acceptance tests

## TEST-P1-001 Deterministic replay
Same config/seed/initial state/generation count → identical authoritative final state.

## TEST-P1-002 Torus
All boundaries wrap correctly.

## TEST-P1-003 Speed
Each supported speed produces expected displacement over known generation counts.

## TEST-P1-004 Tunneling
Intermediate occupied tiles do not collide; destination overlap does.

## TEST-P1-005 Noise determinism
Same accepted conditions → same noise events.

## TEST-P1-006 Collision
Destination collision works; 3+ arrivals do not trigger unbounded pair work.

## TEST-P1-007 HP / black-hole
HP reaches zero → BLACK_HOLE → revival or timeout deletion exactly as configured.

## TEST-P1-008 Snapshot roundtrip
Save → load → continue equals uninterrupted continuation.

## TEST-P1-009 Headless
Phase 1 tests/run can execute without GUI.

## TEST-P1-010 Performance metrics
At least report:

- generations/sec
- active cells
- collision count
- noise spawn count

## Phase 2A acceptance tests

### TEST-P2A-001 Local bond gain/decay

Compatible low-relative-speed destination contact saturating-adds bond
strength; non-contact and incompatible contact saturating-subtract it.

### TEST-P2A-002 Bounded contact accounting

Three or more arrivals continue to resolve only one deterministic pair, and
bond contact accounting does not introduce an N² persistent graph.

### TEST-P2A-003 Bond snapshot continuation

Save/load restores bond parameters and arrays; resumed execution equals
uninterrupted execution.

## Phase 2B acceptance tests

### TEST-P2B-001 Operator formulas

Masked Copy, Masked XOR, Rotate + Masked Copy, and Masked AND preserve the
canonical 16-bit formulas and rotate wraparound.

### TEST-P2B-002 Mask determinism and width

The same accepted event produces the same mask; bond strength selects a width
from 1 through 16 without duplicate bit positions.

### TEST-P2B-003 Synchronous local transmission

Compatible contact applies bounded latent updates from the pre-transmission
state and counts successful transmission as meaningful activity for HP gain.

## Phase 2C acceptance tests

### TEST-P2C-001 Fusion eligibility and result

An exact local 2×2 cover with compatible level, velocity and bond state fuses
once into a level+1 1×1 core with the specified HP, direction, speed, age,
bond, latent and slot lifecycle results.

### TEST-P2C-002 Fusion rejection and bounded discovery

Wrong-level, under-bonded, over-threshold-velocity and non-composing local
groups remain unchanged; candidate discovery is local and bounded.

### TEST-P2C-003 Fusion snapshot continuation

Save/load restores fusion parameters and fused state; resumed execution equals
uninterrupted execution.

## Phase 2D acceptance tests

### TEST-P2D-001 Fragment state split

A level>0 core retains its level and emits one lower 1×1 fragment with the
canonical direction, speed, latent, HP and age split.

### TEST-P2D-002 Level-0 and capacity behavior

Compound level-0 shapes collapse, level-0 singles follow deletion, and full
capacity/probability-zero cases are deterministic no-ops.

### TEST-P2D-003 Fragmentation snapshot continuation

Save/load restores fragmentation parameters and state; resumed execution
equals uninterrupted execution.

## Phase 2E acceptance tests

### TEST-P2E-001 Age-class boundaries

Age zero is safe, age 1 maps to class 0, and the 2/4/8/16 boundaries map to
the highest-set-bit classes specified by `SPEC-AGE-001`.

### TEST-P2E-002 Age-scaled fragmentation pressure

The configured base fragmentation rate is multiplied by the class power of
two with uint16 saturation; disabled aging preserves the base rate.

### TEST-P2E-003 Deterministic age pressure

Fixed seed/config/state produces the same age-dependent fragmentation outcome,
and an older structure receives a higher pressure window than a younger one.

### TEST-P2E-004 Aging snapshot continuation

Save/load restores aging configuration and state; resumed execution equals
uninterrupted execution.

## Phase 3 acceptance tests

### TEST-P3-001 Population layout and matched metadata

The runtime creates exactly 128 independent slots as four categories × 32,
with corresponding genome/seed pairs aligned across categories.

### TEST-P3-002 Independent deterministic stepping

Fixed population seed/configuration produces the same per-slot trajectory on
replay, and stepping one slot cannot mutate another slot.

### TEST-P3-003 Bounded rewind and clone isolation

Only 128/256/512 physical-generation observation histories are accepted.
After Phase 5 integration, rewind and physical 1 Step operate only on an
observation clone; the selected authoritative optimizer slot remains unchanged.

### TEST-P3-004 Headless and observer/control surface

The headless optimizer remains functional without the GUI. The browser 16×8
overview and detail payload are sourced from the same 128 authoritative Phase 5
optimizer slots and expose category/genome/seed, fitness/growth, evidence and
lineage/allocation metadata. Render polling does not advance authority.
Run/Pause/Search Step control outer search; clone physical stepping is separate.
Save/Load round-trips the authoritative optimizer snapshot. Browser E2E must
show that a real optimizer replacement becomes visible through the observer
without rebuilding a parallel population.

### TEST-P3-005 Bounded rewind memory evidence

The original Phase 3 128/256/512 whole-population history policies continue to
retain at most the selected bounded entry count and report a reproducible
compact-history memory estimate against the documented 256 MiB reference
budget. That budget is measured guidance rather than a hard rejection
threshold; bounded entry count remains the normative REQ-151 constraint.

For the integrated Phase 5 observer, the 128/256/512 observation-clone history
is separately bounded to the selected isolated clone and never becomes an
authoritative search clock or rollback mechanism.

## Phase 4 acceptance tests

### TEST-P4-001 Raw bus and fixed organs

Bytes 0..255, independent VALID, fixed input/output organs, and recorded
non-cell coordinates are representable and deterministic.

### TEST-P4-002 Edge-based output events

Only VALID rising edges emit bytes or NULL; continuous HIGH does not repeat an
event, LOW→HIGH emits a new event, and an already-HIGH line at evaluation start
is primed without producing a spurious event.

### TEST-P4-003 Teacher exclusion and clone evaluation

Teacher B/NULL stimulation is kept out of autonomous output scoring, and
evaluation on a clone leaves the authoritative training state unchanged.

### TEST-P4-004 Multi-seed learning measurement

Baseline and trained A→B→NULL measurements run across multiple seeds with a
predeclared criterion, plus no-input and alternate-input output-clean
counterfactuals; a failed criterion is recorded as failure, not success.

### TEST-P4-005 Footprint-safe I/O boundary

Initial and noise spawns avoid every fixed-organ tile across their complete
destination footprint. Output occupancy and input proximity detect compound
cells through the complete footprint rather than only the anchor tile.

## Phase 5 acceptance tests

### TEST-P5-001 Genome separation and mutation

Genome fields exclude seed and protocol fields; mutation changes one adjacent
binary-grid parameter without changing category or seed.

### TEST-P5-002 Fitness and growth

Absolute fitness follows the lexicographic specification, while growth flags
and four 8-bit windows remain separate and bounded. Growth bit 5 retains the
canonical `retention` meaning and bit 6 retains the canonical `noise
robustness` meaning. Phase 4 no-input-clean and alternate-input-clean
counterfactual measurements must not be silently substituted for those fields.

### TEST-P5-003 Pruning and protection

Category-relative low-growth eligibility uses four windows and protects the
absolute-fitness top 1/8 from growth-only pruning. Authoritative 16-generation
health boundaries detect all-active-cell loss as an absolute-failure reason,
including for a provisional slot. Activity telemetry is persisted but is not
used as a task-response proxy. Persistent non-response is task-level and
requires four consecutive no-autonomous-output observations at real
128-generation growth boundaries while active cells remain.

### TEST-P5-004 Steady-state escalation

Category-local replacement is deterministic. Same-genome evidence expands by
allocating additional real Universe slots for the same genome/category, while
mutation children are separate real slots with fresh state. The integrated loop
maintains all 128 authoritative Universe states, measures normalized fitness
from evaluation clones of those states, aggregates evidence across each real
same-genome seed group, advances growth only at real 128-generation boundaries,
applies the accepted category-local `tiered_category_rank` policy: aggregate
canonical fitness ranks evidence groups, 4→8 uses the top 1/2, 8→16 the top
1/4, and 16→32 the top 1/8; fractional cutoffs use floor division with a
minimum of one group. Post-initial allocation preserves REQ-122 matched
comparisons where practical by reusing a same-genome seed already present in
another category when that seed is free locally; this does not couple category
selection. Never-matured mutation groups still complete to four real seeds
first; otherwise each category persistently alternates promising evidence and
mutation 1:1 when both are available, preferring lower evidence
count then better aggregate fitness then stable genome key. It
does not replace a live slot without a real free/prune-eligible target, keeps
groups below four real seed slots out of parent/protection selection, completes
never-matured mutation evidence through later freed slots, keeps provisional
sub-four mutation groups temporarily pruning-protected, preserves an
ever-mature marker once a group first reaches four real seeds, and keeps a
later-depleted mature group pruning-eligible without restoring parent/protection
eligibility. It also exercises multiple genome mutation fields and directly
covers the real growth sequence `0 → 128 → 256 → 384 → 512`. Integrated
mutation uses both directions of the adjacent binary grid, falls back from an
invalid bound direction, and never creates a no-op or an `initial_density`
value above effective `PhysicsConfig.max_cells`. Short-health tests retire
all-active-cell loss at the 16-generation cadence. Task-response tests record
one response/no-response observation at each 128-generation growth boundary
and retire `persistent_non_response` only after four consecutive no-output
observations (512 physical generations) while active cells remain; a wrong
autonomous output still counts as a response for this failure rule. The v0.1 baseline keeps retention/noise-robustness inactive rather than
driving bits 5/6 from counterfactual-clean proxies. When later accepted P6.4 or
P6.5 protocols are active, bits 5/6 require their own explicit evaluable
evidence and remain growth-only.

### TEST-P5-005 Integrated persistence

Optimizer persistence includes the effective base/protocol configuration,
all 128 authoritative Universe states and their parameters, normalized
fitness/growth references, short-health/failure state, physical cadence state,
lineage, explicit prune history, and scheduler policy state. A child persists a
stable parent-genome key independently of its reusable parent slot index.
Prune history contains actual retired/replaced targets and round-trips through
the optimizer snapshot. Current format version 5 must restore exactly; a v5 seed-evidence or mutation
child missing its durable `parent_genome_key` is malformed and must be
rejected. Legacy version 4 remains readable with absent new lineage/history
fields defaulted safely. It does not retain disposable evaluation clones.
Restore/resume produces the same bounded slot population as uninterrupted
continuation.

The headless performance path reports bounded optimizer iterations, evaluated
slots, replacements, mutation fields, actual same-genome slot-group counts,
and throughput. Promising-allocation state reports the accepted persisted
policy name and only reports evidence growth represented by corresponding real
authoritative slots.

The public optimizer CLI preserves the loaded experiment protocol unchanged by
default. A reduced evaluation timeout is permitted only through an explicit
`--optimizer-timeout-generations` override, and JSON output identifies whether
the effective protocol is canonical or explicitly overridden. CI exercises a
real optimizer CLI smoke with the shortened timeout supplied explicitly.

### TEST-P5-006 Phase 6+ handoff boundary

The Phase 5 boundary records the Phase 4 outcome and a durable Phase 6+
handoff; no Phase 6+ capability is activated by the v0.1 Work Order.

## Phase 6.1 acceptance tests

### TEST-P6-001 Ordered mapping protocol

The explicit Phase 6.1 protocol serializes ordered A→B and C→D mappings,
rejects duplicate mapped input bytes, rejects an unmapped-input control that is
actually mapped, and preserves the legacy single A→B default when Phase 6
fields are absent.

### TEST-P6-002 Shared authoritative training state

One authoritative training Universe receives all declared mappings in
deterministic order for each teacher repetition without reset between mappings.
Teacher byte/NULL stimulation remains external and excluded from autonomous
scoring.

### TEST-P6-003 Mapping-specific isolated evaluation

Each mapping is evaluated on its own disposable clone of the same source state.
A mapping succeeds only for its exact output-byte then NULL event tuple; wrong
mapping bytes, extra events, missing events or missing NULL remain failures.
Evaluation does not mutate authoritative state.

### TEST-P6-004 Multi-mapping learning measurement

Baseline/trained results remain visible per mapping and per seed. The aggregate
criterion requires every mapping across every seed, trained improvement over
baseline, no-input cleanliness and a declared unmapped-input cleanliness gate.
A failed experiment remains `learning_claim=false`.

### TEST-P6-005 Phase 5 integration

When a multi-mapping protocol is active, Phase 5 task fitness/error/timeout/
latency/activity measurements are normalized across all mapping evaluation
cases. Counterfactual cleanliness remains per-seed. The integration must not
change category isolation, pruning, seed evolution or promising-allocation
semantics.

### TEST-P6-006 Explicit protocol entry point

`config/experiment_phase6_multi_mapping.json` loads the declared A→B and C→D
protocol with the canonical evaluation timeout. Existing Phase 0–5 tests,
headless/optimizer CLI smoke and browser E2E remain GREEN.

---


## Phase 6.2 acceptance tests

### TEST-P62-001 Ordered two-byte protocol and serialization

AA→B and AC→D serialize as distinct ordered two-byte inputs. Inter-input timing,
prefix control and unmapped CA control round-trip. Invalid input length,
duplicate input sequence, and mapped counterfactual sequence are rejected.

### TEST-P62-002 Shared temporal training order

Both bytes of each mapping are delivered in order to one continuing
authoritative training Universe. Teacher output begins only after full sequence
delivery and no reset occurs between mappings.

### TEST-P62-003 Early-output rejection

An autonomous event produced after only the shared prefix A cannot count as
successful AA→B or AC→D output, even when later events otherwise match the
expected byte→NULL tuple.

### TEST-P62-004 Temporal counterfactual measurement

No-input, prefix-only A, and unmapped CA are measured independently on clones.
The aggregate criterion includes prefix/unmapped-sequence cleanliness and keeps
failed learning as `learning_claim=false`.

### TEST-P62-005 Phase 5 snapshot reconstruction

An optimizer configured with P6.2 mappings round-trips mappings,
`inter_input_generations`, prefix control and unmapped-sequence control through
its authoritative snapshot.

### TEST-P62-006 Explicit timeout reconstruction

The optimizer CLI explicit timeout override changes only the effective timeout
and preserves all P6.2 sequence/timing/control fields. Protocol reporting
exposes those fields.

### TEST-P62-007 Public temporal-sequence reporting and smoke

The public experiment entry point reports per-sequence `input_bytes`,
mapping-level baseline/trained counts, prefix/unmapped-sequence controls and the
truthful aggregate learning claim. CI executes both a bounded P6.2 experiment
smoke and a bounded P6.2 optimizer-integration smoke; Phase 0–5/P6.1 regressions
and browser E2E remain GREEN.

---

## Phase 6.3 acceptance tests

### TEST-P63-001 Repeated-event protocol and serialization

The default protocol remains one expected byte event with interval zero.
P6.3 serializes and reconstructs a bounded two-event protocol with
`output_event_interval_generations >= 2`, guaranteeing at least one released
physical generation between the one-generation teacher pulses. Unsupported
event counts and intervals below two for two-event mode are rejected.

### TEST-P63-002 Teacher event timing

After complete temporal input delivery, one continuing authoritative training
Universe receives two identical teacher byte events. Their onsets are separated
by exactly the declared physical-generation interval and are followed by the
existing teacher NULL event. No reset occurs between events or mappings.

### TEST-P63-003 Exact autonomous timing rejection

Disposable-clone evaluation accepts an exact repeated-byte→NULL tuple only when
the repeated byte-event onset interval is exactly the declared value. The same
event content at the wrong interval remains unsuccessful and contributes to the
existing wrong-output/error metric. Early, extra, missing and wrong-byte events
remain failures.

### TEST-P63-004 Timed-event measurement and controls

AA expects B,B,NULL and AC expects D,D,NULL. Per-seed/per-mapping baseline and
trained results preserve observed event generations. The aggregate criterion
states the timing requirement, retains no-input/prefix-A/unmapped-CA gates, and
keeps failed learning as `learning_claim=false`.

### TEST-P63-005 Phase 5 snapshot reconstruction

An optimizer configured with P6.3 round-trips
`output_event_count` and `output_event_interval_generations` through the
existing serialized `ExperimentConfig` without changing the optimizer snapshot
format solely for P6.3.

### TEST-P63-006 Explicit timeout reconstruction

The optimizer CLI explicit timeout override changes only the effective timeout
and preserves P6.3 count/interval, sequence mappings, inter-input timing and
counterfactual controls. Protocol reporting exposes the effective repeated-event
fields.

### TEST-P63-007 Public P6.3 reporting and real smokes

The public experiment result reports active output-event count/interval and
per-seed/per-mapping baseline/trained success with observed event generations.
CI executes both a bounded P6.3 experiment smoke and a bounded P6.3 optimizer
integration smoke. Phase 0–5, P6.1/P6.2 regressions and browser E2E remain
GREEN.

---

## Phase 6.4 acceptance tests

### TEST-P64-001 Retention protocol serialization and legacy compatibility

P6.1/P6.2/P6.3 defaults leave retention fields disabled at zero. A P6.4
protocol round-trips the declared delay, interference and relearning counts.

### TEST-P64-002 Null-aware retention/relearning rates

Zero retention-eligible or relearning-eligible cases produce null/non-evaluable
rates. Positive eligible counts produce ordinary normalized rates.

### TEST-P64-003 Growth bit 5 evidence gate

Retention growth is comparable only when both Fitness values carry explicit
retention evidence. Becoming newly evaluable does not set bit 5 and retention
metadata does not change absolute fitness ordering.

### TEST-P64-004 Phase 5 retention projection

Only an evaluable P6.4 retention rate is projected into growth-only Fitness
retention with an explicit evidence count. Non-evaluable measurements keep the
retention growth dimension inactive.

### TEST-P64-005 Continuing-state T0/T1/T2 execution

A bounded P6.4 experiment records T0/T1/T2 for every mapping on one continuing
training state. Physical checkpoint generations increase across retention delay,
interference and relearning, with T1-T0 covering at least the declared delay.

### TEST-P64-006 Retention / forgetting / relearning classification

Synthetic T0/T1/T2 cases prove the declared eligibility rules independently:
retained, forgotten, relearning-eligible and relearned counts/rates are derived
only from the corresponding checkpoint outcomes.

### TEST-P64-007 Phase 5 retention probe isolation

The Phase 5 P6.4 probe executes T0/T1/T2 without mutating the authoritative
optimizer Universe state.

### TEST-P64-008 Canonical and bounded-smoke configs

Canonical P6.4 config uses a 128-generation retention delay, one deterministic
CA interference repetition and one relearning pass. A separate bounded smoke
config uses the same semantics with shortened timing for executable CI.

### TEST-P64-009 Public P6.4 reporting and real experiment smoke

Public JSON exposes P6.4 protocol values, aggregate nullable
retention/relearning evidence, per-seed checkpoint generations and per-mapping
T0/T1/T2 success/event generations. CI executes the real bounded P6.4
experiment entrypoint.

### TEST-P64-010 Snapshot / timeout reconstruction and optimizer smoke

Optimizer snapshot round-trip preserves all P6.4 protocol fields. Explicit
timeout override changes only the evaluation timeout and preserves retention
delay/interference/relearning values. CI executes a bounded P6.4 optimizer
integration smoke.

---

## Phase 6.5 acceptance tests

### TEST-P65-001 Protocol serialization and legacy compatibility

P6.1–P6.4 defaults leave P6.5 disabled with zero delta. An enabled P6.5
protocol round-trips the declared additive noise-rate delta.

### TEST-P65-002 Null-aware robustness rate

Zero clean-success eligibility produces null/non-evaluable robustness.
Positive eligible counts produce robust/eligible normalized rate and keep
numeric zero distinct from null.

### TEST-P65-003 Growth bit 6 evidence gate

Becoming newly noise-evaluable does not set bit6. Both compared Fitness values
must carry positive noise-robustness evidence, and robustness metadata does not
change absolute fitness ordering.

### TEST-P65-004 Phase 5 robustness projection and aggregation

Only an evaluable P6.5 robustness rate is projected into growth-only Fitness
with explicit evidence count. Same-genome aggregate robustness is evidence-
weighted.

### TEST-P65-005 Matched T0 clean/noisy physical evaluation

Clean and noisy measurement start from the same trained T0 state. The noisy
effective rate is saturated clean+delta and evaluation uses the existing
physical background-noise engine.

### TEST-P65-006 Eligibility, noisy success and control cleanliness

Synthetic cases prove that clean success is required for eligibility and that
robust classification additionally requires noisy mapped success plus the
required noisy counterfactual controls. Dirty/noisy-failed eligible cases are
counted as failures.

### TEST-P65-007 Phase 5 probe isolation

P6.5 measurement through Phase 5 does not mutate authoritative slot state and
still exposes clean/noisy rates and noisy mapping evidence.

### TEST-P65-008 Canonical and bounded-smoke configs

Canonical P6.5 config uses additive delta 256. The bounded smoke config uses an
explicit stronger delta 65535 while retaining the same protocol semantics.

### TEST-P65-009 Public reporting and real experiment smoke

Public JSON exposes P6.5 protocol state, aggregate eligibility/result counts and
nullable rate, per-seed effective rates/noisy controls, and per-mapping
noise-eligible / noise-robust / noise-failed classification together with noisy
success/event generations. CI executes the real bounded P6.5 experiment path.

### TEST-P65-010 Snapshot / timeout reconstruction and optimizer smoke

Optimizer snapshot round-trip preserves the P6.5 protocol field. Explicit
timeout override changes only evaluation timeout and preserves the noise delta.
CI executes the bounded P6.5 optimizer integration path.

---

## Phase 6.6 acceptance tests

### TEST-P66-001 Held-out protocol serialization and legacy compatibility

Legacy protocols leave P6.6 disabled. An enabled protocol round-trips one
predeclared two-byte held-out mapping.

### TEST-P66-002 Held-out relation validation

Teacher and held-out cases share the fixed prefix, obey second-byte+1, and reject
held-out input/second-byte/target overlap or malformed relation targets.

### TEST-P66-003 Teacher-relation validation

P6.6 rejects teacher mappings that do not obey the same predeclared relation.

### TEST-P66-004 Held-out teacher exclusion

The training curriculum contains only AA→B and AC→D; no F teacher event is
generated for held-out AE.

### TEST-P66-005 Held-out clone evaluation isolation

Baseline and trained held-out results are distinct disposable-clone evidence
with exact F,F,NULL expectations, and Phase 5 measurement does not mutate the
authoritative state.

### TEST-P66-006 Baseline-relative classification

Synthetic seeds separately prove training-qualified, generalization-eligible,
generalized, generalization-failed, innate-baseline and no-trained-improvement
cases.

### TEST-P66-007 Null-aware generalization rate

Zero eligible cases produce null/non-evaluable generalization; positive
eligibility produces generalized/eligible normalized rate.

### TEST-P66-008 Canonical and bounded-smoke configs

Canonical and smoke configs predeclare the same AA/AC training relation and
AE→F held-out relation while retaining the accepted timed two-event semantics.

### TEST-P66-009 Public held-out reporting and real experiment smoke

Public JSON exposes aggregate generalization evidence and per-seed held-out
success/event generations/classification. CI executes the real P6.6 experiment
entrypoint.

### TEST-P66-010 Snapshot / timeout reconstruction and optimizer smoke

Optimizer snapshot round-trip and explicit timeout reconstruction preserve the
held-out relation. CI executes the bounded P6.6 optimizer integration path.

### TEST-P66-011 Phase 5 search-objective isolation

Generalization evidence does not alter Phase 5 Fitness equality or set reserved
growth bit 7.

---

## Phase 6.7 acceptance tests

### TEST-P67-001 Explicit output-sequence serialization and legacy compatibility

Legacy sequence mappings omit `output_bytes` and retain their prior serialized
shape. Explicit mappings round-trip an ordered two-byte tuple.

### TEST-P67-002 Bounded distinct-sequence validation

The initial P6.7 protocol requires exactly two distinct output bytes, requires
the first explicit byte to match legacy `output_byte`, and requires explicit
sequence length to agree with `output_event_count`.

### TEST-P67-003 Distinct-byte teacher execution

Training AA emits B,C,NULL and training AC emits D,E,NULL in declared order at
the configured interval.

### TEST-P67-004 Mapping expected-event content

Baseline/trained mapping evaluation constructs B,C,NULL and D,E,NULL rather
than legacy repeated-byte expected tuples.

### TEST-P67-005 Exact order/timing/termination failure semantics

Synthetic output-edge evidence proves exact B,C,NULL at the declared interval
succeeds while reversed order, repeated byte, wrong interval, extra event and
missing NULL fail.

### TEST-P67-006 Canonical and bounded-smoke configs

Canonical and smoke configs both declare AA→[B,C] and AC→[D,E]; canonical uses
the accepted interval/timing budget while smoke shortens timing explicitly.

### TEST-P67-007 Snapshot and explicit-timeout reconstruction

Optimizer snapshot round-trip and explicit timeout reconstruction preserve
explicit `output_bytes`. Optimizer protocol JSON exposes the serialized
mapping tuples.

### TEST-P67-008 Public reporting and real CI entrypoints

Public experiment JSON exposes declared output-byte sequences plus observed
event kind/value/generation per mapping/seed. CI executes real bounded P6.7
experiment and optimizer entrypoints while prior P6.1–P6.6 smokes remain GREEN.

---

## Phase 6.8 acceptance tests

### TEST-P68-001 Canonical raw UTF-8 byte configs

Canonical and bounded-smoke configs declare exactly C3 A9→C3 B1 and
C3 B6→C3 B8, prefix C3 and unmapped C3 A7. Host-side assertions verify those
numeric arrays are valid UTF-8 encodings of the documented characters while the
protocol itself remains numeric-byte data.

### TEST-P68-002 Byte-only teacher execution

Training through the existing P6.7 path receives/emits the declared numeric
bytes and produces the expected two-byte teacher tuples plus NULL without a
new Unicode/text runtime layer.

### TEST-P68-003 Snapshot and explicit-timeout reconstruction

Optimizer snapshot round-trip preserves all raw P6.8 byte arrays. Explicit
timeout reconstruction changes only timeout while optimizer protocol JSON
retains the raw mappings.

### TEST-P68-004 Public evidence, learning result and real CI entrypoints

Public experiment JSON exposes the declared raw input/output arrays and observed
event lists, retains the prefix/unmapped controls and reports failed learning
truthfully when applicable. CI executes real P6.8 experiment and optimizer
entrypoints and keeps the full P6.1–P6.7 + browser regression suite GREEN.
---

## Phase 6.9 acceptance tests

### TEST-P69-001 Mixed-length mapping shape and round-trip

One protocol represents 1/2/3-byte mapped inputs with 1/2/3-byte effective
outputs, round-trips through `ExperimentConfig`, and rejects bounded sequence
shapes above three bytes.

### TEST-P69-002 Mapping-specific teacher/evaluation event counts

Teacher execution emits one, two and three output bytes for the corresponding
mappings. Clone evaluation constructs exact mapping-specific expected tuples and
reports output-event counts 1/2/3.

### TEST-P69-003 Canonical configs, persistence and timeout reconstruction

Canonical and bounded-smoke configs declare the exact P6.9 byte arrays and
controls. Config round-trip, optimizer snapshot/restore and explicit timeout
override preserve mixed lengths and inter-event timing.

### TEST-P69-004 Public evidence and real entrypoints

Public experiment/optimizer JSON exposes mapping input lengths, output-event
counts, declared byte arrays and observed event lists. CI executes real P6.9
experiment and optimizer entrypoints while prior smokes remain GREEN.

### TEST-P69-005 Prefix-free mapped-input boundary

A mixed protocol rejects a valid mapped input that is a proper prefix of another
valid mapped input. Prefix-overlap semantics remain deferred to a later explicit
capability decision.



---

## Candidate slow-trace persistence architecture tests (#132)

These are **candidate specification acceptance tests**, not current passing
production tests. A later implementation owner must turn the relevant items
RED on the accepted pre-implementation main before production code is added.

### TEST-ST-001 Authoritative state / lifecycle / slot reuse

A slow-trace-enabled authoritative state has exactly one uint8 trace value per
cell slot. FREE and newly allocated cells are zero. ACTIVE→BLACK_HOLE preserves
trace during grace. Final FREE clears trace. Reusing the slot for a new cell
does not inherit the previous trace.

### TEST-ST-002 Generic meaningful-activity write

Fixtures verify the exact per-cell/per-generation rule:
- direct external stimulus alone writes
  `min(recovery_hp, trace_write_cap)`;
- successful selected latent transmission alone writes the same amount;
- simultaneous external stimulus + latent activity still writes exactly once;
- direct external stimulation that revives a BLACK_HOLE cell is eligible;
- local-revival-only eligibility without either qualifying source does not
  create a second write;
- later fusion/fragmentation does not retroactively change whether the
  qualifying event created the write proposal.

The write path has no byte value, organ-line identity, target label,
tokenizer/vocabulary input or matched-control result.

### TEST-ST-003 Local conservative transfer

Known pair fixtures cover `ta>tb`, `tb>ta`, equality and transfer-cap
limits. Each transfer preserves `ta+tb`, keeps both values in uint8 range and
uses post-write/pre-transfer values.

The test must prove that the slow-trace transfer pair set is **exactly the same
deterministic non-overlapping pair set selected for ordinary latent
transmission** in that generation. Nonlocal/incompatible or compatible-but-not-
selected cells do not transfer, and D1 does not perform a second pair-selection
pass.

### TEST-ST-004 Read coupling preserves latent operators

With generation-start source trace zero, effective mask width equals the
accepted SPEC-MASK-001 width. Nonzero trace adds only the configured bounded
bonus and caps width at 16. The selected mask still feeds the unchanged Masked
Copy / XOR / Rotate Copy / AND formulas. A slow-trace write caused by the
current latent event cannot increase that same event's width.

### TEST-ST-005 BLACK_HOLE discharge / revival / FREE

Fixtures cover generation-start BLACK_HOLE carriers with zero/one/multiple
local ACTIVE recipients and multiple BLACK_HOLE carriers competing for the same
recipient headroom.

They verify:
- revival is resolved before discharge and a revived carrier retains its trace;
- non-revived carriers discharge before the accepted timer decrement/final
  FREE rule;
- carrier and recipient processing follow the declared physical-state order,
  with storage-slot index only as a final deterministic tie-break and never an
  RNG/probability or lineage key;
- later carriers observe headroom consumed by earlier ordered carriers;
- no carrier moves more than its configured discharge cap;
- every transferred unit is subtracted from the source and total trace never
  increases;
- a cell newly entering BLACK_HOLE later in the generation does not discharge
  until the next generation;
- with no recipient, loss at final FREE is permitted;
- final FREE always clears trace and slot reuse never inherits it.

### TEST-ST-006 Deterministic decay / physical addressing

Fixed seed, generation, physical state and parameters produce the same decay
event. At most one trace unit decays per eligible carrier/generation. The event
key follows SPEC-RNG-001/002 physical addressing and does not use reusable slot
identity as a probability key. A configured nonzero forgetting regime has
fixtures that demonstrate trace can decrease without deleting the Universe.

### TEST-ST-007 Fusion / fragmentation trace conservation semantics

Fusion computes the saturating participant sum and clears participant slots made
FREE.

Fragmentation fixtures distinguish every accepted outcome:
- successful core+fragment creation splits `old_trace` as floor-half plus
  remainder and conserves the sum;
- level-0 horizontal/vertical in-place degradation retains trace unchanged;
- level-0 single-cell direct FREE erases trace without creating a ghost
  recipient;
- failed fragment allocation leaves trace unchanged.

Edge fixtures include 0, 1, 254 and 255.

### TEST-ST-008 Snapshot v6 and legacy migration

Candidate v6 save/load/continue equals uninterrupted continuation with
nonzero trace and all accepted trace parameters. Current v5 and existing v4
legacy snapshots remain readable and migrate missing trace to all-zero only.
The next save emits v6. Malformed v6 missing/wrong-length/out-of-range trace,
nonzero FREE trace, or missing required deterministic parameters is rejected.

### TEST-ST-009 Phase 5 authoritative-slot persistence / clone isolation

All 128 occupied Phase 5 slots round-trip their authoritative slow-trace state
and parameters. Disposable evaluation clones may copy trace for evaluation but
do not become separately persisted authoritative state and do not mutate the
source slot.

### TEST-ST-010 Bounded work / no hidden graph

Slow-trace storage is fixed by `MAX_CELLS`. Transfer uses only bounded local
candidate relations already produced by physical processing; discharge uses
bounded local neighborhood information; no persistent all-pairs graph/global
memory search is introduced. Performance evidence reports actual overhead
rather than assuming the raw-state bound is sufficient.

### TEST-ST-011 Semantic-shortcut negative boundary

Production slow-trace write/transfer/decay/discharge/read APIs receive no
teacher/input byte value, organ-line identity, target output, token/vocabulary
identity or host-side learned table. Physically matched events with the same
local state/activity follow the same law independent of experiment label.

### TEST-ST-012 L3 persistence / turnover causal gate

Using the predeclared high-contrast B/H condition and frozen #122/#127
density-32 primary cohort:

- >=8/12 primary seeds remain teacher-content-specific at +1000;
- negative sentinels remain clean;
- deterministic replay and raw-vs-instrumented state are equivalent;
- declared cases demonstrate original carrier FREE while the branch
  distinction survives in other authoritative local state;
- no semantic shortcut is used.

Only this gate may support an L3-persistence-capable classification. L4 recall,
output reachability, target bias and canonical learning remain separate later
tests.
