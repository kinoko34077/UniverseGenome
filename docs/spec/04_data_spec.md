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

---

---

# 38. Snapshot timing

## SPEC-SNAP-010
**Status: accepted**

Later search mode may save leading universes every 128 generations.

Do not permanently save every universe every generation.

---
