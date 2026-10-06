# UniverseGenome v0.1 Requirements

Canonicalized from repository Issue #3. Issue #3 remains the review/history surface; this checked-in file owns the durable requirement text after Phase 0 acceptance.

# Purpose

This Issue is the **repository-local v0.1 requirements document** for UniverseGenome.

It states **what must be achieved and what must be verifiably true**, while deliberately avoiding unnecessary implementation details.

Parent work: #1  
Design record: #2  
Control: kinoko34077/devflow#314

## Traceability correction

The canonical requirements in this file end at `REQ-082`. Historical Issue #8
contains an old related-canon range mentioning nonexistent `REQ-083`; that
reference is retained as history and corrected additively in the changelog.
No `REQ-083` requirement is introduced by this note.

Specification details are maintained separately from this requirements layer.

---

# 0. Status vocabulary

- `accepted`: explicitly adopted requirement
- `accepted-default`: v0.1 default, revisable after experiment
- `parameterized`: value must remain configurable/searchable
- `candidate`: not yet accepted
- `implemented`: code exists
- `tested`: observable verification exists

Do not promote `accepted-default` or `parameterized` items to immutable requirements merely because an implementation uses one concrete value.

---

# 1. Product / research objective

## REQ-001 — Local-physics learning universe
**Status: accepted**

UniverseGenome shall provide an artificial universe in which learning can be investigated as **deterministic local state evolution through time**.

The inner universe shall not require:

- backpropagation
- a separate conventional training phase
- a separate conventional inference phase
- semantic token classes
- explicit syntax classes
- explicit concept labels

Acceptance:

- one universe can be stepped forward solely through its configured local physics plus external stimuli/noise
- replay from the same accepted initial conditions produces the same state trajectory

---

## REQ-002 — Separation of inner learning and outer search
**Status: accepted**

The system shall distinguish:

1. **inner universe learning**  
   state change caused by experience and local dynamics

2. **outer universe-genome search**  
   search/evolution over universe-level physical parameters or rule families

Outer search shall not be treated as the learned memory of the inner universe.

---

# 2. Scope requirements

## REQ-010 — v0.1 development boundary
**Status: accepted**

The first implementation milestone shall stop at:

- canonical specification establishment
- repository scaffold
- one deterministic universe
- minimal local physics
- deterministic replay
- snapshot save/load equivalence
- headless execution
- measurable performance counters

The first implementation milestone shall **not require**:

- 128-universe search
- fusion
- fragmentation
- four latent transmission categories
- A→B→NULL learning success
- steady-state evolution
- full GUI dashboard

Those remain specified for later phases.

---

## REQ-011 — Future v0.1 learning target
**Status: accepted**

The first learning task after the physics foundation is ready shall be:

> input `A` → autonomous output `B` → `NULL`

The success definition must compare learned behavior against a baseline/untrained state and must be evaluated on unseen evaluation runs or held-out seeds where applicable.

---

# 3. World requirements

## REQ-020 — Discrete toroidal world
**Status: accepted**

Each universe shall provide a finite discrete 2D world with:

- logical size: 32×32
- toroidal wrapping
- discrete generation steps

Boundary crossing shall wrap rather than stop or reflect.

---

## REQ-021 — Fixed-point motion
**Status: accepted**

The universe shall support sub-cell motion without floating-point position state.

Required velocity set:

- 0
- 1/8
- 1/4
- 1/2
- 1
- 2
- 4
- 8 logical cells per generation

The implementation shall be capable of exact deterministic movement for these values.

---

## REQ-022 — Intentional tunneling
**Status: accepted**

High-speed cells are allowed to pass over intermediate positions without collision.

Collision shall be based on the destination footprint, not swept-path intersection.

This is intentional behavior, not a defect.

---

# 4. Cell-state requirements

## REQ-030 — No permanent Cell ID
**Status: accepted**

The model shall not require a persistent semantic identity/UUID for each cell.

The implementation may use transient/reusable storage slots.

Acceptance:

- deletion and reuse of storage does not require maintaining lineage identity
- replay correctness does not depend on persistent cell IDs
- snapshot correctness does not require UUID mapping

---

## REQ-031 — Compact state
**Status: accepted**

The model shall support at least:

- `structure` state
- `latent` state
- HP
- position
- direction
- speed
- age/lifecycle state

The primary structure and latent fields shall each fit in 16 bits in v0.1.

---

## REQ-032 — Bounded cell population
**Status: accepted-default**

A universe shall use a bounded active-cell capacity suitable for fixed-array execution.

Initial capacity:

> 1024 active cell slots per universe

If a spawn cannot be represented because capacity is full, behavior must be defined rather than allowing unbounded allocation.

---

# 5. Structure / hierarchy requirements

## REQ-040 — Eight hierarchy levels
**Status: accepted**

The structure representation shall support 8 hierarchy levels using 2 bits per level inside a 16-bit field.

---

## REQ-041 — Minimal shape vocabulary
**Status: accepted-default**

The v0.1 structure vocabulary shall be sufficient to represent:

- empty
- 1×1
- 1×2
- 2×1

A 2×2 arrangement shall be interpreted as a candidate structural transition/fusion condition rather than requiring a fifth stored shape code.

---

## REQ-042 — Hierarchy movement semantics
**Status: accepted**

Moving one hierarchy level upward/downward must be distinguishable from ordinary geometric movement.

Hierarchy is an abstraction/structure axis, not physical z-position.

---

# 6. Latent-state requirements

## REQ-050 — Anonymous latent state
**Status: accepted**

Each active cell shall support a 16-bit latent state.

No semantic labels may be attached to individual latent bits in the core model.

---

## REQ-051 — Gradual local propagation
**Status: accepted**

Latent influence between cells shall be local and capable of partial-bit propagation.

The model shall not require dense all-to-all mixing of all 16 latent dimensions each step.

---

## REQ-052 — Comparable operator families
**Status: accepted**

Later multi-universe experiments shall support four distinct latent propagation rule categories while keeping unrelated experimental conditions aligned as much as possible.

Initial accepted-default families:

- Masked Copy
- Masked XOR
- Rotate + Masked Copy
- Masked AND

Categories must be comparable without cross-category direct elimination during the initial comparison stage.

---

# 7. Collision / contact requirements

## REQ-060 — Local collision detection
**Status: accepted**

Collision processing shall use spatial locality.

The implementation must not rely on all-cell × all-cell pair search.

Target complexity should remain near O(N) with respect to active cells under ordinary operation.

---

## REQ-061 — Direction-aware relative velocity
**Status: accepted**

Contact/collision intensity shall consider velocity direction, not only scalar speed magnitude.

Two equal-speed cells moving in opposite directions must not be treated as low-relative-speed contact merely because their scalar speeds match.

---

## REQ-062 — Bounded multi-cell collision work
**Status: accepted**

When 3 or more cells occupy/collide at one destination, the system shall avoid exhaustive pairwise processing in a single generation.

Initial behavior:

> process one deterministically selected/pseudorandom pair per generation.

---

# 8. Bond/contact requirements

## REQ-070 — No arbitrary persistent N² bond matrix
**Status: accepted**

The model shall not require arbitrary persistent pairwise bonds between every possible pair of cells.

---

## REQ-071 — Local contact strength
**Status: accepted-default**

The system shall support a compact local contact/bond-strength quantity that can:

- increase under compatible low-relative-speed contact
- decrease outside compatible contact
- affect local signal transmission/fusion tendency

Long-term memory must not depend solely on a graph edge table.

---

# 9. HP / lifecycle requirements

## REQ-080 — HP as bounded survival state
**Status: accepted**

HP shall be represented as an 8-bit bounded quantity.

Required range:

> 0..255

---

## REQ-081 — Activity-based recovery
**Status: accepted**

HP recovery shall be caused by meaningful interaction such as:

- external stimulation
- actual latent signal transmission

Ordinary movement alone shall not be sufficient for HP recovery.

---

## REQ-082 — Black-hole grace state
**Status: accepted**

HP reaching zero shall not require immediate deletion.

A temporary deletion-wait/black-hole lifecycle shall exist.

During that state:

- ordinary movement stops
- fusion/fragmentation stops
- external/local stimulation may permit revival
- expiration releases the storage slot

Grace duration shall be configurable.

---

# 10. Noise requirements

## REQ-090 — Background exploration noise
**Status: accepted**

The universe shall support low-density background noise that creates new ordinary cells.

Noise shall not be implemented as a special damage-only process in the first design.

---

## REQ-091 — Noise is bounded and parameterized
**Status: parameterized**

Noise frequency shall be externally configurable/searchable.

Initial candidate family:

- 1/1024
- 1/512
- 1/256
- 1/128
- 1/64

Noise handling must remain deterministic for a fixed seed/configuration.

---

# 11. I/O requirements

## REQ-100 — Raw byte capability
**Status: accepted**

The architecture shall ultimately support raw 8-bit byte values `0..255` without requiring a learned vocabulary/tokenizer.

---

## REQ-101 — Compact fixed I/O organs
**Status: accepted-default**

The v0.1 I/O design shall use an 8-bit bus rather than 256 one-hot byte organs.

Input:

- 8 data signals
- VALID

Output:

- 8 data signals
- VALID
- NULL

---

## REQ-102 — Distinguish silence from NULL
**Status: accepted**

No output event and explicit NULL are different states.

- no event = universe has emitted nothing
- NULL event = explicit end of utterance

---

## REQ-103 — Event-edge output
**Status: accepted**

Output events shall be edge-based.

Continuous assertion of the same VALID state shall not be counted as repeated bytes without deassertion/reassertion.

---

# 12. Training / evaluation requirements

## REQ-110 — Teacher stimulation without hidden backprop
**Status: accepted**

Training shall be expressible as external stimulation of the same universe, including teacher stimulation at the output side.

The teacher process shall not secretly modify internal weights using a separate optimization rule.

---

## REQ-111 — Teacher output excluded from autonomous score
**Status: accepted**

Teacher-forced output activity shall not count as autonomous correct output.

---

## REQ-112 — Evaluation isolation
**Status: accepted-default**

Evaluation shall be capable of running on a clone/snapshot-derived copy so that testing does not alter the training universe.

---

# 13. Outer-search requirements

## REQ-120 — 128 simultaneous universe slots
**Status: accepted**

The full search mode shall support:

> 128 simultaneous universe slots

---

## REQ-121 — Four category isolation
**Status: accepted**

The 128 slots shall be divisible into four 32-slot latent-rule categories.

Direct cross-category elimination/selection shall not be used during the initial rule-family comparison.

---

## REQ-122 — Matched genome/seed comparison
**Status: accepted-default**

Where practical, the same universe-genome + seed combination shall be represented across the four categories so that the latent operator is the main differing variable.

---

## REQ-123 — Seed must not be genome
**Status: accepted**

Random seed shall not be an evolvable universe-genome parameter.

The optimizer must not win merely by selecting lucky initial randomness.

---

## REQ-124 — Universe parameters separate from experiment parameters
**Status: accepted**

Universe-genome parameters and experiment-protocol parameters shall be represented separately.

Examples of universe parameters:

- initial density
- HP gain/decay
- noise rate
- contact gain/decay
- collision/fusion thresholds
- fragmentation rate
- black-hole grace
- rotate amount

Examples of experiment parameters:

- byte hold
- byte gap
- teacher delay
- teacher repetitions
- evaluation timeout
- test noise strength

---

# 14. Evaluation requirements

## REQ-130 — Absolute fitness and growth are separate
**Status: accepted**

The system shall distinguish:

- current performance
- recent improvement/growth

A mature high-performing universe must not be discarded solely because recent growth is near zero.

---

## REQ-131 — Lexicographic performance comparison
**Status: accepted-default**

Initial absolute comparison should prioritize, in order:

1. success
2. fewer wrong outputs
3. fewer timeouts
4. lower latency
5. lower activity cost

Avoid collapsing these into an arbitrary weighted scalar unless later evidence justifies it.

---

## REQ-132 — Do not reward internal complexity directly
**Status: accepted**

Fitness shall not directly reward:

- more cells
- more bonds
- greater hierarchy depth

unless a future experiment explicitly tests such a hypothesis.

These may be recorded as diagnostics.

---

## REQ-133 — Binary-aligned observation windows
**Status: accepted**

The system shall support evaluation/pruning windows centered on:

- 16 generations
- 128 generations
- 512 generations

---

# 15. Determinism / reproducibility requirements

## REQ-140 — Deterministic replay
**Status: accepted**

For a fixed:

- initial state
- seed
- physical parameters
- experiment inputs
- generation count

the resulting universe state must be reproducible.

---

## REQ-141 — Randomness must not depend unnecessarily on branch execution count
**Status: accepted-default**

Random-event generation should be stable enough that comparisons across rule categories are not invalidated merely because one category consumed an extra sequential RNG call.

A counter/hash-derived event RNG is an acceptable preferred design.

---

# 16. Persistence requirements

## REQ-150 — Snapshot continuation equivalence
**Status: accepted**

Saving a universe snapshot and resuming it must reproduce the same continuation as uninterrupted execution, for all state required by the implemented phase.

This is a Phase 1 acceptance condition.

---

## REQ-151 — Bounded rewind history
**Status: accepted**

GUI/history mode shall support bounded history lengths:

- 128
- 256
- 512 generations

The system shall not require permanent storage of every generation of every universe.

---

# 16.1 Candidate slow-trace persistence architecture (#132)

The requirements in this section are **candidate specification changes** selected
by #130 for formal review. They are not implemented/accepted production
behavior until #132 reaches its terminal acceptance and a separate
implementation owner completes the required production acceptance.

## REQ-ST-001 — Anonymous bounded slow state
**Status: candidate**

When the slow-trace architecture is enabled, every cell slot shall have one
authoritative bounded anonymous slow state:

`slow_trace:uint8`, range `0..255`.

Requirements:

- slow-trace values/bits have no byte/token/teacher/target semantic labels;
- FREE slots contain zero slow trace;
- newly spawned/noise-created ordinary cells begin with zero slow trace;
- reusable slot allocation must not inherit a previously freed carrier's trace;
- the field is part of authoritative UniverseState rather than host-side
  weights, caches, lookup tables or observer metadata;
- adding this state must not introduce a permanent Cell ID.

---

## REQ-ST-002 — Generic meaningful-activity write
**Status: candidate**

Slow trace may be increased only by meaningful physical activity already
recognized by the local universe.

Initial qualifying sources:

- external physical stimulus received by an ordinary cell;
- successful local latent signal propagation.

The write law shall consume only the physical activity amount attributed to
the affected ordinary cell. It shall not receive:

- input/teacher byte value;
- organ/line identity;
- target label;
- tokenizer/vocabulary identity;
- matched-control outcome.

The same physical write law applies regardless of why the qualifying activity
occurred.

A cell receives at most one slow-trace write increment per generation. If
external stimulus and successful latent propagation both qualify for the same
cell in one generation, they do not multiply the write. Direct external
stimulation that revives a BLACK_HOLE cell is a qualifying physical stimulus;
local-revival eligibility by itself is not a second slow-trace write source.

---

## REQ-ST-003 — Local bounded conservative transfer
**Status: candidate**

Slow trace may transfer only through an already-local compatible physical
relation admitted by ordinary contact/transmission processing.

Requirements:

- transfer per selected local pair/event is bounded;
- transfer uses pre-transfer pair values and is deterministic;
- transfer is conservative before explicit decay or bounded saturation loss;
- no arbitrary persistent N² pair graph is added;
- no global broadcast/search is used;
- ordinary operation remains bounded by the existing local candidate relation;
- the transfer pair set reuses the same deterministic non-overlapping selected
  pair set used by ordinary latent transmission for that generation; D1 does
  not create a second independent pair-selection graph.

---

## REQ-ST-004 — Turnover-tolerant local discharge
**Status: candidate**

A BLACK_HOLE carrier shall have a bounded local physical path to discharge slow
trace before final transition to FREE.

Requirements:

- only currently local ACTIVE recipients are eligible;
- discharge per generation is bounded;
- transferred quantity is subtracted from the dying carrier;
- no permanent Cell ID, ghost edge, lineage cache or FREE-slot memory is used;
- if no eligible local recipient exists before final FREE, trace loss is
  permitted;
- revival before FREE retains the carrier's remaining trace.

This requirement provides a turnover path; it does not guarantee that every
memory survives every carrier loss.

---

## REQ-ST-005 — Explicit physical forgetting
**Status: candidate**

Slow trace shall be forgettable through an explicit bounded deterministic
physical process.

Requirements:

- nonzero trace can decay without deleting the entire Universe;
- decay is deterministic for fixed accepted state/seed/config;
- event addressing must not depend on permanent/reusable Cell identity;
- memory may also be lost through isolated carrier deletion or bounded
  saturation/interference;
- the architecture shall not create immutable/permanent trace.

---

## REQ-ST-006 — Bounded local causal read effect
**Status: candidate**

Slow trace shall be capable of influencing later local physics without
encoding or injecting a target value.

Initial proposed read boundary:

- slow trace may modify only the width of an already-local latent transmission;
- the four accepted latent operator formulas remain unchanged;
- effective transmission width remains in `1..16`;
- a same-generation slow-trace write shall not retroactively amplify the
  latent event that created that write.

---

## REQ-ST-007 — Deterministic persistence and migration
**Status: candidate**

All slow-trace state and all accepted physical parameters required for exact
continuation shall be represented in authoritative persistence.

Requirements:

- save/load/continue remains equivalent to uninterrupted execution;
- a new snapshot contract version is required when production slow trace is
  adopted;
- the immediately prior accepted snapshot version remains readable;
- missing historical slow trace migrates deterministically to all-zero only;
- migration must not synthesize historical learned state;
- malformed new-format slow-trace state is rejected rather than guessed;
- Phase 5 authoritative slot snapshots round-trip the field;
- disposable evaluation clones remain non-authoritative/non-persisted.

---

## REQ-ST-008 — Separate L3 persistence acceptance gate
**Status: candidate**

The slow-trace architecture shall not be classified as L3-persistence-capable
until a separately predeclared causal audit demonstrates all of:

- the accepted high-contrast B/H physical-write condition;
- the frozen #122/#127 density-32 primary cohort;
- at least **8 of 12** teacher-content-specific physical distinctions remain
  at +1000 generations;
- declared turnover cases in which an original carrier is freed while the
  branch distinction survives in other authoritative local state;
- negative sentinels remain clean;
- deterministic replay and raw-vs-instrumented authoritative equivalence;
- no semantic shortcut.

This gate does not establish L4 recall, L5 output reachability, L6 target bias
or L7 canonical learning.

---

# 17. GUI / observation requirements

## REQ-160 — Core must run without GUI
**Status: accepted**

The simulation core shall be independently executable/headless.

GUI rendering must not drive the authoritative simulation clock.

---

## REQ-161 — Multi-universe overview
**Status: accepted**

Later GUI mode shall present:

- 128 universes
- 16×8 layout
- 8×8 summary per universe
- approximately 2 fps

Universe thumbnails shall be visually separated.

Initial mapping:

- activity → brightness
- highest hierarchy → hue

---

## REQ-162 — Detailed observation
**Status: accepted**

A selected universe shall support detailed 32×32 observation at approximately 8 fps with switchable modes including:

- HP
- hierarchy
- latent bit
- activity
- bond/contact strength

---

## REQ-163 — Observation must not perturb search
**Status: accepted**

Manual inspection during automated search shall use a clone or otherwise avoid pausing/modifying the authoritative search universe.

---

# 18. Performance requirements

## REQ-170 — Avoid quadratic collision architecture
**Status: accepted**

Normal collision handling shall not scale as arbitrary O(N²) all-pairs comparison.

---

## REQ-171 — Phase 1 performance instrumentation
**Status: accepted**

Headless Phase 1 execution shall expose at least:

- generations/sec
- active cell count
- collision count
- noise spawn count

No unsupported absolute speed target is imposed before measurement.

---

# 19. Phase 1 acceptance requirements

Phase 1 shall not be considered complete merely because the program launches.

The following observable checks are required.

## REQ-A01
Same config/seed/initial state/generation count → identical final state.

## REQ-A02
Torus wrapping is correct on all boundaries.

## REQ-A03
All supported velocity magnitudes move to the expected positions.

## REQ-A04
Tunneling ignores intermediate occupied tiles and reacts at destination only.

## REQ-A05
Noise events are deterministic for the same accepted conditions.

## REQ-A06
Destination collision works and multi-cell collision work remains bounded.

## REQ-A07
HP→BLACK_HOLE→revival/deletion behavior matches specification.

## REQ-A08
Snapshot save→load→continue equals uninterrupted continuation.

## REQ-A09
Headless execution path does not depend on GUI.

## REQ-A10
Measured performance counters are reported.

---

# 20. Non-goals for the initial foundation

The following are explicitly **not required to prove Phase 1 complete**:

- human-like language behavior
- UTF-8 sentence generation
- generalized reasoning
- successful outer evolution
- final GUI polish
- persistent graph neural connections
- classical-CA purity
- learned semantic labels
- production deployment

---

# 21. Completion criterion for the first learning milestone

After later phases implement I/O and learning, the initial research success criterion is:

> Across multiple seeds, without internal backpropagation, repeated teacher experience produces a statistically/observably higher autonomous `A → B → NULL` reproduction performance than the corresponding untrained/baseline condition.

Exact success threshold/sample count is intentionally not frozen in this requirements Issue yet; it shall be defined before that experiment is accepted.

---

# 22. Phase 6 capability requirements

## REQ-200 — Multiple mapping protocol
**Status: accepted**

The experiment layer shall support a bounded ordered set of byte-to-byte
mappings as protocol data, separate from UniverseGenome. Phase 6.1 begins with:

- `A (0x41) → B (0x42) → NULL`
- `C (0x43) → D (0x44) → NULL`

Mapped input bytes shall be unambiguous within one protocol.

---

## REQ-201 — Shared authoritative training history
**Status: accepted**

All declared Phase 6.1 mappings for one seed shall be presented to the same
authoritative training Universe in deterministic protocol order. The Universe
shall not be reset between mappings merely to simplify measurement.

Teacher-produced output remains external stimulation and shall not count as
autonomous success.

---

## REQ-202 — Isolated per-mapping evaluation
**Status: accepted**

Each declared mapping shall be evaluated independently on a disposable clone
of the same source state. Evaluation of one mapping shall not mutate the
authoritative training state or another mapping's evaluation clone.

Wrong mapped outputs, extra events, missing expected events, or missing NULL
termination shall remain observable failures.

---

## REQ-203 — Truthful multi-mapping learning claim
**Status: accepted**

A Phase 6.1 learning claim may be true only under a predeclared criterion that:

- evaluates every declared mapping across every evaluated seed;
- compares trained performance against the corresponding baseline;
- retains no-input and a predeclared unmapped-input cleanliness control;
- does not use another valid mapped input as the unmapped-input control;
- records failure as `learning_claim=false` when the criterion is not met.

Implementation of the experimental capability does not itself constitute
evidence that learning succeeded.

---

## REQ-210 — Ordered temporal sequence protocol
**Status: accepted**

The experiment layer shall support bounded ordered input-byte sequences as
protocol data outside UniverseGenome. Phase 6.2 begins with exactly two-byte
inputs:

- `AA → B → NULL`;
- `AC → D → NULL`.

Input sequence identity includes byte order. Duplicate declared input sequences
within one protocol are invalid.

---

## REQ-211 — Explicit inter-input timing and shared history
**Status: accepted**

Temporal mappings shall expose an explicit inter-input timing interval. All
input bytes of a mapping shall be delivered in declared order before teacher
output begins. All declared P6.2 mappings for one seed shall train the same
continuing authoritative Universe without reset between mappings.

---

## REQ-212 — Sequence-specific isolated evaluation
**Status: accepted**

Each declared temporal mapping shall be evaluated on a separate disposable clone
of the same source state. Autonomous output before the complete declared input
sequence is delivered is an early/wrong output and cannot count as success.

Cross-target output, extra events, missing expected output, missing NULL, and
timeout remain failures. Evaluation shall not mutate authoritative training
state or another evaluation clone.

---

## REQ-213 — Predeclared temporal counterfactuals
**Status: accepted**

P6.2 shall measure predeclared controls that distinguish sequence/history
dependence from a response to the shared first byte:

- no-input control;
- prefix-only `A` control;
- an unmapped two-byte sequence, initially `CA`.

These controls shall be declared before observing results and shall remain
independent learning-claim gates.

---

## REQ-214 — Truthful temporal-sequence claim and Phase 5 compatibility
**Status: accepted**

A P6.2 learning claim may be true only when every declared sequence across every
evaluated seed satisfies the exact-output criterion, trained performance exceeds
the corresponding baseline, and all required counterfactuals remain clean.

Phase 5 evaluation/fitness shall consume every active sequence evaluation case
deterministically without changing category isolation, seed evolution, fitness
ordering, pruning, or promising-allocation policy merely to enable P6.2.
Failure remains `learning_claim=false`.

---

## REQ-220 — Bounded repeated-output event protocol
**Status: accepted**

Phase 6.3 shall extend an active mapping with a bounded expected autonomous
output-event count while preserving the existing input mapping representation.
The initial P6.3 capability is exactly two repeated byte events followed by
NULL:

- `AA → B, B → NULL`;
- `AC → D, D → NULL`.

The repeated-event count and timing remain experiment/protocol data outside
UniverseGenome. The existing one-byte and P6.2 one-output-event protocols remain
valid with one expected byte event.

---

## REQ-221 — Explicit output-event timing and authoritative training
**Status: accepted**

P6.3 shall expose an explicit physical-generation interval between the onsets of
the repeated expected byte events. For the bounded two-event protocol, the
interval shall be at least two generations so the one-generation teacher pulses are separated by at least one released physical generation.

Teacher stimulation shall begin only after the complete input sequence and
teacher delay. Both repeated teacher byte events and the terminating NULL shall
act on the same continuing authoritative training Universe without reset.
Teacher-generated events shall not count as autonomous success.

---

## REQ-222 — Exact multi-event clone evaluation
**Status: accepted**

Each P6.3 mapping shall continue to be evaluated on an isolated disposable
clone. Success requires the exact declared byte-event content, order, count and
byte-event onset interval followed by NULL.

Early output, wrong byte, wrong repeated-event interval, wrong event count,
extra output, missing NULL, or timeout cannot count as success. A timing-mismatched
otherwise-correct byte event shall remain observable through the existing output
error surface used by Phase 5.

P6.3 does not introduce an independent NULL-timing objective.

---

## REQ-223 — Truthful timed-event measurement and controls
**Status: accepted**

Baseline and trained results shall retain per-mapping/per-seed event-generation
evidence sufficient to inspect the repeated-event timing criterion.

The existing P6.2 no-input, prefix-only `A`, and predeclared unmapped `CA`
controls remain independent learning-claim gates. A P6.3 learning claim may be
true only when every declared mapping across every evaluated seed satisfies the
exact timed-event criterion, trained performance exceeds the corresponding
baseline, and all required counterfactuals remain clean.

Failure remains `learning_claim=false`. Implementing P6.3 measurement capability
does not itself establish that timed-output learning succeeded.

---

## REQ-224 — Phase 5 compatibility and bounded capability boundary
**Status: accepted**

Phase 5 shall consume active P6.3 mapping evaluations through the existing
success, wrong-output, timeout, latency and activity fitness surfaces without
changing category isolation, seed evolution, fitness ordering, pruning,
promising allocation, matched-seed rules, or authoritative-slot semantics merely
to enable P6.3.

Snapshot/config reconstruction and explicit timeout override shall preserve the
P6.3 event-count/timing protocol. P6.3 is limited to the bounded repeated
same-byte event capability; arbitrary distinct output-byte sequences remain a
later capability.

---

# 22.4 Phase 6.4 forgetting / relearning requirements

## REQ-230 — Explicit retention / relearning protocol
**Status: accepted**

Phase 6.4 shall retain the accepted P6.3 timed mappings and add explicit
experiment/protocol parameters for:

- retention delay in physical generations;
- deterministic interference repetitions;
- relearning teacher-curriculum repetitions.

The initial canonical protocol uses a 128-generation no-teacher delay, one
predeclared unmapped `CA` interference episode without desired teacher output,
and one relearning curriculum pass. These settings are experiment data, not
UniverseGenome fields. P6.5 stochastic/noise robustness remains separate.

---

## REQ-231 — Continuing-state T0 / T1 / T2 evaluation
**Status: accepted**

For each seed, one authoritative trained Universe shall continue without reset
through:

1. T0 disposable-clone evaluation immediately after initial training;
2. the declared no-teacher retention delay and deterministic interference;
3. T1 disposable-clone evaluation;
4. the declared relearning curriculum on that same authoritative Universe;
5. T2 disposable-clone evaluation.

Evaluation clones shall not mutate the authoritative training state. Snapshot
rollback, hidden restoration, or reset shall not count as relearning.

---

## REQ-232 — Explicit retention / forgetting / relearning evaluability
**Status: accepted**

A mapping/seed result is retention-eligible only when T0 succeeds. A
retention-eligible case is retained when T1 succeeds and forgotten when T1
fails. Only forgotten cases are relearning-eligible; a forgotten case is
relearned when T2 succeeds.

Aggregate reporting shall expose eligibility and result counts. Retention rate
is defined only when retention-eligible count is non-zero. Relearning rate is
defined only when relearning-eligible count is non-zero. Zero eligible cases
shall be reported as non-evaluable/null rather than as successful or failed
retention.

---

## REQ-233 — Retention is growth-only Phase 5 evidence
**Status: accepted**

P6.4 is the first accepted protocol allowed to populate the canonical Phase 5
retention growth observable. Growth bit 5 may compare retention only when both
compared measurements carry explicit evaluable retention evidence.

Retention and retention-evidence metadata shall not alter the canonical
absolute-fitness ordering. Relearning remains research evidence in this bounded
capability and shall not become an absolute-fitness weight. Category isolation,
seed handling, pruning thresholds, promising allocation and authoritative-slot
semantics remain unchanged.

---

## REQ-234 — P6.4 persistence and public evidence
**Status: accepted**

Experiment serialization, optimizer snapshot/restore and explicit timeout
reconstruction shall preserve the P6.4 protocol. Public experiment reporting
shall expose per-seed/per-mapping T0/T1/T2 success and event generations,
checkpoint generations, aggregate retention/relearning eligibility and rates,
and truthful non-evaluable states.

Canonical and bounded-smoke P6.4 configs shall use the same protocol surface.
Implementing this capability shall not be interpreted as evidence that the
current universe learned, retained or relearned a mapping.

---

# 22.5 Phase 6.5 controlled physical-noise robustness requirements

## REQ-240 — Explicit physical-noise robustness protocol
**Status: accepted**

Phase 6.5 shall measure robustness using the existing deterministic physical
background-noise mechanism. The experiment protocol adds
`noise_robustness_rate_delta`, separate from UniverseGenome.

The initial canonical delta is 256 in the uint16 probability domain
(additional 1/256 event probability per physical generation). The noisy
effective rate is `min(65535, clean_noise_rate + delta)`. A smoke protocol may
use a stronger explicit delta but shall not redefine the canonical protocol.

---

## REQ-241 — Matched clean/noisy T0 evaluation and authority isolation
**Status: accepted**

For each seed/mapping, clean and noisy evaluations shall originate from the
same trained T0 state on disposable clones. The noisy clone changes only the
effective physical `noise_rate`; the authoritative training Universe and clean
clone remain unchanged.

P6.4 retention/interference/relearning remains a separate continuing-state
capability. P6.5 evaluation shall not advance or mutate authoritative Phase 5
slot state.

---

## REQ-242 — Explicit noise-robustness evaluability
**Status: accepted**

A mapping/seed case is noise-eligible only when its clean T0 mapped evaluation
succeeds and the noisy effective rate is strictly greater than the clean rate.
An eligible case is robust only when the noisy mapped evaluation succeeds and
the required noisy counterfactual controls remain output-clean.

For the active temporal protocol those controls are no-input, prefix-only A and
unmapped CA. Eligible cases that do not satisfy the robust condition are noise
failures.

Aggregate reporting shall expose eligible/robust/failed counts. The robustness
rate is defined only when eligible count is non-zero; zero eligible cases are
non-evaluable/null. Clean failure followed by noisy failure or accidental noisy
success is not evidence of robustness.

---

## REQ-243 — Noise robustness is growth-only Phase 5 evidence
**Status: accepted**

P6.5 is the first accepted protocol allowed to populate the canonical Phase 5
noise-robustness growth observable. Growth bit 6 may compare robustness only
when both compared Fitness values carry explicit evaluable noise-robustness
evidence.

Noise robustness and its evidence count shall not change the canonical
absolute-fitness ordering. P6.4 retention/bit5 remains independent. Category
isolation, pruning thresholds, promising allocation, seed handling and
authoritative-slot semantics remain unchanged.

---

## REQ-244 — P6.5 persistence and public evidence
**Status: accepted**

Experiment serialization, optimizer snapshot/restore and explicit timeout
reconstruction shall preserve the P6.5 protocol field. Public reporting shall
expose effective clean/noisy rates, per-seed/per-mapping clean/noisy results,
noisy control results, eligibility/result counts and null-aware robustness
rate.

Canonical and bounded-smoke configs shall use the same protocol surface. CI
shall execute real P6.5 experiment and optimizer entrypoints. Implementing the
capability does not itself constitute evidence that the current universe
learned or is noise-robust.

---

# 22.6 Phase 6.6 predeclared held-out relation generalization requirements

## REQ-250 — Predeclared held-out relation protocol
**Status: accepted**

Phase 6.6 shall evaluate a held-out relation declared before results are observed.
The bounded initial relation keeps one fixed prefix and maps the second input
byte to its successor byte. Teacher training remains limited to:

- `AA → B, B → NULL`;
- `AC → D, D → NULL`.

The held-out case is `AE → F, F → NULL`. It shall be protocol data, never an
evolved UniverseGenome field, and shall not be included in teacher training.

---

## REQ-251 — Held-out validation and clone isolation
**Status: accepted**

Teacher and held-out mappings shall be ordered two-byte sequences with the same
declared prefix. Each relation target must equal the second input byte plus one.
The held-out input, second byte and target shall be distinct from the
teacher-trained cases.

Baseline held-out and trained held-out evaluations shall use separate disposable
clones. Neither evaluation may mutate the authoritative training Universe.

---

## REQ-252 — Baseline-relative generalization evaluability
**Status: accepted**

A seed is training-qualified only when every teacher mapping succeeds after
training, each corresponding teacher baseline did not already succeed, and the
required trained counterfactual controls remain clean.

A seed is generalization-eligible only when it is training-qualified and its
baseline held-out evaluation did not already succeed. An eligible seed is
generalized when the trained held-out evaluation succeeds, otherwise it is a
generalization failure.

Aggregate reporting shall expose training-qualified, eligible, generalized and
failed counts. Generalization rate is defined only when eligible count is
non-zero; zero eligible cases are non-evaluable/null.

---

## REQ-253 — P6.6 remains outside Phase 5 search objective
**Status: accepted**

P6.6 generalization evidence is measurement/reporting evidence only. It shall
not change the canonical absolute-fitness tuple or ordering, shall not consume
reserved growth bit 7, and shall not alter category isolation, pruning,
promising allocation, seed handling or authoritative-slot semantics.

P6.4 retention/bit5 and P6.5 noise-robustness/bit6 remain independent.

---

## REQ-254 — P6.6 persistence, public evidence and executable entrypoints
**Status: accepted**

Experiment serialization, optimizer snapshot/restore and explicit timeout
reconstruction shall preserve the predeclared held-out mapping. Public reporting
shall expose held-out protocol identity, per-seed baseline/trained held-out
success and event generations, per-seed classification, aggregate null-aware
counts/rate, and the unchanged learning claim.

Canonical and bounded-smoke configs shall use the same semantics. CI shall
execute real P6.6 experiment and optimizer entrypoints. Implementing the
capability does not itself constitute evidence that the current universe
generalizes.

---

# 22.7 Phase 6.7 bounded distinct multi-byte output requirements

## REQ-260 — Explicit ordered distinct output-byte sequence protocol
**Status: accepted**

Phase 6.7 shall allow a two-byte input mapping to declare an explicit ordered
output-byte tuple as experiment/protocol data. The initial bounded capability is:

- `AA → B, C → NULL`;
- `AC → D, E → NULL`.

The explicit tuple has exactly two distinct bytes and its first byte remains
compatible with the legacy `output_byte` field. When no explicit tuple is
present, P6.1–P6.6 legacy `output_byte + output_event_count` behavior remains
authoritative.

---

## REQ-261 — Exact teacher and autonomous sequence semantics
**Status: accepted**

Teacher training shall stimulate the declared output bytes in order using the
accepted output-event interval and then terminate with teacher NULL. Evaluation
shall use disposable clones and require exact byte content, order, count,
inter-event timing and NULL termination.

Repeated wrong bytes, reversed order, wrong timing, missing/extra byte events,
missing NULL, output before complete input and timeout are failures.
Teacher-generated events shall never count as autonomous success.

---

## REQ-262 — Counterfactual-gated learning claim and authority isolation
**Status: accepted**

P6.7 shall retain no-input, prefix-A and unmapped-CA controls. A learning claim
may be true only when every declared mapping succeeds for every evaluated seed,
trained performance is strictly better than baseline, and all required controls
remain clean.

Baseline/trained and other evaluation probes remain disposable clones and shall
not mutate the continuing authoritative training Universe. Failed learning is a
valid result and remains `learning_claim=false`.

---

## REQ-263 — P6.7 remains outside Phase 5 search-policy changes
**Status: accepted**

Distinct sequence content may flow through existing success/wrong-output/
timeout/latency/activity observables but shall not change the canonical
absolute-fitness ordering, consume reserved growth bit 7, or alter retention
bit5/noise-robustness bit6.

P6.7 shall not change pruning, promising allocation, category isolation, seed
handling, matched-seed behavior or authoritative-slot semantics.

---

## REQ-264 — Persistence, public evidence and executable entrypoints
**Status: accepted**

Experiment serialization, optimizer snapshot/restore and explicit timeout
reconstruction shall preserve explicit output-byte tuples. Public experiment
reporting shall expose declared output sequences and observed event
kind/value/generation per mapping/seed.

Canonical and bounded-smoke P6.7 configs shall use the same semantics. CI shall
execute real P6.7 experiment and optimizer entrypoints. P6.8 raw UTF-8 remains
deferred.

Implementing this capability does not itself constitute evidence that the
current universe learned the sequence task.

---

# 22.8 Phase 6.8 bounded raw UTF-8 byte experiment requirements

## REQ-270 — UTF-8 remains external raw byte traffic
**Status: accepted**

Phase 6.8 shall exercise the existing byte-sequence protocol with byte arrays
that are externally predeclared as valid UTF-8. The artificial universe shall
continue to receive and emit only 8-bit bus values.

P6.8 shall not introduce tokenizer/vocabulary state, Unicode/code-point
semantics, semantic labels, text embeddings, a semantic parser, or any other
symbolic shortcut into the universe, fitness, or search policy.

---

## REQ-271 — Canonical bounded UTF-8 mappings and controls
**Status: accepted**

The initial bounded P6.8 protocol shall use exactly:

- `[0xC3,0xA9] → [0xC3,0xB1] → NULL` (documented externally as é→ñ);
- `[0xC3,0xB6] → [0xC3,0xB8] → NULL` (documented externally as ö→ø).

Required controls remain:
- no input;
- prefix-only `[0xC3]`;
- unmapped valid UTF-8 sequence `[0xC3,0xA7]` (ç).

Human-readable characters are documentation only; canonical runtime/config
identity is the numeric byte sequence.

---

## REQ-272 — Reuse exact byte-sequence teacher/evaluation semantics
**Status: accepted**

P6.8 shall reuse the accepted P6.7 teacher and disposable-clone evaluation
path without decoding text during training or scoring. Success continues to
require exact byte content, order, event count, declared inter-event timing and
NULL termination, with no early/extra/wrong events.

Tests may externally decode the predeclared arrays solely to prove that the
canonical experiment traffic is valid UTF-8. Invalid/malformed UTF-8
classification and arbitrary-length text are outside this bounded child.

---

## REQ-273 — Learning claim and Phase 5 boundary remain unchanged
**Status: accepted**

A P6.8 learning claim remains all-mappings/all-seeds, strictly
baseline-relative and counterfactual-gated. Failed learning remains
`learning_claim=false`.

P6.8 shall not change canonical absolute-fitness ordering, consume reserved
growth bit 7, or change retention bit5, noise-robustness bit6, generalization,
pruning, promising allocation, category isolation, seed handling,
matched-seed behavior or authoritative-slot semantics.

---

## REQ-274 — Persistence, public evidence and executable entrypoints
**Status: accepted**

Canonical and bounded-smoke P6.8 configs shall preserve the raw input/output
byte arrays through `ExperimentConfig`, optimizer snapshot/restore and
explicit timeout reconstruction using the existing P6.7 sequence format.

Public experiment/optimizer diagnostics shall expose the declared numeric byte
arrays and observed event evidence without making decoded text part of
authoritative state or fitness. CI shall execute real P6.8 experiment and
optimizer entrypoints while P6.1–P6.7 regressions remain GREEN.

P6.8 alone does not require a snapshot-format increment or a new inner-universe
text representation. After P6.8 acceptance, any further capability requires a
new explicit roadmap decision rather than automatic P6.9 work.

---

# 22.9 Phase 6.9 mixed-length raw byte sequence requirements

## REQ-280 — One bounded protocol may mix 1/2/3-byte mappings
**Status: accepted**

Phase 6.9 shall allow one experiment protocol to contain one-byte, two-byte and
three-byte raw input mappings together, with declared output sequences of the
corresponding bounded lengths. Mixed-length mappings must preserve their exact
declared byte arrays without padding or truncation.

The initial bounded mapped inputs shall be prefix-free so P6.9 isolates mixed
length handling from valid-mapping prefix ambiguity.

---

## REQ-281 — Mapping-specific teacher and autonomous event counts
**Status: accepted**

Teacher execution and disposable-clone evaluation shall resolve output-event
count from each mapping's declared output sequence. Success requires exact byte
content, order, count, accepted inter-event timing and NULL termination.

The legacy global output-event count remains the fallback for mappings without
an explicit output tuple; existing P6.1–P6.8 fixed-length behavior must remain
compatible.

---

## REQ-282 — Mixed-length controls and learning claim
**Status: accepted**

The bounded P6.9 protocol shall retain no-input cleanliness and use:
- one proper-prefix control of the three-byte mapped input: `[0x47,0x48]`;
- one unmapped complete sequence control: `[0x4D,0x4E]`.

A learning claim remains all-mappings/all-seeds, strictly baseline-relative and
counterfactual-gated. Failed learning remains `learning_claim=false`.

---

## REQ-283 — Phase 5 and semantic boundaries remain unchanged
**Status: accepted**

P6.9 shall not add tokenizer/vocabulary/Unicode semantic state, decoded-text
scoring, arbitrary/unbounded sequence lengths, prefix-overlapping valid
mappings, or hidden learned weights.

It shall not change Phase 5 absolute-fitness ordering, reserved growth bit 7,
retention/noise-robustness semantics, pruning, promising allocation, category
isolation, seed handling, matched-seed behavior or authoritative-slot
semantics. P6.1–P6.8 remain regression-compatible.

---

## REQ-284 — Persistence, public evidence and executable entrypoints
**Status: accepted**

Canonical and bounded-smoke P6.9 configs shall preserve exact mapping arrays,
mixed lengths and timing through `ExperimentConfig`, optimizer
snapshot/restore and explicit timeout reconstruction.

Public experiment/optimizer diagnostics shall expose mapping input lengths,
mapping output-event counts and declared/observed raw byte evidence. CI shall
execute real P6.9 experiment and optimizer entrypoints together with the
earlier capability regression set.

Implementing P6.9 does not itself constitute evidence that the current universe
learned the mixed-length tasks.

---

# 23. Traceability

Historical rationale: #2  
Parent implementation/bootstrap task: #1

This Issue owns **requirements**.  
Exact equations, field layouts, generation ordering, and implementation defaults belong in the detailed specification Issue.
