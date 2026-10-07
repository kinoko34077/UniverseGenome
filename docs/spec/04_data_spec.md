# Data and Persistence Specification

Owns authoritative state representation and snapshot requirements. Permanent Cell IDs are explicitly excluded.

# 3. Slot pool and cell state

## SPEC-CELL-001 — No permanent identity
**Status: accepted**

No permanent Cell UUID or semantic identity.

Implementation may use reusable slot indices.

Slot index semantics:

- storage location only
- may be reused after deletion
- must not encode lineage
- must not be used as research meaning

---

## SPEC-CELL-002 — Capacity
**Status: accepted-default**

`MAX_CELLS = 1024` per universe.

If a spawn event occurs when no free slot exists:

> discard the spawn event and continue deterministically.

Do not dynamically grow the population container in v0.1.

---

## SPEC-CELL-003 — SoA state
**Status: accepted-default**

Preferred authoritative arrays:

- `lifecycle:uint8[MAX_CELLS]`
- `x:uint8[MAX_CELLS]`
- `y:uint8[MAX_CELLS]`
- `structure:uint16[MAX_CELLS]`
- `latent:uint16[MAX_CELLS]`
- `hp:uint8[MAX_CELLS]`
- `bond_strength:uint8[MAX_CELLS]`
- `direction:uint8[MAX_CELLS]`
- `speed_code:uint8[MAX_CELLS]`
- `age:uint32 or bounded unsigned integer[MAX_CELLS]`
- black-hole timer/state as required by implementation

Lifecycle must distinguish at least:

- FREE
- ACTIVE
- BLACK_HOLE

Exact integer codes are implementation details.

---

---

# 4. Structure field

## SPEC-STRUCT-001 — Bit layout
**Status: accepted**

`structure:uint16`

Eight hierarchy levels.

Each level consumes 2 bits.

For level `k`:

`bits [2k, 2k+1]`

---

## SPEC-STRUCT-002 — Shape values
**Status: accepted-default**

Per-level shape code:

- `00` = empty
- `01` = 1×1
- `10` = 1×2
- `11` = 2×1

A stored 2×2 code does not exist.

2×2 completion is a fusion condition.

---

## SPEC-STRUCT-003 — Hierarchy shift
**Status: accepted**

One hierarchy-level move corresponds to a 2-bit position move.

Upward:

`structure << 2`

Downward:

`structure >> 2`

Implementation must mask/clamp to 16 bits.

Hierarchy shift is conceptually different from geometric movement.

---

---

# 12. Latent state

## SPEC-LATENT-001 — Storage
**Status: accepted**

`latent:uint16`

Bits are anonymous.

No bit may be named as a semantic category in the simulation core.

---

---

# 12.1 Slow-trace state (#132)

## SPEC-ST-DATA-001 — Authoritative storage
**Status: accepted**

The accepted D1 specification adds to authoritative UniverseState:

`slow_trace:uint8[MAX_CELLS]`

This array is distinct from `latent`, HP, bond strength and structure.

Semantic constraints:

- values are anonymous physical history quantities;
- no bit/value is assigned a byte/token/teacher/target meaning;
- the array is authoritative state and is included in clone/snapshot equality;
- no host-side cache or observer-only metadata may substitute for it.

At `MAX_CELLS=1024`, compact raw storage adds exactly 1024 bytes per
Universe before container/serialization overhead.

---

## SPEC-ST-DATA-002 — Lifecycle initialization and erasure
**Status: accepted**

Per-slot data rules:

- FREE: `slow_trace=0`;
- newly allocated initial/noise/spawn ordinary cell: `slow_trace=0`;
- ACTIVE: ordinary write/transfer/decay rules apply;
- BLACK_HOLE: retains its current trace during grace and may discharge it
  locally according to accepted slow-trace behavior;
- revival: remaining trace is retained;
- final FREE: trace is set to 0 before the slot can be reused.

Reusable slot indices remain storage locations only and do not carry trace
lineage across FREE→new allocation.

---

# 18. HP

## SPEC-HP-001 — Storage
**Status: accepted**

`hp:uint8`, range 0..255.

---

## SPEC-HP-002 — Natural update
**Status: accepted**

General model:

`hp_new = clip(hp - decay + activity_gain - damage)`

Actual implementation may combine terms efficiently, but behavior must preserve:

- natural decay
- gain only from accepted meaningful activity
- collision damage

---

## SPEC-HP-003 — Activity gain
**Status: accepted**

Gain sources:

- external stimulus received
- successful latent signal propagation

Not a gain source:

- ordinary motion by itself

---

---

# 37. Snapshot format requirements

## SPEC-SNAP-001
**Status: accepted**

Snapshot must contain enough state to continue deterministically.

At minimum, when relevant to implemented phase:

- format_version
- generation
- category
- genome identifier/data
- parent genome reference if outer search is active
- universe parameters
- experiment parameters
- seed
- RNG state if chosen RNG requires state
- all authoritative cell arrays
- fitness state
- growth history
- prune history

Phase 1 can omit fields for features not yet implemented, but format versioning is required.

For the Phase 5 search population, each occupied slot is one authoritative
UniverseState. The initial matched layout uses the same four seed values for
the corresponding genome position in each latent-rule category. Later seed
evidence is represented by multiple real slots assigned to the same
genome/category; a CandidateSlot or optimizer summary must not embed multiple
hidden seed Universes. Each slot also persists whether its category/genome
evidence group has ever reached the canonical four-real-seed minimum. That
maturity marker is distinct from current group cardinality: a later-depleted
mature group remains pruning/retirement-eligible while staying ineligible for
parent selection/protection below four current seeds.

For active outer search, lineage persistence distinguishes the reusable slot
location from durable ancestry. `parent_index` may be retained as an immediate
slot-reference convenience, but it is not durable lineage identity after slot
reuse. Newly allocated seed-evidence and mutation slots therefore also persist
the parent's canonical serialized genome key as `parent_genome_key`.

The optimizer-level `prune_history` records actual retirement/replacement
events only, not every candidate that merely became prune-eligible and not
per-generation Universe snapshots. Each event records the completed optimizer
generation, retired slot index/category, retired genome key, seed, and
retirement reason. This event history is part of deterministic search
provenance.

Phase 5 optimizer snapshot format version 5 carries these fields. Version 4
snapshots remain readable for compatibility; missing durable parent-genome
references are restored as unknown and missing prune history as empty, after
which the next save emits version 5.

Disposable evaluation clones are never part of the authoritative snapshot.

For Phase 6.1, the persisted `ExperimentConfig` may additionally contain an
ordered byte-mapping list and a predeclared unmapped counterfactual input byte.
These remain experiment-protocol data, not UniverseGenome fields. Their
serialization is sufficient to restore the same evaluation/training protocol;
no evaluation-clone state is persisted and no new snapshot format version is
required solely for these protocol fields.

For Phase 6.2, the same persisted `ExperimentConfig` may contain two-byte
`input_bytes` mappings, `inter_input_generations`,
`counterfactual_prefix`, and `counterfactual_input_sequence`. These fields
round-trip through optimizer snapshots and explicit timeout reconstruction.
They remain protocol data; disposable sequence-evaluation clones are not
persisted and P6.2 alone does not require a snapshot-format increment.

For Phase 6.3, the persisted `ExperimentConfig` may additionally contain
`output_event_count` and `output_event_interval_generations`. These values
describe the bounded repeated-output evaluation protocol rather than evolved
UniverseGenome state. They round-trip through optimizer snapshots and explicit
timeout reconstruction. Observed event-generation evidence belongs to
evaluation results/reporting and does not turn disposable evaluation clones
into authoritative persisted state. P6.3 alone does not require a snapshot
format increment.

For Phase 6.4, the persisted `ExperimentConfig` may additionally contain
`retention_delay_generations`, `retention_interference_repetitions`, and
`relearning_teacher_repetitions`. These remain experiment protocol fields and
round-trip through optimizer snapshots and explicit timeout reconstruction.
Authoritative optimizer slot fitness may persist the growth-only current
`retention` value together with `retention_evidence_count` so non-evaluable
retention remains distinct from numeric zero. Detailed T0/T1/T2 disposable
clone results and checkpoint observations are measurement/reporting evidence,
not separately persisted authoritative clone state. P6.4 alone does not require
a snapshot-format increment.

For Phase 6.5, persisted `ExperimentConfig` may additionally contain
`noise_robustness_rate_delta`. Authoritative optimizer Fitness may persist
growth-only `noise_robustness` together with
`noise_robustness_evidence_count` so non-evaluable remains distinct from
numeric zero. Clean/noisy evaluation clone results, effective-rate observations
and noisy counterfactual outcomes are measurement/reporting evidence and are not
authoritative clone state. P6.5 alone does not require a snapshot-format
increment.

For Phase 6.6, persisted `ExperimentConfig` may additionally contain one
predeclared `held_out_mapping`. The held-out relation is experiment protocol
data and round-trips through optimizer snapshots and explicit timeout
reconstruction. Baseline/trained held-out clone results, event generations and
generalization classifications are measurement/reporting evidence only; they
are not authoritative clone state and are not new Phase 5 Fitness fields.
P6.6 alone does not require a snapshot-format increment.

For Phase 6.7, persisted `ByteSequenceMapping` may additionally carry an
explicit ordered `output_bytes` tuple. The tuple is experiment protocol data,
not UniverseGenome state. It round-trips through `ExperimentConfig`,
optimizer snapshots and explicit timeout reconstruction. Observed autonomous
event content/generations remain disposable measurement/reporting evidence and
are not persisted evaluation-clone state. P6.7 alone does not require a
snapshot-format increment.

For Phase 6.8, the same numeric `input_bytes` / `output_bytes` sequence
fields may be externally documented as valid UTF-8 traffic. No decoded string,
Unicode code point, tokenizer/vocabulary identity or semantic label becomes
authoritative state. Raw byte arrays continue to round-trip inside the existing
experiment protocol and optimizer snapshot. Host-side UTF-8 validity checks and
human-readable character annotations are test/documentation evidence only.
P6.8 alone does not require a snapshot-format increment.

For Phase 6.9, the same experiment protocol may contain mixed one-, two- and
three-byte mapping lengths. Exact input/output arrays, the legacy fallback
output-event count and the common inter-event timing must round-trip without
padding or truncation through `ExperimentConfig`, optimizer snapshots and
explicit timeout reconstruction. Mapping-specific observed events remain
disposable measurement/reporting evidence. P6.9 alone does not require a
snapshot-format increment.

---

---

# 37.1 Slow-trace snapshot migration (#132)

The repository currently has **two distinct versioned persistence layers**:

1. standalone/nested `UniverseState` snapshot:
   - current `format_version = 1`;
   - current kind `UniverseGenomePhase1`;
   - used directly by `persistence/snapshot.py` and embedded inside optimizer
     slot records;
2. Phase 5 optimizer envelope:
   - current `format_version = 5`;
   - current kind `UniverseGenomePhase5SteadyStateOptimizer`;
   - currently reads optimizer envelope versions 4 and 5.

The accepted slow-trace specification versions these layers independently when
implemented. There is no single repository-wide snapshot version number.

## SPEC-SNAP-ST-001 — UniverseState version 2
**Status: accepted**

Production implementation of D1 changes the authoritative cell-array schema and
therefore requires:

`UniverseState.format_version: 1 → 2`

The existing snapshot kind remains stable unless a later implementation review
finds a concrete compatibility reason to change it.

A version-2 UniverseState snapshot must contain:

- the complete `slow_trace` array with exactly `MAX_CELLS` uint8 values;
- every accepted slow-trace physical parameter needed for exact continuation in
  its serialized physics config;
- all pre-existing authoritative arrays/fields required by SPEC-SNAP-001.

Standalone `persistence/snapshot.py` therefore moves its
`SNAPSHOT_FORMAT_VERSION` from 1 to 2 when D1 is implemented.

---

## SPEC-SNAP-ST-002 — Phase 5 optimizer envelope version 6
**Status: accepted**

Because every occupied Phase 5 slot embeds an authoritative UniverseState,
production implementation of D1 also requires:

`SteadyStateOptimizer.format_version: 5 → 6`

A version-6 optimizer envelope must:

- retain existing Phase 5 scheduler, lineage, prune-history, fitness/growth and
  experiment-protocol semantics;
- serialize every occupied slot with a version-2 UniverseState;
- serialize the accepted slow-trace physical parameters in the effective base
  and per-state physics configuration needed by current consistency checks;
- keep disposable evaluation clones non-authoritative/non-persisted.

The optimizer envelope version and nested UniverseState version are related but
not interchangeable.

---

## SPEC-SNAP-ST-003 — Legacy migration / inert compatibility profile
**Status: accepted**

Backward-read compatibility must preserve both current layers.

UniverseState migration:

- version 1 remains readable;
- v1→v2 initializes `slow_trace` to an all-zero array;
- no historical trace is inferred from HP, latent, structure, output history or
  any other field.

Optimizer migration:

- accepted outer versions 4 and 5 remain readable;
- embedded version-1 UniverseState payloads migrate to version 2 using the same
  all-zero rule;
- existing v4/v5 lineage, prune-history and scheduler compatibility behavior is
  preserved;
- after successful legacy restore, the next save emits optimizer v6 containing
  nested UniverseState v2 payloads.

To preserve old trajectories rather than silently activating new memory physics,
legacy migration must also use an **inert slow-trace compatibility profile**:
no migrated zero trace may begin accumulating or affecting latent transmission
unless explicitly converted by a later user/research action.

SP3 assigns these canonical serialized compatibility values:

- `trace_write_cap = 0`;
- `trace_transfer_cap = 0`;
- `trace_discharge_cap = 0`;
- `trace_decay_rate = 0`;
- `trace_bonus_shift = 8`.

Together with the all-zero migrated trace array, this is the accepted **inert
compatibility/default profile**. It satisfies:

- effective trace write = disabled;
- transfer/discharge cannot create trace from zero;
- `uint8_trace >> 8 == 0`, so trace cannot affect latent mask width even if a
  nonzero diagnostic trace is loaded;
- decay does not introduce a stochastic change while the architecture is
  disabled.

These values are the only numeric accepted defaults established by #132.
They are selected for backward trajectory compatibility, not as an active
learning regime. Any non-inert profile remains an explicitly selected
research-only physical override until a later accepted gate promotes it.

---

## SPEC-SNAP-ST-004 — Malformed new-format rejection
**Status: accepted**

A version-2 UniverseState snapshot is malformed and must be rejected when:

- `slow_trace` is missing;
- its length differs from effective `MAX_CELLS`;
- any value is outside uint8 range;
- a FREE slot carries nonzero trace after canonical restore validation;
- an accepted slow-trace parameter required for deterministic continuation is
  missing or invalid.

A version-6 optimizer snapshot is malformed and must be rejected when:

- any authoritative slot lacks a valid version-2 UniverseState;
- required slow-trace physical configuration is absent/inconsistent between the
  slot state and accepted effective config;
- existing v5 integrity requirements such as durable parent-genome references
  for allocated children are violated.

The loader must not silently invent nonzero trace, infer historical learned
state or downgrade malformed new-format payloads to legacy semantics.

---

# 38. Snapshot timing

## SPEC-SNAP-010
**Status: accepted**

Later search mode may save leading universes every 128 generations.

Do not permanently save every universe every generation.

---


---

# 39. Generalized Outer Search data contract (#144 / #145)

## OSG-DATA-001 — SearchPlan schema
**Status: accepted**

SearchPlan is a versioned Outer-layer record. Its canonical semantics include at
minimum:

```yaml
schema_version: <integer>
plan_id: <stable id>
plan_version: <integer>
population_size: 128
fixed:
  <dimension_id>: <value>
search:
  <dimension_id>:
    domain: <registered finite/named domain>
    strategy: <registered strategy id>
rules:
  <rule_dimension_id>:
    variants: [<registered rule variant ids>]
    strategy: <registered strategy id>
constraints:
  - kind: <registered structured constraint kind>
    ...
strata:
  - group_by: [<dimension ids>]
    selection_scope: <within|across>
    allocation_policy: <registered id>
    matched_evidence_policy: <registered id>
objective_profile:
  id: <stable id>
  version: <integer>
cohorts:
  search: <declared seed/evidence policy>
  validation: <declared held-out policy>
scheduler:
  base_seed: <integer>
  policy: <registered id>
```

Serialization syntax may be JSON/YAML internally, but canonicalization shall
produce one deterministic digest for semantically identical plan data.

SearchPlan shall not contain executable source, callable references supplied by
the plan, runtime `eval` expressions or import paths to be executed.

## OSG-DATA-002 — Scalar Dimension definition
**Status: accepted**

A registered Scalar Dimension record contains:

- `dimension_id`;
- physical destination/resolver key;
- value type;
- finite values and/or explicit legal bounds;
- canonical fixed/default value;
- compatible strategy IDs;
- optional structured activation condition;
- cross-value validation constraints;
- canonical serialization/canonicalization rules.

The registry record is trusted, version-controlled repository code/data.
SearchPlan may reference it but shall not redefine executable resolver behavior.

## OSG-DATA-003 — Rule Dimension and variant definition
**Status: accepted**

A Rule Dimension record contains:

- stable `rule_dimension_id`;
- physical hook/responsibility;
- finite registered variant IDs;
- compatible search/mutation strategy IDs;
- optional activation condition and compatibility constraints.

Each variant record contains:

- stable `variant_id`;
- implementation/resolver identity owned by repository code;
- deterministic/snapshot compatibility declaration;
- applicable physical constraints.

The current latent operator variants
`masked_copy|masked_xor|rotate_copy|masked_and` are one registered Rule
Dimension family.

## OSG-DATA-004 — Structured Conditional Dimension
**Status: accepted**

Conditional activation is represented as data, not executable code.

Supported conditions shall use a bounded registered grammar such as equality,
membership and conjunction over previously resolvable dimension/rule IDs.

Each condition record declares its dependency IDs. Dependency graphs shall be
validated acyclic before execution.

Inactive dimensions resolve to their registered canonical inactive/fixed value
for physical construction and are excluded from candidate identity as an
independent varying axis.

## OSG-DATA-005 — Candidate identity
**Status: accepted / blocking**

Candidate identity is the deterministic canonical serialization/digest of the
candidate's active resolved Universe-level physical scalar values and physical
rule variant IDs, including fixed active values required to distinguish the
resolved physical candidate.

Candidate identity excludes:

- evidence seed;
- slot index;
- optimizer generation;
- fitness/growth/evidence result;
- parent/lineage metadata;
- allocation reason;
- cohort role;
- experiment/protocol parameters.

Conditionally inactive dimensions shall not create multiple candidate
identities for physically identical resolved candidates.

## OSG-DATA-006 — ResolvedUniverseSpec
**Status: accepted / blocking**

`ResolvedUniverseSpec` is an immutable, fully resolved Inner-construction
record. It contains:

- schema/version;
- all complete effective physical scalar values required to construct the
  Universe;
- all selected physical rule variant IDs/bindings;
- canonical inactive/fixed physical values where applicable;
- registry/spec identity sufficient to validate deterministic reconstruction.

It contains no search domain, mutation strategy, objective, fitness, rank,
cohort, seed, slot, lineage or acceptance metadata.

The resolver may project ResolvedUniverseSpec to the existing PhysicsConfig and
bound rule implementations, but there shall be one authoritative mapping.

## OSG-DATA-007 — Candidate record and lineage
**Status: accepted**

Outer candidate state stores separately from Inner state:

- candidate identity;
- canonical resolved candidate values/rule IDs;
- parent candidate identity, if any;
- mutation dimension/strategy/direction/result when applicable;
- evidence maturity/state;
- allocation reason;
- slot assignments;
- search provenance reference.

Reusable slot index is not durable candidate identity.

## OSG-DATA-008 — Search provenance
**Status: accepted**

Every persisted/reportable generalized run shall record:

- repository/code revision;
- SearchPlan ID/version/digest;
- registry version/digest;
- base physical config digest;
- experiment protocol digest;
- ObjectiveProfile ID/version;
- deterministic scheduler/base-seed inputs;
- candidate identity;
- evidence seed set and each seed's cohort role;
- candidate lineage;
- fixed/searchable/inactive status and resolved value for each declared
  dimension;
- relevant artifact/oracle version when running legacy compatibility.

Search provenance is Outer state. It shall never be inserted into ordinary-cell
state as learned memory.

## OSG-DATA-009 — Legacy SearchPlan data
**Status: accepted / blocking**

The canonical Legacy SearchPlan shall encode the accepted Phase 5 search without
broadening it:

- population `128`;
- one `latent_operator` Rule Dimension with the existing four variants;
- four 32-slot within-selection strata;
- eight initial genomes × four evidence seeds/category;
- existing eleven UniverseGenome scalar fields;
- existing seven initial-variation fields in current order;
- current mutation strategy/scheduler;
- current `tiered_category_rank` evidence policy;
- current fitness/growth/pruning ObjectiveProfile;
- slow-trace tuple fixed at `(0,0,0,0,8)`;
- no protocol field and no seed dimension.

Its canonical definition shall be versioned/digestible and testable against the
Phase A oracle.

## OSG-DATA-010 — Dimension registry legacy mapping
**Status: accepted**

The generalized registry shall provide one authoritative mapping from the
existing UniverseGenome/latent-category surface to generalized dimensions.

Compatibility adapters may expose the old API during migration, but they shall
delegate to this mapping rather than duplicate field lists, bounds, mutation
domains or rule-family knowledge.

## OSG-DATA-011 — Optimizer envelope v7
**Status: accepted / blocking**

Persisting generalized Outer state changes the optimizer envelope from accepted
version 6 to version 7.

A version-7 optimizer snapshot shall retain all v6 authoritative slot and
optimizer state and additionally persist or unambiguously identify:

- SearchPlan canonical payload or stable versioned reference plus digest;
- registry version/digest;
- ObjectiveProfile ID/version;
- generalized candidate identity/value records;
- generalized comparison-stratum/scheduler state;
- search provenance required for deterministic continuation.

The nested UniverseState schema does **not** change solely because Outer Search
is generalized.

## OSG-DATA-012 — Optimizer v6 → v7 migration
**Status: accepted / blocking**

Accepted optimizer envelope v6 remains readable.

A v6 restore shall deterministically migrate to v7 by binding exactly the
canonical Legacy SearchPlan and legacy ObjectiveProfile, reconstructing
generalized candidate identities from the v6 candidate/genome/category records,
and preserving:

- all 128 authoritative UniverseState snapshots;
- seeds;
- fitness/growth/health/response state;
- evidence maturity;
- scheduler cursors/counts;
- lineage/parent references;
- prune history;
- allocation/mutation metadata.

Migration shall not infer any newly searchable dimension and shall keep all
slow-trace fields fixed at the accepted inert tuple.

The next save after successful migration emits v7.

## OSG-DATA-013 — New-format fail-closed loading
**Status: accepted**

A v7 snapshot is malformed and shall be rejected if:

- SearchPlan/registry/ObjectiveProfile identity is missing or inconsistent;
- candidate identity does not match canonical resolved values/rule IDs;
- an unknown dimension/rule/strategy/objective ID is referenced;
- a seed/protocol value appears as a candidate dimension;
- stratum/scheduler state is incompatible with the bound plan;
- required provenance for deterministic continuation is absent;
- nested UniverseState payload is invalid under its own accepted schema.

The loader shall not guess replacements for unknown new IDs.

## OSG-DATA-014 — Legacy oracle artifact identity
**Status: accepted**

The blocking pre-generalization oracle is identified by:

- source SHA
  `211d84b18fe68e70f89c8921d156e1b7c0592895`;
- schema v1;
- manifest
  `research/artifacts/legacy_outer_search_oracle_v1/manifest.json`;
- bundle digest
  `9cb98606546725e3d4790d82f0e3a01f6cd8235215607c209e6952fdc283e5e3`.

Generalized code shall consume/compare against this frozen artifact; it shall
not regenerate it after production search/physics paths diverge.
